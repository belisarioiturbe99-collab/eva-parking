"""Rutas Web que sirven las vistas HTML de la Capa de Presentación."""

from flask import Blueprint, render_template, g, redirect, url_for
from backend.services import stay_service
from backend.services.exceptions import DomainError

web_bp = Blueprint("web", __name__)


@web_bp.get("/")
def index():
    return render_template("index.html")


@web_bp.get("/ticket/<int:estadia_id>")
def printable_ticket(estadia_id: int):
    if not g.current_user:
        return redirect(url_for("web.index"))
    try:
        receipt = stay_service.get_ticket(g.current_user, estadia_id)
    except DomainError as exc:
        return render_template("ticket.html", error=exc.message, comprobante=None), exc.status_code
    return render_template("ticket.html", comprobante=receipt, error=None)
