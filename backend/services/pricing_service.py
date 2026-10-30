"""Motor de Cálculo Dinámico de Tiempos y Tarifas de E.V.A."""

from decimal import Decimal, ROUND_HALF_UP
import math


def calculate_live_charge(modalidad: str, tarifa_aplicada, segundos_transcurridos: int) -> tuple:
    """
    Calcula (minutos_cobrables, monto_acumulado) según las reglas de negocio:
    - ESTADIA_FIJA: cobra el valor plano pactado de la estadía.
    - HORA: cobra mínimo 1 hora completa (60 min) y, a partir del minuto 61,
      fracciona proporcionalmente por minuto transcurrido.
    """
    segundos = max(0, int(segundos_transcurridos or 0))
    minutos = max(1, math.ceil(segundos / 60.0)) if segundos > 0 else 1
    tarifa = Decimal(str(tarifa_aplicada))

    if modalidad == "ESTADIA_FIJA":
        monto = tarifa.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return minutos, monto

    # Modalidad HORA: mínimo 60 minutos, luego proporcional por minuto
    if minutos <= 60:
        monto = tarifa.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    else:
        minutos_extra = Decimal(minutos - 60)
        adicional = (minutos_extra / Decimal(60)) * tarifa
        monto = (tarifa + adicional).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    return minutos, monto
