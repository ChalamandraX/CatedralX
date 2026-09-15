"""Entry-risk checks and confidence-based position sizing."""

import math
from typing import Any, Dict, Tuple


CONFIANZA_MINIMA_ENTRADA = 0.40
RIESGO_MAXIMO_POR_OPERACION = 0.10
PERDIDA_MAXIMA_DIARIA = 0.10


class _DecisionMemory:
    """Small in-process statistics store used by the risk gate."""

    def __init__(self) -> None:
        self.estadisticas: Dict[str, float] = {"ganancia_acumulada": 0.0}


memoria = _DecisionMemory()


def verificar_seguridad(
    accion: str,
    confianza: float,
    datos: Dict[str, Any],
) -> Tuple[bool, str]:
    """Return whether an action passes confidence, market and loss limits."""
    try:
        confidence = float(confianza)
    except (TypeError, ValueError):
        return False, "Confianza inválida"
    if not math.isfinite(confidence):
        return False, "Confianza inválida"

    if accion.startswith("ENTRAR") and confidence < CONFIANZA_MINIMA_ENTRADA:
        return False, f"Confianza baja: {confidence} < {CONFIANZA_MINIMA_ENTRADA}"
    if float(datos.get("entropia", 0.0)) > 0.8:
        return False, "Mercado caótico"
    if memoria.estadisticas["ganancia_acumulada"] < -PERDIDA_MAXIMA_DIARIA:
        return False, "Límite pérdida diaria"
    if float(datos.get("volatilidad", 0.0)) > 0.05 and accion.startswith("ENTRAR"):
        return False, "Volatilidad extrema"
    return True, "OK"


def calcular_tamano_operacion(confianza: float) -> float:
    """Scale the maximum per-trade risk by confidence in ``[0, 1]``."""
    try:
        confidence = float(confianza)
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(confidence):
        return 0.0
    return round(RIESGO_MAXIMO_POR_OPERACION * max(0.0, min(1.0, confidence)), 4)