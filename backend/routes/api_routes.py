"""Endpoints de la API REST de E.V.A (Comunicación JSON entre Presentación y Negocio)."""

from flask import Blueprint, request, jsonify, session, g

from backend.config import Config, detect_lan_ip
from backend.database import read_cursor
from backend.routes.guards import require_auth
from backend.services import (
    auth_service,
    vehicle_service,
    wallet_service,
    parking_service,
    stay_service,
    admin_service,
)

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.get("/health")
def health_check():
    with read_cursor() as cursor:
        cursor.execute("SELECT 1 AS alive")
        cursor.fetchone()
    return jsonify({"ok": True, "database": "connected"})


@api_bp.get("/network-info")
def network_info():
    lan_ip = detect_lan_ip()
    port = Config.FLASK_PORT
    return jsonify(
        {
            "ok": True,
            "port": port,
            "lan_ip": lan_ip,
            "local_url": f"http://127.0.0.1:{port}",
            "lan_url": f"http://{lan_ip}:{port}",
        }
    )


@api_bp.get("/vehicle-types")
def get_vehicle_types():
    types = vehicle_service.list_active_vehicle_types()
    return jsonify({"ok": True, "tipos_vehiculo": types})


# ---------------------------------------------------------------------------
# Autenticación y Sesión (EP2)
# ---------------------------------------------------------------------------
@api_bp.get("/auth/me")
def auth_me():
    return jsonify({"ok": True, "user": g.current_user})


@api_bp.post("/auth/register")
def auth_register():
    payload = request.get_json(silent=True) or {}
    user = auth_service.register_user(payload)
    session["user_id"] = user["id"]
    return jsonify({"ok": True, "message": "Cuenta creada exitosamente.", "user": user}), 201


@api_bp.post("/auth/login")
def auth_login():
    payload = request.get_json(silent=True) or {}
    user = auth_service.authenticate_user(payload.get("email"), payload.get("password"))
    session["user_id"] = user["id"]
    return jsonify({"ok": True, "message": f"Bienvenido/a, {user['nombre']}.", "user": user})


@api_bp.post("/auth/logout")
def auth_logout():
    session.clear()
    return jsonify({"ok": True, "message": "Sesión cerrada correctamente."})


@api_bp.put("/auth/profile")
@require_auth()
def auth_update_profile():
    payload = request.get_json(silent=True) or {}
    updated = auth_service.update_user_profile(g.current_user["id"], payload.get("nombre"))
    return jsonify({"ok": True, "message": "Perfil actualizado.", "user": updated})


# ---------------------------------------------------------------------------
# Catálogo Público, Mapa y Grilla de Plazas en Tiempo Real (EP1 + EP3)
# ---------------------------------------------------------------------------
@api_bp.get("/parkings")
def list_parkings():
    result = parking_service.list_catalog(request.args, current_user=g.current_user)
    return jsonify({"ok": True, **result})


@api_bp.get("/parkings/<int:parking_id>")
def get_parking_detail(parking_id: int):
    detail = parking_service.get_parking_live_detail(parking_id, current_user=g.current_user)
    return jsonify({"ok": True, "estacionamiento": detail})


# ---------------------------------------------------------------------------
# Vehículos del Usuario Conductor (EP2-HU3)
# ---------------------------------------------------------------------------
@api_bp.get("/vehicles")
@require_auth(roles=("USUARIO", "ADMIN"))
def list_my_vehicles():
    vehicles = vehicle_service.list_vehicles_for_user(g.current_user["id"])
    return jsonify({"ok": True, "vehiculos": vehicles})


@api_bp.post("/vehicles")
@require_auth(roles=("USUARIO", "ADMIN"))
def create_my_vehicle():
    payload = request.get_json(silent=True) or {}
    created = vehicle_service.register_user_vehicle(g.current_user["id"], payload)
    return jsonify({"ok": True, "message": "Vehículo registrado con éxito.", "vehiculo": created}), 201


@api_bp.delete("/vehicles/<int:vehicle_id>")
@require_auth(roles=("USUARIO", "ADMIN"))
def delete_my_vehicle(vehicle_id: int):
    vehicle_service.remove_user_vehicle(g.current_user["id"], vehicle_id)
    return jsonify({"ok": True, "message": "Vehículo eliminado de tu cuenta."})


# ---------------------------------------------------------------------------
# Billetera Virtual (EP4)
# ---------------------------------------------------------------------------
@api_bp.get("/wallet")
@require_auth()
def get_my_wallet():
    data = wallet_service.get_wallet_overview(g.current_user["id"])
    return jsonify({"ok": True, **data})


@api_bp.post("/wallet/deposit")
@require_auth(roles=("USUARIO", "ADMIN"))
def deposit_my_wallet():
    payload = request.get_json(silent=True) or {}
    data = wallet_service.deposit_funds(
        g.current_user["id"],
        payload.get("monto"),
        payload.get("metodo", "Tarjeta / Transferencia Inmediata"),
    )
    return jsonify({"ok": True, "message": "Saldo acreditado en tu Billetera Virtual.", **data})


# ---------------------------------------------------------------------------
# Estadías en Tiempo Real, Facturación, Tickets y Reseñas (EP3 + EP4 + EP5)
# ---------------------------------------------------------------------------
@api_bp.get("/stays/my")
@require_auth(roles=("USUARIO", "ADMIN"))
def list_my_stays():
    data = stay_service.get_driver_stays(g.current_user["id"])
    return jsonify({"ok": True, **data})


