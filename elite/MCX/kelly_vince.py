"""Kelly clásico y Optimal-f de Vince para gestión de capital MCX."""

from typing import List

import numpy as np


def kelly_clasico(
    prob_ganancia: float,
    retorno_esperado: float,
    perdida_max: float,
) -> float:
    """Return the Kelly fraction capped to 30 percent of capital."""
    if perdida_max <= 0.0 or retorno_esperado <= 0.0:
        return 0.02

    b = retorno_esperado / perdida_max
    p = float(np.clip(prob_ganancia, 0.01, 0.99))
    q = 1.0 - p
    fraction = (b * p - q) / b
    return float(max(0.01, min(0.3, fraction)))


def optimal_f_vince(serie_retornos: List[float]) -> float:
    """Estimate Vince's Optimal-f by maximizing geometric growth."""
    if len(serie_retornos) < 10:
        return 0.02

    returns = np.asarray(serie_retornos, dtype=float)
    minimum = np.min(returns)
    max_loss = abs(minimum) if minimum < 0.0 else 0.01
    if max_loss == 0.0:
        return 0.02

    f_values = np.linspace(0.01, 0.3, 10)
    best_f, best_growth = 0.02, -np.inf
    for fraction in f_values:
        factors = 1.0 + fraction * returns / max_loss
        if np.any(factors <= 0.0):
            continue
        growth = np.sum(np.log(factors))
        if growth > best_growth:
            best_growth, best_f = growth, fraction
    return round(float(best_f), 4)