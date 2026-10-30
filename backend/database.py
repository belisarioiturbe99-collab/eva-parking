"""Capa de Datos — Gestión de conexiones MySQL (XAMPP local y MySQL Cloud con SSL/TLS)."""

from contextlib import contextmanager
from decimal import Decimal
from datetime import datetime, date
import os
import ssl
from pathlib import Path
import pymysql
from pymysql.cursors import DictCursor

from backend.config import Config, BASE_DIR

XAMPP_MAC_SOCKET = "/Applications/XAMPP/xamppfiles/var/mysql/mysql.sock"


def _is_local_host() -> bool:
    return Config.DB_HOST in ("127.0.0.1", "localhost", "::1")


def _should_use_ssl() -> bool:
    if Config.DB_SSL in ("1", "true", "yes", "required"):
        return True
    if Config.DB_SSL in ("0", "false", "no", "disabled"):
        return False
    return not _is_local_host()


def _build_ssl_context():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _build_connection_kwargs(include_db: bool = True, force_tcp: bool = False) -> dict:
    """Construye los argumentos de conexión compatibles con XAMPP local y MySQL Cloud (Aiven/TiDB/Railway)."""
    kwargs = {
        "user": Config.DB_USER,
        "password": Config.DB_PASSWORD,
        "charset": "utf8mb4",
        "cursorclass": DictCursor,
        "autocommit": False,
        "connect_timeout": 12,
    }
    if include_db:
        kwargs["database"] = Config.DB_NAME

    if not force_tcp and Config.DB_SOCKET and os.path.exists(Config.DB_SOCKET):
        kwargs["unix_socket"] = Config.DB_SOCKET
    elif not force_tcp and _is_local_host() and os.path.exists(XAMPP_MAC_SOCKET):
        kwargs["unix_socket"] = XAMPP_MAC_SOCKET
    else:
        kwargs["host"] = "127.0.0.1" if Config.DB_HOST == "localhost" else Config.DB_HOST
        kwargs["port"] = Config.DB_PORT
        if _should_use_ssl():
            kwargs["ssl"] = _build_ssl_context()

    return kwargs


def get_connection(include_db: bool = True) -> pymysql.connections.Connection:
    """Abre y retorna una nueva conexión a MySQL."""
    try:
        return pymysql.connect(**_build_connection_kwargs(include_db=include_db, force_tcp=False))
    except pymysql.OperationalError:
        if _is_local_host():
            return pymysql.connect(**_build_connection_kwargs(include_db=include_db, force_tcp=True))
        raise


@contextmanager
def transaction():
    """Context manager transaccional ACID: hace COMMIT al salir sin errores o ROLLBACK si falla."""
    conn = get_connection(include_db=True)
    try:
        with conn.cursor() as cursor:
            yield cursor
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@contextmanager
def read_cursor():
    """Context manager de solo lectura para consultas SELECT."""
    conn = get_connection(include_db=True)
    try:
        with conn.cursor() as cursor:
            yield cursor
    finally:
        conn.close()


def serialize_row(row: dict) -> dict:
    """Convierte tipos Decimal y datetime de MySQL a tipos serializables en JSON."""
    if row is None:
        return None
    out = {}
    for key, val in row.items():
        if isinstance(val, Decimal):
            out[key] = float(val)
        elif isinstance(val, (datetime, date)):
            out[key] = val.strftime("%Y-%m-%d %H:%M:%S")
        else:
            out[key] = val
    return out


def serialize_rows(rows: list) -> list:
    """Serializa una lista de diccionarios provenientes de MySQL."""
    return [serialize_row(r) for r in (rows or [])]


def _ensure_database_exists() -> None:
    """Intenta conectarse a DB_NAME; si no existe (ej. XAMPP local nuevo), la crea."""
    try:
        conn = get_connection(include_db=True)
        conn.close()
    except pymysql.MySQLError as exc:
        code = exc.args[0] if exc.args else 0
        if code == 1049:
            safe_db = Config.DB_NAME.replace("`", "")
            conn = get_connection(include_db=False)
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        f"CREATE DATABASE IF NOT EXISTS `{safe_db}` "
                        "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                    )
                conn.commit()
            finally:
                conn.close()
        else:
            raise


def execute_sql_script(script_path: Path) -> None:
    """
    Ejecuta un archivo .sql sentencia por sentencia directamente sobre Config.DB_NAME.
    Omite CREATE DATABASE y USE para ser 100% compatible con bases MySQL en la nube
    (como 'defaultdb' en Aiven o 'railway' en Railway) además de XAMPP local.
    """
    sql_text = script_path.read_text(encoding="utf-8")
    statements = []
    current = []
    for line in sql_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            continue
        current.append(line)
        if stripped.endswith(";"):
            stmt = "\n".join(current).strip()[:-1].strip()
            current = []
            if not stmt:
                continue
            upper_prefix = " ".join(stmt.upper().split()[:2])
            if upper_prefix.startswith("CREATE DATABASE") or upper_prefix.startswith("USE "):
                continue
            statements.append(stmt)

    conn = get_connection(include_db=True)
    try:
        with conn.cursor() as cursor:
            for stmt in statements:
                cursor.execute(stmt)
        conn.commit()
    finally:
        conn.close()


def init_database(with_seed: bool = True) -> None:
    """Inicializa el esquema de base de datos y opcionalmente carga los datos semilla."""
    _ensure_database_exists()
    schema_path = BASE_DIR / "database" / "schema.sql"
    seed_path = BASE_DIR / "database" / "seed.sql"
    execute_sql_script(schema_path)
    if with_seed and seed_path.exists():
        execute_sql_script(seed_path)


def auto_init_if_empty() -> bool:
    """
    Si AUTO_INIT_DB=true (ideal para primer despliegue en Render/Railway sin consola SSH),
    toma un candado distribuido en MySQL (GET_LOCK) y verifica si el esquema completo ('resenas') existe;
    solo si la base está vacía crea las 10 tablas y carga seed.sql sin condiciones de carrera entre workers.
    Nunca sobrescribe datos existentes en reinicios posteriores.
    """
    if not Config.AUTO_INIT_DB:
        return True
    conn = None
    try:
        _ensure_database_exists()
        conn = get_connection(include_db=True)
        with conn.cursor() as cursor:
            cursor.execute("SELECT GET_LOCK('eva_auto_init_lock', 30) AS locked")
            lock_row = cursor.fetchone() or {}
            has_lock = bool(lock_row.get("locked"))
            try:
                cursor.execute("SHOW TABLES LIKE 'resenas'")
                exists = cursor.fetchone()
                if not exists:
                    print(f"[EVA] Base '{Config.DB_NAME}' vacía detectada. Ejecutando inicialización automática...")
                    init_database(with_seed=True)
                    print("[EVA] Tablas y datos iniciales cargados con éxito en la nube.")
            finally:
                if has_lock:
                    cursor.execute("SELECT RELEASE_LOCK('eva_auto_init_lock')")
        return True
    except Exception as exc:
        print(f"[EVA] Aviso en auto_init_if_empty: {exc}")
        return False
    finally:
        if conn is not None:
            conn.close()