@api_bp.post("/stays/checkin")
@require_auth(roles=("USUARIO",))
def start_stay():
    payload = request.get_json(silent=True) or {}
    result = stay_service.start_user_stay(g.current_user, payload)
    return jsonify(
        {
            "ok": True,
            "message": f"Ingreso confirmado en plaza {result['plaza_codigo']}. Cronómetro iniciado.",
            "estadia": result,
        }
    ), 201


@api_bp.post("/stays/<int:estadia_id>/checkout")
@require_auth()
def finish_stay(estadia_id: int):
    payload = request.get_json(silent=True) or {}
    cobro_mostrador = bool(payload.get("cobro_mostrador", False))
    receipt = stay_service.checkout_stay(g.current_user, estadia_id, cobro_mostrador=cobro_mostrador)
    return jsonify(
        {
            "ok": True,
            "message": f"Estadía finalizada y plaza {receipt['plaza_codigo']} liberada. Ticket {receipt['numero_ticket']} emitido.",
            "comprobante": receipt,
        }
    )


@api_bp.get("/stays/<int:estadia_id>/ticket")
@require_auth()
def get_stay_ticket(estadia_id: int):
    receipt = stay_service.get_ticket(g.current_user, estadia_id)
    return jsonify({"ok": True, "comprobante": receipt})


@api_bp.post("/stays/<int:estadia_id>/review")
@require_auth(roles=("USUARIO",))
def review_stay(estadia_id: int):
    payload = request.get_json(silent=True) or {}
    review = stay_service.create_stay_review(g.current_user, estadia_id, payload)
    return jsonify({"ok": True, "message": "¡Gracias por tu calificación y reseña!", "resena": review}), 201


# ---------------------------------------------------------------------------
# Panel del Propietario del Estacionamiento
# ---------------------------------------------------------------------------
@api_bp.get("/owner/dashboard")
@require_auth(roles=("PROPIETARIO",))
def owner_dashboard():
    data = parking_service.get_owner_dashboard(g.current_user)
    return jsonify({"ok": True, **data})


@api_bp.put("/owner/parking")
@require_auth(roles=("PROPIETARIO",))
def owner_update_parking():
    payload = request.get_json(silent=True) or {}
    updated = parking_service.save_owner_parking_config(g.current_user["id"], payload)
    return jsonify(
        {
            "ok": True,
            "message": "Configuración y cantidad de plazas actualizadas correctamente.",
            "estacionamiento": updated,
        }
    )


@api_bp.put("/owner/tariffs")
@require_auth(roles=("PROPIETARIO",))
def owner_update_tariffs():
    payload = request.get_json(silent=True) or {}
    tariffs = parking_service.save_owner_tariffs(g.current_user["id"], payload.get("tarifas"))
    return jsonify({"ok": True, "message": "Matriz de tarifas guardada con éxito.", "tarifas": tariffs})


@api_bp.post("/owner/manual-checkin")
@require_auth(roles=("PROPIETARIO", "ADMIN"))
def owner_manual_checkin():
    payload = request.get_json(silent=True) or {}
    result = stay_service.start_manual_desk_stay(g.current_user, payload)
    return jsonify(
        {
            "ok": True,
            "message": f"Ingreso presencial registrado en plaza {result['plaza_codigo']} ({result['patente']}).",
            "estadia": result,
        }
    ), 201


# ---------------------------------------------------------------------------
# Panel del Administrador Global
# ---------------------------------------------------------------------------
@api_bp.get("/admin/dashboard")
@require_auth(roles=("ADMIN",))
def admin_dashboard():
    data = admin_service.get_admin_dashboard()
    return jsonify({"ok": True, **data})


@api_bp.patch("/admin/users/<int:user_id>/status")
@require_auth(roles=("ADMIN",))
def admin_toggle_user(user_id: int):
    payload = request.get_json(silent=True) or {}
    activo = bool(payload.get("activo", True))
    admin_service.set_user_active_status(g.current_user["id"], user_id, activo)
    estado_txt = "activada" if activo else "suspendida"
    return jsonify({"ok": True, "message": f"Cuenta de usuario {estado_txt}."})


@api_bp.patch("/admin/parkings/<int:parking_id>/status")
@require_auth(roles=("ADMIN",))
def admin_toggle_parking(parking_id: int):
    payload = request.get_json(silent=True) or {}
    activo = bool(payload.get("activo", True))
    admin_service.set_parking_active_status(parking_id, activo)
    estado_txt = "habilitado" if activo else "pausado"
    return jsonify({"ok": True, "message": f"Estacionamiento {estado_txt}."})


@api_bp.post("/admin/vehicle-types")
@require_auth(roles=("ADMIN",))
def admin_create_vehicle_type():
    payload = request.get_json(silent=True) or {}
    created = admin_service.add_vehicle_type(payload)
    return jsonify({"ok": True, "message": "Tipo de vehículo añadido al catálogo.", "tipo": created}), 201


@api_bp.patch("/admin/vehicle-types/<int:type_id>/status")
@require_auth(roles=("ADMIN",))
def admin_toggle_vehicle_type(type_id: int):
    payload = request.get_json(silent=True) or {}
    activo = bool(payload.get("activo", True))
    admin_service.set_vehicle_type_status(type_id, activo)
    return jsonify({"ok": True, "message": "Estado de tipo de vehículo actualizado."})
