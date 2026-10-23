"""Stochastic decision collapse for the Catedral motor layer."""

import random
from typing import Tuple


def colapsar_qubit(
    fuerza_tendencia: float,
    fuerza_rango: float,
    direccion: float,
    cortisol: float,
    umbral_defensa: float = 0.8,
) -> str:
    """Return ``buy``, ``sell`` or ``hold`` from trend/range strengths."""
    if cortisol > umbral_defensa:
        return "hold"

    alpha2 = fuerza_tendencia ** 2
    beta2 = fuerza_rango ** 2
    suma_cuadrados = alpha2 + beta2
    if suma_cuadrados < 1e-9:
        return "hold"

    p_dominancia_tendencia = alpha2 / suma_cuadrados
    sigue_tendencia = random.random() < p_dominancia_tendencia

    if direccion > 0.1:
        return "buy" if sigue_tendencia else "sell"
    if direccion < -0.1:
        return "sell" if sigue_tendencia else "buy"
    return "hold"


def colapsar_qubit_determinista(
    fuerza_tendencia: float,
    fuerza_rango: float,
    direccion: float,
    cortisol: float,
    umbral_defensa: float = 0.8,
) -> str:
    """Deterministic MAP-style diagnostic counterpart to the stochastic legacy API.

    This is for reproducible diagnostics only. It does not replace the canonical
    financial signal and it never creates an execution intent.
    """
    import math

    values = (fuerza_tendencia, fuerza_rango, direccion, cortisol, umbral_defensa)
    if not all(math.isfinite(float(value)) for value in values):
        raise ValueError("qubit inputs must be finite")
    if cortisol > umbral_defensa:
        return "hold"

    tendencia = max(0.0, float(fuerza_tendencia))
    rango = max(0.0, float(fuerza_rango))
    alpha2 = tendencia ** 2
    beta2 = rango ** 2
    suma_cuadrados = alpha2 + beta2
    if suma_cuadrados < 1e-9:
        return "hold"

    # Resolve the same trend-vs-range choice at p >= 0.5 rather than
    # sampling random.random(), so the saved historical diagnostic is repeatable.
    sigue_tendencia = alpha2 / suma_cuadrados >= 0.5
    if direccion > 0.1:
        return "buy" if sigue_tendencia else "sell"
    if direccion < -0.1:
        return "sell" if sigue_tendencia else "buy"
    return "hold"
