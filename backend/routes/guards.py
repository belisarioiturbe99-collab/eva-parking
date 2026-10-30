"""Middlewares y decoradores de control de sesión y roles (RBAC)."""

from functools import wraps
from flask import session, g
from backend.services import auth_service
from backend.services.exceptions import DomainError


def load_logged_in_user() -> dict:
    """Carga en flask.g el usuario autenticado de la sesión actual si existe y está activo."""
    user_id = session.get("user_id")
    if not user_id:
        g.current_user = None
        return None

    user = auth_service.get_current_user(user_id)
    if not user:
        session.clear()
        g.current_user = None
        return None

    g.current_user = user
    return user


def require_auth(roles: tuple = None):
    """Decorador que exige sesión activa y opcionalmente valida que el rol esté permitido."""

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = getattr(g, "current_user", None)
            if not user:
                raise DomainError(
                    "Debes iniciar sesión para realizar esta acción.",
                    status_code=401,
                    code="AUTH_REQUIRED",
                )
            if roles and user["rol"] not in roles:
                raise DomainError(
                    "Tu rol de usuario no tiene permisos para acceder a este módulo.",
                    status_code=403,
                    code="FORBIDDEN_ROLE",
                )
            return fn(*args, **kwargs)

        return wrapper

    return decorator
