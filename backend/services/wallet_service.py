"""Servicio de Billetera Virtual — Depósitos de Saldo e Historial Financiero."""

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from backend.database import transaction, read_cursor, serialize_rows
from backend.repositories import user_repo
from backend.services.exceptions import DomainError


def get_wallet_overview(usuario_id: int) -> dict:
    with read_cursor() as cursor:
        user = user_repo.find_by_id(cursor, usuario_id)
        if not user:
            raise DomainError("Usuario no encontrado.", status_code=404)
        movements = user_repo.list_wallet_movements(cursor, usuario_id, limit=30)
        return {
            "saldo_billetera": float(user["saldo_billetera"]),
            "movimientos": serialize_rows(movements),
        }


def deposit_funds(usuario_id: int, raw_amount, metodo_simulado: str = "Transferencia / Tarjeta") -> dict:
    """Acredita saldo en la Billetera Virtual del usuario con validación de límites."""
    try:
        amount = Decimal(str(raw_amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError, ValueError):
        raise DomainError("Ingresa un monto numérico válido para recargar.")

    if amount < Decimal("100.00"):
        raise DomainError("El monto mínimo de recarga es de $100.00.")
    if amount > Decimal("500000.00"):
        raise DomainError("El monto máximo por operación de recarga es de $500,000.00.")

    clean_method = (metodo_simulado or "Recarga Digital").strip()[:60]

    with transaction() as cursor:
        user = user_repo.find_by_id(cursor, usuario_id, for_update=True)
        if not user:
            raise DomainError("Usuario no encontrado.", status_code=404)

        current_balance = Decimal(str(user["saldo_billetera"]))
        new_balance = (current_balance + amount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        user_repo.update_wallet_balance(cursor, usuario_id, new_balance)
        user_repo.insert_wallet_movement(
            cursor,
            usuario_id=usuario_id,
            estadia_id=None,
            tipo="RECARGA",
            monto=amount,
            saldo_posterior=new_balance,
            descripcion=f"Recarga de saldo ({clean_method})",
        )

    return get_wallet_overview(usuario_id)
