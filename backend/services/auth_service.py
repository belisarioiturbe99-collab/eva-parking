"""Servicio de Autenticación, Encriptación de Contraseñas y Control de Roles."""

import re
from werkzeug.security import generate_password_hash, check_password_hash

from backend.database import transaction, read_cursor, serialize_row
from backend.repositories import user_repo, parking_repo, vehicle_repo
from backend.services.exceptions import DomainError

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PASSWORD_HASH_METHOD = "pbkdf2:sha256"


def _sanitize_user(user_row: dict) -> dict:
    if not user_row:
        return None
    clean = serialize_row(user_row)
    clean.pop("password_hash", None)
    return clean


def register_user(payload: dict) -> dict:
    """
    Registra un nuevo usuario (USUARIO o PROPIETARIO).
    Si el rol es PROPIETARIO, crea automáticamente su estacionamiento 1 a 1 y sus plazas iniciales.
    """
    nombre = (payload.get("nombre") or "").strip()
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""
    rol = (payload.get("rol") or "USUARIO").strip().upper()

    if len(nombre) < 3:
        raise DomainError("El nombre completo debe tener al menos 3 caracteres.")
    if not EMAIL_REGEX.match(email):
        raise DomainError("Ingresa una dirección de correo electrónico válida.")
    if len(password) < 6:
        raise DomainError("La contraseña debe tener al menos 6 caracteres.")
    if rol not in ("USUARIO", "PROPIETARIO"):
        raise DomainError("Rol de registro inválido. Selecciona Conductor o Propietario.")

    # Validaciones previas si se registra como Propietario (relación 1 a 1 inmediata)
    est_nombre = (payload.get("nombre_estacionamiento") or f"Parking de {nombre}").strip()
    est_direccion = (payload.get("direccion_estacionamiento") or "Dirección a configurar").strip()
    est_ciudad = (payload.get("ciudad_estacionamiento") or "San Miguel de Tucumán").strip()
    try:
        est_plazas = int(payload.get("cantidad_plazas") or 10)
    except (TypeError, ValueError):
        raise DomainError("La cantidad de plazas debe ser un número entero válido.")

    if rol == "PROPIETARIO":
        if len(est_nombre) < 3:
            raise DomainError("El nombre del estacionamiento debe tener al menos 3 caracteres.")
        if len(est_direccion) < 4:
            raise DomainError("Ingresa una dirección válida para tu estacionamiento.")
        if not (1 <= est_plazas <= 200):
            raise DomainError("La cantidad de plazas debe estar entre 1 y 200.")

    password_hash = generate_password_hash(password, method=PASSWORD_HASH_METHOD)

    with transaction() as cursor:
        existing = user_repo.find_by_email(cursor, email)
        if existing:
            raise DomainError(
                "Ya existe una cuenta registrada con ese correo electrónico.",
                status_code=409,
                code="DUPLICATE_EMAIL",
            )

        user_id = user_repo.create_user(cursor, nombre, email, password_hash, rol)

        if rol == "PROPIETARIO":
            lat = float(payload.get("latitud") or -26.83037)
            lng = float(payload.get("longitud") or -65.20381)
            techado = 1 if payload.get("techado", True) else 0
            horario = (payload.get("horario_texto") or "24 Horas").strip()

            parking_id = parking_repo.create_parking(
                cursor,
                propietario_id=user_id,
                nombre=est_nombre,
                direccion=est_direccion,
                ciudad=est_ciudad,
                latitud=lat,
                longitud=lng,
                cantidad_plazas=est_plazas,
                horario_texto=horario,
                techado=techado,
            )
            for num in range(1, est_plazas + 1):
                codigo = f"P-{num:02d}"
                parking_repo.create_spot(cursor, parking_id, num, codigo)

            # Crear tarifas iniciales por defecto para que el local sea operativo al instante
            tipos = vehicle_repo.list_vehicle_types(cursor, only_active=True)
            defaults = {"Auto": (1500, 8000), "Moto": (800, 4000), "Camioneta": (2200, 11500)}
            for tv in tipos:
                ph, pf = defaults.get(tv["nombre"], (1800, 9000))
                parking_repo.upsert_tariff(cursor, parking_id, tv["id"], ph, pf)

        created = user_repo.find_by_id(cursor, user_id)
        return _sanitize_user(created)


def authenticate_user(email: str, password: str) -> dict:
    """Valida credenciales encriptadas y estado activo de la cuenta (EP2-HU2)."""
    clean_email = (email or "").strip().lower()
    raw_password = password or ""

    if not clean_email or not raw_password:
        raise DomainError("Debes ingresar tu correo electrónico y contraseña.")

    with read_cursor() as cursor:
        user = user_repo.find_by_email(cursor, clean_email)
        if not user or not check_password_hash(user["password_hash"], raw_password):
            raise DomainError(
                "Credenciales incorrectas. Verifica tu correo y contraseña.",
                status_code=401,
                code="INVALID_CREDENTIALS",
            )
        if not user["activo"]:
            raise DomainError(
                "Tu cuenta se encuentra suspendida por el Administrador.",
                status_code=403,
                code="ACCOUNT_DISABLED",
            )
        return _sanitize_user(user)


def get_current_user(user_id: int) -> dict:
    if not user_id:
        return None
    with read_cursor() as cursor:
        user = user_repo.find_by_id(cursor, user_id)
        if not user or not user["activo"]:
            return None
        return _sanitize_user(user)


def update_user_profile(user_id: int, nombre: str) -> dict:
    clean_name = (nombre or "").strip()
    if len(clean_name) < 3:
        raise DomainError("El nombre debe tener al menos 3 caracteres.")
    with transaction() as cursor:
        user_repo.update_profile(cursor, user_id, clean_name)
        updated = user_repo.find_by_id(cursor, user_id)
        return _sanitize_user(updated)
