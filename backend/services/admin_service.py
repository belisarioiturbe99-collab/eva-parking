"""Servicio de Administración Global — Métricas, Moderación de Usuarios, Locales y Tipos de Vehículo."""

from backend.database import transaction, read_cursor, serialize_row, serialize_rows
from backend.repositories import user_repo, parking_repo, vehicle_repo, stay_repo
from backend.services.exceptions import DomainError


def get_admin_dashboard() -> dict:
    with read_cursor() as cursor:
        metrics = serialize_row(stay_repo.get_global_metrics(cursor))
        users = serialize_rows(user_repo.list_all_users(cursor))
        parkings = serialize_rows(parking_repo.list_all_parkings_admin(cursor))
        vehicle_types = serialize_rows(vehicle_repo.list_vehicle_types(cursor, only_active=False))
        return {
            "metricas": metrics,
            "usuarios": users,
            "estacionamientos": parkings,
            "tipos_vehiculo": vehicle_types,
        }


def set_user_active_status(admin_id: int, target_user_id: int, activo: bool) -> None:
    if admin_id == target_user_id and not activo:
        raise DomainError("No puedes desactivar tu propia cuenta de Administrador.")
    with transaction() as cursor:
        target = user_repo.find_by_id(cursor, target_user_id)
        if not target:
            raise DomainError("Usuario no encontrado.", status_code=404)
        user_repo.toggle_user_active(cursor, target_user_id, 1 if activo else 0)


def set_parking_active_status(parking_id: int, activo: bool) -> None:
    with transaction() as cursor:
        parking = parking_repo.find_parking_by_id(cursor, parking_id)
        if not parking:
            raise DomainError("Estacionamiento no encontrado.", status_code=404)
        parking_repo.toggle_parking_active(cursor, parking_id, 1 if activo else 0)


def add_vehicle_type(payload: dict) -> dict:
    nombre = (payload.get("nombre") or "").strip()
    icono = (payload.get("icono") or "car").strip()[:30]
    descripcion = (payload.get("descripcion") or "").strip()[:150]

    if len(nombre) < 2:
        raise DomainError("El nombre del tipo de vehículo debe tener al menos 2 caracteres.")

    with transaction() as cursor:
        existing = vehicle_repo.find_vehicle_type_by_name(cursor, nombre)
        if existing:
            raise DomainError(f"El tipo de vehículo '{nombre}' ya existe en el catálogo.", status_code=409)
        new_id = vehicle_repo.create_vehicle_type(cursor, nombre, icono, descripcion)
        return serialize_row(vehicle_repo.find_vehicle_type(cursor, new_id))


def set_vehicle_type_status(type_id: int, activo: bool) -> None:
    with transaction() as cursor:
        vtype = vehicle_repo.find_vehicle_type(cursor, type_id)
        if not vtype:
            raise DomainError("Tipo de vehículo no encontrado.", status_code=404)
        vehicle_repo.toggle_vehicle_type(cursor, type_id, 1 if activo else 0)
