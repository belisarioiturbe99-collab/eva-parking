"""Servicio de Gestión de Estacionamientos, Grilla de Plazas Estilo Restaurante y Tarifas."""

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from backend.database import transaction, read_cursor, serialize_row, serialize_rows
from backend.repositories import parking_repo, stay_repo, vehicle_repo
from backend.services.exceptions import DomainError
from backend.services.pricing_service import calculate_live_charge


def list_catalog(filters: dict, current_user: dict = None) -> dict:
    """
    Lista estacionamientos activos para el Mapa y Explorador.
    Regla EP1-HU2: Los Visitantes (sin sesión) pueden buscar por texto/ubicación,
    pero los filtros avanzados requieren haber iniciado sesión.
    """
    search = (filters.get("search") or "").strip() or None
    is_logged_in = current_user is not None

    tipo_id = None
    max_precio = None
    solo_techado = False
    solo_disponibles = False
    filtros_aplicados = False

    if is_logged_in:
        if filters.get("tipo_vehiculo_id"):
            try:
                tipo_id = int(filters["tipo_vehiculo_id"])
                filtros_aplicados = True
            except (TypeError, ValueError):
                raise DomainError("Filtro de tipo de vehículo inválido.")

        if filters.get("max_precio_hora"):
            try:
                max_precio = float(filters["max_precio_hora"])
                if max_precio <= 0:
                    raise DomainError("El filtro de precio máximo debe ser mayor a cero.")
                filtros_aplicados = True
            except (TypeError, ValueError):
                raise DomainError("Filtro de precio máximo inválido.")

        solo_techado = str(filters.get("solo_techado", "")).lower() in ("1", "true", "si")
        solo_disponibles = str(filters.get("solo_disponibles", "")).lower() in ("1", "true", "si")
        if solo_techado or solo_disponibles:
            filtros_aplicados = True

    with read_cursor() as cursor:
        rows = parking_repo.list_parkings_public(
            cursor,
            search=search,
            tipo_vehiculo_id=tipo_id,
            max_precio_hora=max_precio,
            solo_techado=solo_techado,
            solo_disponibles=solo_disponibles,
        )
        parkings = serialize_rows(rows)
        parking_ids = [p["id"] for p in parkings]
        all_tariffs = serialize_rows(parking_repo.list_tariffs_for_parkings(cursor, parking_ids))

        tariffs_by_parking = {}
        for t in all_tariffs:
            tariffs_by_parking.setdefault(t["estacionamiento_id"], []).append(t)

        for p in parkings:
            p["tarifas"] = tariffs_by_parking.get(p["id"], [])

        return {
            "estacionamientos": parkings,
            "filtros_habilitados": is_logged_in,
            "filtros_aplicados": filtros_aplicados,
        }


def _enrich_spots_grid(spots_raw: list, viewer: dict, owner_id: int) -> list:
    """Enriquece cada plaza con estado Verde/Rojo y cálculo de tarifa acumulada en tiempo real."""
    viewer_id = viewer["id"] if viewer else None
    viewer_role = viewer["rol"] if viewer else "VISITANTE"
    is_privileged = viewer_role == "ADMIN" or (viewer_id and viewer_id == owner_id)

    grid = []
    for sp in spots_raw:
        item = serialize_row(sp)
        ocupada = bool(item["ocupada"])
        item["ocupada"] = ocupada
        item["color_estado"] = "ROJO" if ocupada else "VERDE"

        if ocupada and item.get("estadia_id"):
            is_own_stay = viewer_id and item.get("estadia_usuario_id") == viewer_id
            mins, monto = calculate_live_charge(
                item["modalidad"], item["tarifa_aplicada"], item["segundos_transcurridos"]
            )
            item["minutos_cobrables"] = mins
            item["monto_acumulado"] = float(monto)
            item["es_mi_estadia"] = bool(is_own_stay)

            # Privacidad: visitantes y otros conductores ven plaza Roja ocupada (y tipo de vehículo),
            # mientras que el Propietario, el Admin y el propio Conductor ven patente y detalle completo.
            if not (is_privileged or is_own_stay):
                plate = item.get("patente_snapshot") or ""
                item["patente_snapshot"] = f"{plate[:2]}***{plate[-2:]}" if len(plate) >= 5 else "OCUPADA"
                item["nombre_cliente_snapshot"] = None
        else:
            item["minutos_cobrables"] = 0
            item["monto_acumulado"] = 0.0
            item["es_mi_estadia"] = False

        grid.append(item)
    return grid


