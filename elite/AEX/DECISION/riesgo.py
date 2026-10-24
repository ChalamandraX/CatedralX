"""Entry-risk checks and confidence-based position sizing; fail closed on bad data."""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

from contracts.actions import normalizar_senal

CONFIANZA_MINIMA_ENTRADA = 0.40
RIESGO_MAXIMO_POR_OPERACION = 0.10
PERDIDA_MAXIMA_DIARIA = 0.10


class _DecisionMemory:
    """Small in-process statistics store used by the risk gate."""

    def __init__(self) -> None:
        self.estadisticas: dict[str, float] = {"ganancia_acumulada": 0.0}


memoria = _DecisionMemory()


def _finite_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) else None


def verificar_seguridad(
    accion: str,
    confianza: float,
    datos: dict[str, Any],
) -> tuple[bool, str]:
    """Return whether an action passes confidence, market and loss limits.

    All action aliases are normalized before the gate is applied. Invalid or
    missing safety metrics fail closed; they do not bypass comparisons.
    """
    try:
        signal = normalizar_senal(accion)
    except (TypeError, ValueError):
        return False, "Acción no reconocida"

    confidence = _finite_number(confianza)
    if confidence is None or not 0.0 <= confidence <= 1.0:
        return False, "Confianza inválida"

    if not isinstance(datos, Mapping):
        return False, "Datos de riesgo inválidos"

    entropy = _finite_number(datos.get("entropia", 0.0))
    volatility = _finite_number(datos.get("volatilidad", 0.0))
    if entropy is None or not 0.0 <= entropy <= 1.0:
        return False, "Entropía inválida"
    if volatility is None or volatility < 0.0:
        return False, "Volatilidad inválida"

    try:
        daily_result = _finite_number(
            memoria.estadisticas.get("ganancia_acumulada", 0.0)
        )
    except (AttributeError, TypeError):
        daily_result = None
    if daily_result is None:
        return False, "Estadísticas de riesgo inválidas"

    is_entry = signal in {"buy", "sell"}
    if is_entry and confidence < CONFIANZA_MINIMA_ENTRADA:
        return False, (f"Confianza baja: {confidence} < {CONFIANZA_MINIMA_ENTRADA}")
    if entropy > 0.8:
        return False, "Mercado caótico"
    if daily_result < -PERDIDA_MAXIMA_DIARIA:
        return False, "Límite pérdida diaria"
    if volatility > 0.05 and is_entry:
        return False, "Volatilidad extrema"
    return True, "OK"


def calcular_tamano_operacion(confianza: float) -> float:
    """Scale the maximum per-trade risk by confidence in [0, 1]."""
    confidence = _finite_number(confianza)
    if confidence is None:
        return 0.0
    return round(RIESGO_MAXIMO_POR_OPERACION * max(0.0, min(1.0, confidence)), 4)
