"""Configuración centralizada de E.V.A cargada desde variables de entorno (.env)."""

import os
import socket
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def detect_lan_ip() -> str:
    """Detecta la IP privada en la red Wi-Fi/LAN actual para acceso desde celulares y otras PCs."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))
            ip = s.getsockname()[0]
            if ip and not ip.startswith("127."):
                return ip
    except Exception:
        pass
    try:
        ip = socket.gethostbyname(socket.gethostname())
        if ip and not ip.startswith("127."):
            return ip
    except Exception:
        pass
    return "127.0.0.1"


class Config:
    """Parámetros de conexión a MySQL (XAMPP o Nube) y servidor Flask / Gunicorn."""

    SECRET_KEY: str = os.getenv("SECRET_KEY", "eva_default_dev_secret_change_me")
    FLASK_ENV: str = os.getenv("FLASK_ENV", "development")
    FLASK_HOST: str = os.getenv("FLASK_HOST", "0.0.0.0")
    FLASK_PORT: int = int(os.getenv("PORT", os.getenv("FLASK_PORT", "5050")))

    DB_HOST: str = os.getenv("DB_HOST", "127.0.0.1").strip()
    DB_PORT: int = int(os.getenv("DB_PORT", "3306"))
    DB_USER: str = os.getenv("DB_USER", "root").strip()
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    DB_NAME: str = os.getenv("DB_NAME", "eva_parking").strip()
    DB_SOCKET: str = os.getenv("DB_SOCKET", "").strip()

    # DB_SSL: 'auto' activa SSL/TLS cuando DB_HOST es un servidor remoto en la nube (ej. Aiven, TiDB, Railway)
    DB_SSL: str = os.getenv("DB_SSL", "auto").strip().lower()
    AUTO_INIT_DB: bool = os.getenv("AUTO_INIT_DB", "false").strip().lower() in ("1", "true", "yes", "si")
