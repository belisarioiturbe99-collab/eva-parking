"""Servicio de Gestión de Vehículos del Usuario y Catálogo de Tipos de Vehículo."""

import re
from backend.database import transaction, read_cursor, serialize_row, serialize_rows
from backend.repositories import vehicle_repo, stay_repo
from backend.services.exceptions import DomainError

PLATE_REGEX = re.compile(r"^[A-Z0-9]{5,10}$")


def normalize_plate(raw_plate: str) -> str:
    """Normaliza patentes eliminando espacios/guiones y convirtiendo a mayúsculas."""
    cleaned = re.sub(r"[\s\-]+", "", (raw_plate or "").strip().upper())
    if not PLATE_REGEX.match(cleaned):
        raise DomainError(
            "La patente debe contener entre 5 y 10 caracteres alfanuméricos sin símbolos (ej: AF420TK o ABC123)."
        )
    return cleaned


def list_active_vehicle_types() -> list:
    with read_cursor() as cursor:
        return serialize_rows(vehicle_repo.list_vehicle_types(cursor, only_active=True))


def list_vehicles_for_user(usuario_id: int) -> list:
    with read_cursor() as cursor:
        return serialize_rows(vehicle_repo.list_user_vehicles(cursor, usuario_id))


def register_user_vehicle(usuario_id: int, payload: dict) -> dict:
    """Registra un vehículo validando formato y unicidad de patente (EP2-HU3)."""
    patente = normalize_plate(payload.get("patente"))
    descripcion = (payload.get("descripcion") or "").strip()[:100]
    try:
        tipo_id = int(payload.get("tipo_vehiculo_id"))
    except (TypeError, ValueError):
        raise DomainError("Debes seleccionar un tipo de vehículo válido.")

    with transaction() as cursor:
        vtype = vehicle_repo.find_vehicle_type(cursor, tipo_id)
        if not vtype or not vtype["activo"]:
            raise DomainError("El tipo de vehículo seleccionado no está disponible.")

        existing = vehicle_repo.find_by_plate(cursor, patente)
        if existing:
            if existing["activo"]:
                raise DomainError(
                    f"La patente {patente} ya se encuentra registrada en el sistema.",
                    status_code=409,
                    code="DUPLICATE_PLATE",
                )
            # Si existía dada de baja anteriormente, se reactiva para el usuario
            vehicle_repo.reactivate_vehicle(cursor, existing["id"], usuario_id, tipo_id, descripcion)
            vid = existing["id"]
        else:
            vid = vehicle_repo.create_vehicle(cursor, usuario_id, tipo_id, patente, descripcion)

        created = vehicle_repo.find_vehicle_by_id(cursor, vid)
        return serialize_row(created)


def remove_user_vehicle(usuario_id: int, vehicle_id: int) -> None:
    """Da de baja lógica un vehículo si no posee una estadía activa en curso."""
    with transaction() as cursor:
        vehicle = vehicle_repo.find_vehicle_by_id(cursor, vehicle_id)
        if not vehicle or not vehicle["activo"] or vehicle["usuario_id"] != usuario_id:
            raise DomainError("Vehículo no encontrado en tu cuenta.", status_code=404)

        active_stay = stay_repo.find_active_stay_by_plate(cursor, vehicle["patente"])
        if active_stay:
            raise DomainError(
                f"No puedes eliminar el vehículo {vehicle['patente']} mientras tiene una estadía activa.",
                status_code=409,
            )

        vehicle_repo.deactivate_vehicle(cursor, vehicle_id, usuario_id)
