"""Variational free-energy surprise using only stdlib and numpy."""

import numpy as np


def free_energy(
    prediccion_tendencia: float,
    realidad_gap: float,
    inercia_observada: float,
    retorno_actual: float = 0.0,
    coherencia_previa: float = 0.5,
) -> float:
    """Calculate bounded surprise from prediction and observed market data.

    The return component follows ``abs(retorno_actual) * 10``. Gap and
    inertia disagreement are added as normalized surprise terms, then the
    result is amplified by prior incoherence and bounded to ``[0, 20]``.
    """
    fe_base = abs(retorno_actual) * 10.0
    error_gap = min(1.0, realidad_gap * 200.0)

    inercia_esperada = 2.0 * (prediccion_tendencia - 0.5)
    error_inercia = abs(inercia_observada - inercia_esperada) / 2.0
    error_inercia = min(1.0, error_inercia)

    factor_decoherencia = 1.0 + (1.0 - coherencia_previa)
    fe_total = (fe_base + error_gap + error_inercia) * factor_decoherencia * 2.5
    return float(min(20.0, max(0.0, fe_total)))


def prediccion_interna(hurst: float, cross_ratio: float) -> float:
    """Estimate continuation probability from Hurst and cross-ratio values.

    Values above ``0.5`` indicate stronger continuation pressure; values
    below it indicate weaker trend evidence and possible reversion.
    """
    fuerza_tendencia = abs(hurst - 0.5) * 2.0
    score_eliptico = min(1.0, abs(cross_ratio) / 5.0)
    factor_reduccion = 1.0 - (score_eliptico * 0.5)
    prob_tendencia = fuerza_tendencia * factor_reduccion
    return float(max(0.0, min(1.0, prob_tendencia)))