"""Factory principal de la aplicación Flask para E.V.A (Sistema de Gestión de Estacionamientos)."""

from flask import Flask, jsonify, request
import pymysql

from backend.config import Config, BASE_DIR
from backend.database import auto_init_if_empty
from backend.routes.guards import load_logged_in_user
from backend.routes.api_routes import api_bp
from backend.routes.web_routes import web_bp
from backend.services.exceptions import DomainError


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder=str(BASE_DIR / "frontend" / "templates"),
        static_folder=str(BASE_DIR / "frontend" / "static"),
    )
    app.config["SECRET_KEY"] = Config.SECRET_KEY
    app.config["JSON_AS_ASCII"] = False
    app.config["_DB_BOOTSTRAPPED"] = False

    @app.before_request
    def _before_request():
        if request.path.startswith("/static/"):
            return
        if Config.AUTO_INIT_DB and not app.config.get("_DB_BOOTSTRAPPED"):
            if auto_init_if_empty():
                app.config["_DB_BOOTSTRAPPED"] = True
        try:
            load_logged_in_user()
        except pymysql.MySQLError:
            # Permitir que el endpoint concreto maneje el error de conexión a BD con claridad
            pass

    app.register_blueprint(web_bp)
    app.register_blueprint(api_bp)

    @app.errorhandler(DomainError)
    def _handle_domain_error(err: DomainError):
        return jsonify(err.to_dict()), err.status_code

    @app.errorhandler(pymysql.MySQLError)
    def _handle_mysql_error(err: pymysql.MySQLError):
        code = err.args[0] if err.args else 0
        if code == 1049:
            msg = (
                f"La base de datos '{Config.DB_NAME}' aún no existe en MySQL. "
                "Ejecuta 'python run.py --init-db' o importa database/schema.sql y database/seed.sql en phpMyAdmin."
            )
        else:
            is_local = Config.DB_HOST in ("127.0.0.1", "localhost", "::1")
            if is_local:
                msg = (
                    "No se pudo conectar a MySQL (XAMPP). Verifica que el servicio 'MySQL Database' "
                    "esté iniciado (en verde) en XAMPP y revisa las credenciales de tu archivo .env."
                )
            else:
                msg = (
                    f"No se pudo conectar al servidor MySQL en la nube ({Config.DB_HOST}:{Config.DB_PORT}). "
                    "Verifica las variables DB_HOST, DB_PORT, DB_USER, DB_PASSWORD y DB_NAME en tu panel de despliegue."
                )
        return jsonify({"ok": False, "error": msg, "code": "DATABASE_UNAVAILABLE"}), 503

    return app