def get_parking_live_detail(parking_id: int, current_user: dict = None) -> dict:
    """Obtiene ficha completa del estacionamiento, tarifas, reseñas y grilla Verde/Rojo en vivo."""
    with read_cursor() as cursor:
        parking = parking_repo.find_parking_by_id(cursor, parking_id)
        if not parking or (not parking["activo"] and (not current_user or current_user["rol"] != "ADMIN")):
            raise DomainError("Estacionamiento no encontrado o inactivo.", status_code=404)

        spots_raw = parking_repo.list_spots_with_live_stay(cursor, parking_id)
        tariffs = parking_repo.list_tariffs(cursor, parking_id)
        reviews = parking_repo.list_reviews(cursor, parking_id, limit=15)

        grid = _enrich_spots_grid(spots_raw, current_user, parking["propietario_id"])
        total = len(grid)
        ocupadas = sum(1 for s in grid if s["ocupada"])
        libres = total - ocupadas

        data = serialize_row(parking)
        data["plazas_totales"] = total
        data["plazas_ocupadas"] = ocupadas
        data["plazas_libres"] = libres
        data["porcentaje_ocupacion"] = round((ocupadas / total) * 100, 1) if total > 0 else 0.0
        data["plazas"] = grid
        data["tarifas"] = serialize_rows(tariffs)
        data["resenas"] = serialize_rows(reviews)
        return data


def get_owner_dashboard(owner_user: dict) -> dict:
    """Obtiene el panel integral en tiempo real para el Propietario del Estacionamiento."""
    with read_cursor() as cursor:
        parking = parking_repo.find_parking_by_owner(cursor, owner_user["id"])
        if not parking:
            return {"tiene_estacionamiento": False}

        pid = parking["id"]
        spots_raw = parking_repo.list_spots_with_live_stay(cursor, pid)
        tariffs = parking_repo.list_tariffs(cursor, pid)
        all_types = vehicle_repo.list_vehicle_types(cursor, only_active=True)
        metrics = stay_repo.get_owner_metrics(cursor, pid)
        recent_stays = stay_repo.list_recent_stays_by_parking(cursor, pid, limit=20)
        reviews = parking_repo.list_reviews(cursor, pid, limit=10)

        grid = _enrich_spots_grid(spots_raw, owner_user, owner_user["id"])
        total = len(grid)
        ocupadas = sum(1 for s in grid if s["ocupada"])
        acumulado_en_curso = round(sum(s["monto_acumulado"] for s in grid if s["ocupada"]), 2)

        return {
            "tiene_estacionamiento": True,
            "estacionamiento": serialize_row(parking),
            "resumen": {
                "plazas_totales": total,
                "plazas_ocupadas": ocupadas,
                "plazas_libres": total - ocupadas,
                "porcentaje_ocupacion": round((ocupadas / total) * 100, 1) if total > 0 else 0.0,
                "monto_en_curso_vivo": acumulado_en_curso,
                **serialize_row(metrics),
            },
            "plazas": grid,
            "tarifas": serialize_rows(tariffs),
            "tipos_vehiculo": serialize_rows(all_types),
            "actividad_reciente": serialize_rows(recent_stays),
            "resenas": serialize_rows(reviews),
        }


