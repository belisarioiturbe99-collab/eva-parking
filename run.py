"""Punto de entrada para ejecutar E.V.A localmente, en red Wi-Fi o inicializar la base de datos en XAMPP."""

import sys
import pymysql
from backend.config import Config, detect_lan_ip
from backend.database import init_database
from backend.app_factory import create_app


def main():
    if "--init-db" in sys.argv:
        with_seed = "--no-seed" not in sys.argv
        print(f"[EVA] Inicializando base de datos '{Config.DB_NAME}' en MySQL (XAMPP)...")
        try:
            init_database(with_seed=with_seed)
            print("[EVA] Base de datos y datos de ejemplo cargados correctamente.")
        except pymysql.MySQLError as exc:
            print(
                "\n[EVA - ERROR DE CONEXIÓN MYSQL]\n"
                "No se pudo conectar al servidor MySQL en XAMPP.\n"
                "1. Abre XAMPP (manager-osx en macOS o XAMPP Control Panel en Windows).\n"
                "2. Inicia el servicio 'MySQL Database' hasta que quede en VERDE.\n"
                "3. Vuelve a ejecutar: python run.py --init-db\n"
                f"Detalle técnico: {exc}"
            )
            sys.exit(1)
        if "--serve" not in sys.argv:
            return

    app = create_app()
    host = Config.FLASK_HOST
    port = Config.FLASK_PORT
    lan_ip = detect_lan_ip()
    debug = Config.FLASK_ENV == "development"

    print("\n" + "=" * 62)
    print("  E.V.A — EXECUTIVE MOBILITY (Servidor Activo)")
    print("=" * 62)
    print(f"  En esta computadora : http://127.0.0.1:{port}")
    print(f"  En celular / Wi-Fi  : http://{lan_ip}:{port}")
    print("=" * 62 + "\n")

    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    main()
