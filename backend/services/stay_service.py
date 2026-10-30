"""Servicio Transaccional de Estadías, Facturación Automática, Tickets y Reseñas."""

from decimal import Decimal, ROUND_HALF_UP

from backend.database import transaction, read_cursor, serialize_row, serialize_rows
from backend.repositories import stay_repo, parking_repo, vehicle_repo, user_repo
from backend.services.exceptions import DomainError
from backend.services.pricing_service import calculate_live_charge
from backend.services.vehicle_service import normalize_plate


def _build_ticket_number(estadia_id: int) -> str:
    return f"EVA-2026-{estadia_id:05d}"


def start_user_stay(user: dict, payload: dict) -> dict:
    """
    Inicia una estadía en tiempo real para un Conductor con Sesión:
    1. Verifica que la plaza esté libre (Verde).
    2. Verifica propiedad del vehículo y que no esté ya estacionado.
    3. Verifica que exista tarifa para ese tipo de vehículo.
    4. Valida saldo mínimo en Billetera Virtual (1h o Estadía Fija).
    5. Registra la estadía y cambia la plaza a Rojo (ocupada = 1).
    """
    try:
        plaza_id = int(payload.get("plaza_id"))
        vehiculo_id = int(payload.get("vehiculo_id"))
    except (TypeError, ValueError):
        raise DomainError("Debes seleccionar una plaza y uno de tus vehículos registrados.")

    modalidad = (payload.get("modalidad") or "HORA").strip().upper()
    if modalidad not in ("HORA", "ESTADIA_FIJA"):
        raise DomainError("Modalidad de tarifa inválida. Elige Por Hora o Estadía Fija.")

    with transaction() as cursor:
        spot = stay_repo.find_spot_for_update(cursor, plaza_id)
        if not spot or not spot["activa"] or not spot["estacionamiento_activo"]:
            raise DomainError("La plaza seleccionada no se encuentra disponible.", status_code=404)
        if spot["ocupada"]:
            raise DomainError(
                f"La plaza {spot['codigo']} acaba de ser ocupada. Selecciona otra plaza en verde.",
                status_code=409,
                code="SPOT_ALREADY_OCCUPIED",
            )

        vehicle = vehicle_repo.find_vehicle_by_id(cursor, vehiculo_id)
        if not vehicle or not vehicle["activo"] or vehicle["usuario_id"] != user["id"]:
            raise DomainError("El vehículo seleccionado no pertenece a tu cuenta.", status_code=403)

        already_parked = stay_repo.find_active_stay_by_plate(cursor, vehicle["patente"])
        if already_parked:
            raise DomainError(
                f"Tu vehículo {vehicle['patente']} ya posee una estadía activa en curso.",
                status_code=409,
            )

        tariff = parking_repo.find_tariff(
            cursor, spot["estacionamiento_id"], vehicle["tipo_vehiculo_id"]
        )
        if not tariff:
            raise DomainError(
                f"Este estacionamiento no tiene tarifa configurada para '{vehicle['tipo_nombre']}'.",
                status_code=400,
            )

        required_amount = Decimal(
            str(tariff["precio_hora"] if modalidad == "HORA" else tariff["precio_estadia_fija"])
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        fresh_user = user_repo.find_by_id(cursor, user["id"], for_update=True)
        current_balance = Decimal(str(fresh_user["saldo_billetera"]))
        if current_balance < required_amount:
            faltante = (required_amount - current_balance).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            raise DomainError(
                f"Fondos insuficientes en tu Billetera Virtual. Necesitas al menos ${required_amount:.2f} y tu saldo es ${current_balance:.2f}.",
                status_code=402,
                code="INSUFFICIENT_FUNDS",
                payload={
                    "saldo_actual": float(current_balance),
                    "monto_requerido": float(required_amount),
                    "faltante": float(faltante),
                },
            )

        stay_id = stay_repo.create_stay(
            cursor,
            estacionamiento_id=spot["estacionamiento_id"],
            plaza_id=spot["id"],
            usuario_id=user["id"],
            vehiculo_id=vehicle["id"],
            tipo_vehiculo_id=vehicle["tipo_vehiculo_id"],
            patente_snapshot=vehicle["patente"],
            nombre_cliente_snapshot=fresh_user["nombre"],
            modalidad=modalidad,
            tarifa_aplicada=required_amount,
            origen="APP_USUARIO",
        )
        stay_repo.set_spot_occupied(cursor, spot["id"], 1)

    return {
        "estadia_id": stay_id,
        "plaza_codigo": spot["codigo"],
        "estacionamiento_nombre": spot["estacionamiento_nombre"],
        "patente": vehicle["patente"],
        "modalidad": modalidad,
        "tarifa_aplicada": float(required_amount),
    }


def start_manual_desk_stay(owner_user: dict, payload: dict) -> dict:
    """Permite al Propietario ocupar manualmente una plaza libre desde su grilla para un cliente presencial."""
    try:
        plaza_id = int(payload.get("plaza_id"))
        tipo_vehiculo_id = int(payload.get("tipo_vehiculo_id"))
    except (TypeError, ValueError):
        raise DomainError("Debes indicar la plaza y el tipo de vehículo.")

    patente = normalize_plate(payload.get("patente"))
    nombre_cliente = (payload.get("nombre_cliente") or "Cliente Mostrador").strip()[:100]
    modalidad = (payload.get("modalidad") or "HORA").strip().upper()
    if modalidad not in ("HORA", "ESTADIA_FIJA"):
        raise DomainError("Modalidad inválida.")

    with transaction() as cursor:
        spot = stay_repo.find_spot_for_update(cursor, plaza_id)
        if not spot or not spot["activa"]:
            raise DomainError("Plaza no encontrada.", status_code=404)

        if owner_user["rol"] != "ADMIN" and spot["propietario_id"] != owner_user["id"]:
            raise DomainError("No tienes permiso para operar plazas de otro estacionamiento.", status_code=403)

        if spot["ocupada"]:
            raise DomainError(f"La plaza {spot['codigo']} ya se encuentra ocupada.", status_code=409)

        already_parked = stay_repo.find_active_stay_by_plate(cursor, patente)
        if already_parked:
            raise DomainError(f"El vehículo {patente} ya figura estacionado en una plaza activa.", status_code=409)

        tariff = parking_repo.find_tariff(cursor, spot["estacionamiento_id"], tipo_vehiculo_id)
        if not tariff:
            raise DomainError("No configuraste una tarifa para ese tipo de vehículo en tu local.")

        rate = Decimal(
            str(tariff["precio_hora"] if modalidad == "HORA" else tariff["precio_estadia_fija"])
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        stay_id = stay_repo.create_stay(
            cursor,
            estacionamiento_id=spot["estacionamiento_id"],
            plaza_id=spot["id"],
            usuario_id=None,
            vehiculo_id=None,
            tipo_vehiculo_id=tipo_vehiculo_id,
            patente_snapshot=patente,
            nombre_cliente_snapshot=nombre_cliente,
            modalidad=modalidad,
            tarifa_aplicada=rate,
            origen="MOSTRADOR_PROPIETARIO",
        )
        stay_repo.set_spot_occupied(cursor, spot["id"], 1)

    return {"estadia_id": stay_id, "plaza_codigo": spot["codigo"], "patente": patente}


def checkout_stay(actor_user: dict, estadia_id: int, cobro_mostrador: bool = False) -> dict:
    """
    Finaliza una estadía activa de forma atómica:
    1. Calcula tiempo exacto en servidor y monto total dinámico.
    2. Si es estadía de App, debita automáticamente de la Billetera Virtual del conductor
       y acredita en la cuenta del Propietario (salvo cobro en efectivo autorizado por Propietario).
    3. Libera la plaza pasándola de Rojo a Verde (ocupada = 0).
    4. Emite el Comprobante / Ticket digital imprimible (EP4-HU2).
    """
    with transaction() as cursor:
        stay = stay_repo.find_stay_for_checkout(cursor, estadia_id)
        if not stay:
            raise DomainError("Estadía no encontrada.", status_code=404)
        if stay["estado"] != "ACTIVA":
            raise DomainError("Esta estadía ya fue finalizada y facturada anteriormente.", status_code=409)

        is_stay_driver = stay["usuario_id"] and stay["usuario_id"] == actor_user["id"]
        is_parking_owner = stay["propietario_id"] == actor_user["id"]
        is_admin = actor_user["rol"] == "ADMIN"

        if not (is_stay_driver or is_parking_owner or is_admin):
            raise DomainError("No tienes permisos para finalizar esta estadía.", status_code=403)

        minutos, monto_total = calculate_live_charge(
            stay["modalidad"], stay["tarifa_aplicada"], stay["segundos_transcurridos"]
        )

        use_wallet = stay["origen"] == "APP_USUARIO" and stay["usuario_id"] is not None
        if cobro_mostrador and (is_parking_owner or is_admin):
            use_wallet = False

        if use_wallet:
            driver = user_repo.find_by_id(cursor, stay["usuario_id"], for_update=True)
            driver_balance = Decimal(str(driver["saldo_billetera"]))
            if driver_balance < monto_total:
                faltante = (monto_total - driver_balance).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                raise DomainError(
                    f"Saldo insuficiente para finalizar la estadía (${monto_total:.2f}). Saldo disponible: ${driver_balance:.2f}. Faltan ${faltante:.2f}.",
                    status_code=402,
                    code="INSUFFICIENT_FUNDS",
                    payload={
                        "estadia_id": estadia_id,
                        "saldo_actual": float(driver_balance),
                        "monto_requerido": float(monto_total),
                        "faltante": float(faltante),
                    },
                )

            new_driver_balance = (driver_balance - monto_total).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            user_repo.update_wallet_balance(cursor, driver["id"], new_driver_balance)
            user_repo.insert_wallet_movement(
                cursor,
                usuario_id=driver["id"],
                estadia_id=estadia_id,
                tipo="PAGO_ESTADIA",
                monto=-monto_total,
                saldo_posterior=new_driver_balance,
                descripcion=f"Pago estadía en {stay['estacionamiento_nombre']} (Plaza {stay['plaza_codigo']} - {stay['patente_snapshot']})",
            )

            owner = user_repo.find_by_id(cursor, stay["propietario_id"], for_update=True)
            new_owner_balance = (Decimal(str(owner["saldo_billetera"])) + monto_total).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            user_repo.update_wallet_balance(cursor, owner["id"], new_owner_balance)
            user_repo.insert_wallet_movement(
                cursor,
                usuario_id=owner["id"],
                estadia_id=estadia_id,
                tipo="ACREDITACION_PROPIETARIO",
                monto=monto_total,
                saldo_posterior=new_owner_balance,
                descripcion=f"Cobro estadía Plaza {stay['plaza_codigo']} - Patente {stay['patente_snapshot']}",
            )
            metodo_pago = "BILLETERA_VIRTUAL"
        else:
            # Cobro presencial en mostrador: se registra acreditación contable al propietario
            owner = user_repo.find_by_id(cursor, stay["propietario_id"], for_update=True)
            new_owner_balance = (Decimal(str(owner["saldo_billetera"])) + monto_total).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            user_repo.update_wallet_balance(cursor, owner["id"], new_owner_balance)
            user_repo.insert_wallet_movement(
                cursor,
                usuario_id=owner["id"],
                estadia_id=estadia_id,
                tipo="ACREDITACION_PROPIETARIO",
                monto=monto_total,
                saldo_posterior=new_owner_balance,
                descripcion=f"Cobro en mostrador Plaza {stay['plaza_codigo']} - Patente {stay['patente_snapshot']}",
            )
            metodo_pago = "EFECTIVO_MOSTRADOR"

        stay_repo.finalize_stay(cursor, estadia_id, minutos, monto_total)
        stay_repo.set_spot_occupied(cursor, stay["plaza_id"], 0)

        ticket_num = _build_ticket_number(estadia_id)
        stay_repo.create_receipt(cursor, estadia_id, ticket_num, metodo_pago, monto_total)
        receipt = stay_repo.find_receipt_details(cursor, estadia_id)
        return serialize_row(receipt)


def get_driver_stays(usuario_id: int) -> dict:
    """Devuelve las estadías activas con cálculo dinámico en vivo y el historial finalizado del conductor."""
    with read_cursor() as cursor:
        active_raw = stay_repo.list_active_stays_by_user(cursor, usuario_id)
        history_raw = stay_repo.list_history_by_user(cursor, usuario_id, limit=25)

        activas = []
        for row in active_raw:
            item = serialize_row(row)
            mins, monto = calculate_live_charge(
                item["modalidad"], item["tarifa_aplicada"], item["segundos_transcurridos"]
            )
            item["minutos_cobrables"] = mins
            item["monto_acumulado"] = float(monto)
            activas.append(item)

        return {
            "activas": activas,
            "historial": serialize_rows(history_raw),
        }


def get_ticket(actor_user: dict, estadia_id: int) -> dict:
    with read_cursor() as cursor:
        receipt = stay_repo.find_receipt_details(cursor, estadia_id)
        if not receipt:
            raise DomainError("Comprobante no encontrado.", status_code=404)

        is_owner = receipt["propietario_id"] == actor_user["id"]
        is_driver = receipt["usuario_id"] and receipt["usuario_id"] == actor_user["id"]
        if not (is_owner or is_driver or actor_user["rol"] == "ADMIN"):
            raise DomainError("No tienes permiso para ver este comprobante.", status_code=403)

        return serialize_row(receipt)


def create_stay_review(user: dict, estadia_id: int, payload: dict) -> dict:
    """Permite al conductor calificar (1 a 5 estrellas) y reseñar su estadía finalizada (EP5-HU1)."""
    try:
        estrellas = int(payload.get("estrellas"))
    except (TypeError, ValueError):
        raise DomainError("Selecciona una calificación entre 1 y 5 estrellas.")

    if not (1 <= estrellas <= 5):
        raise DomainError("La calificación debe estar entre 1 y 5 estrellas.")

    comentario = (payload.get("comentario") or "").strip()[:300]

    with transaction() as cursor:
        stay = stay_repo.find_stay_for_review(cursor, estadia_id)
        if not stay or stay["usuario_id"] != user["id"]:
            raise DomainError("No se encontró la estadía en tu historial.", status_code=404)
        if stay["estado"] != "FINALIZADA":
            raise DomainError("Solo puedes calificar estadías que ya hayan finalizado.")
        if stay["resena_existente_id"]:
            raise DomainError("Ya registraste una reseña para esta estadía.", status_code=409)

        review_id = stay_repo.create_review(
            cursor,
            estadia_id=estadia_id,
            usuario_id=user["id"],
            estacionamiento_id=stay["estacionamiento_id"],
            estrellas=estrellas,
            comentario=comentario,
        )
        return {"id": review_id, "estadia_id": estadia_id, "estrellas": estrellas, "comentario": comentario}