def save_owner_parking_config(owner_id: int, payload: dict) -> dict:
    """
    Crea (si aún no tuviera) o actualiza los datos del estacionamiento 1 a 1 del Propietario
    y redimensiona dinámicamente la cantidad N de plazas (P-01..P-N) sin perder historial.
    """
    nombre = (payload.get("nombre") or "").strip()
    direccion = (payload.get("direccion") or "").strip()
    ciudad = (payload.get("ciudad") or "San Miguel de Tucumán").strip()
    horario = (payload.get("horario_texto") or "24 Horas").strip()
    techado = 1 if payload.get("techado") in (True, 1, "1", "true") else 0

    if len(nombre) < 3:
        raise DomainError("El nombre del estacionamiento debe tener al menos 3 caracteres.")
    if len(direccion) < 4:
        raise DomainError("La dirección debe tener al menos 4 caracteres.")

    try:
        cantidad_plazas = int(payload.get("cantidad_plazas"))
    except (TypeError, ValueError):
        raise DomainError("La cantidad total de plazas debe ser un número entero.")

    if not (1 <= cantidad_plazas <= 200):
        raise DomainError("La cantidad total de plazas debe estar entre 1 y 200.")

    try:
        latitud = float(payload.get("latitud", -26.83037))
        longitud = float(payload.get("longitud", -65.20381))
    except (TypeError, ValueError):
        raise DomainError("Las coordenadas geográficas ingresadas no son válidas.")

    if not (-90 <= latitud <= 90) or not (-180 <= longitud <= 180):
        raise DomainError("Las coordenadas deben estar dentro de rangos geográficos válidos.")

    with transaction() as cursor:
        existing = parking_repo.find_parking_by_owner(cursor, owner_id)
        if not existing:
            pid = parking_repo.create_parking(
                cursor,
                propietario_id=owner_id,
                nombre=nombre,
                direccion=direccion,
                ciudad=ciudad,
                latitud=latitud,
                longitud=longitud,
                cantidad_plazas=cantidad_plazas,
                horario_texto=horario,
                techado=techado,
            )
            for num in range(1, cantidad_plazas + 1):
                parking_repo.create_spot(cursor, pid, num, f"P-{num:02d}")
        else:
            pid = existing["id"]
            all_spots = parking_repo.list_all_spots(cursor, pid, for_update=True)
            spots_by_num = {s["numero"]: s for s in all_spots}

            # Verificar que ninguna plaza que quedaría fuera del nuevo límite N esté ocupada
            occupied_above = [
                s["codigo"]
                for s in all_spots
                if s["numero"] > cantidad_plazas and s["activa"] and s["ocupada"]
            ]
            if occupied_above:
                raise DomainError(
                    f"No se puede reducir a {cantidad_plazas} plazas porque actualmente están ocupadas: {', '.join(occupied_above)}.",
                    status_code=409,
                )

            parking_repo.update_parking(
                cursor,
                parking_id=pid,
                nombre=nombre,
                direccion=direccion,
                ciudad=ciudad,
                latitud=latitud,
                longitud=longitud,
                cantidad_plazas=cantidad_plazas,
                horario_texto=horario,
                techado=techado,
            )

            # Activar o crear plazas 1..N
            for num in range(1, cantidad_plazas + 1):
                if num in spots_by_num:
                    if not spots_by_num[num]["activa"]:
                        parking_repo.set_spot_active(cursor, spots_by_num[num]["id"], 1)
                else:
                    parking_repo.create_spot(cursor, pid, num, f"P-{num:02d}")

            # Desactivar plazas > N
            for s in all_spots:
                if s["numero"] > cantidad_plazas and s["activa"]:
                    parking_repo.set_spot_active(cursor, s["id"], 0)

        updated = parking_repo.find_parking_by_id(cursor, pid)
        return serialize_row(updated)


def save_owner_tariffs(owner_id: int, tariffs_list: list) -> list:
    """Actualiza la matriz de tarifas (Por Hora y Estadía Fija) del estacionamiento del Propietario."""
    if not isinstance(tariffs_list, list) or not tariffs_list:
        raise DomainError("Debes enviar al menos una tarifa configurada.")

    with transaction() as cursor:
        parking = parking_repo.find_parking_by_owner(cursor, owner_id)
        if not parking:
            raise DomainError("Primero debes configurar los datos de tu estacionamiento.", status_code=404)

        pid = parking["id"]
        saved_count = 0

        for item in tariffs_list:
            habilitado = item.get("habilitado", True)
            try:
                tipo_id = int(item.get("tipo_vehiculo_id"))
            except (TypeError, ValueError):
                raise DomainError("Tipo de vehículo inválido en la configuración de tarifas.")

            if not habilitado:
                parking_repo.delete_tariff(cursor, pid, tipo_id)
                continue

            try:
                p_hora = Decimal(str(item.get("precio_hora"))).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                p_fija = Decimal(str(item.get("precio_estadia_fija"))).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
            except (InvalidOperation, TypeError, ValueError):
                raise DomainError("Los precios de tarifa deben ser valores numéricos válidos.")

            if p_hora <= 0 or p_fija <= 0:
                raise DomainError("Las tarifas por hora y por estadía fija deben ser mayores a $0.")

            parking_repo.upsert_tariff(cursor, pid, tipo_id, p_hora, p_fija)
            saved_count += 1

        if saved_count == 0:
            raise DomainError("Tu estacionamiento debe tener tarifas activas para al menos un tipo de vehículo.")

        return serialize_rows(parking_repo.list_tariffs(cursor, pid))
