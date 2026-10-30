"""Punto de entrada WSGI de producción para Gunicorn (Render, Railway, etc.)."""

from backend.app_factory import create_app

app = create_app()
