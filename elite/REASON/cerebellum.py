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