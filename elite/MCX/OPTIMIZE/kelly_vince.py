"""Kelly clásico y Optimal-f de Ralph Vince para gestión de capital."""

from typing import List

import numpy as np


def kelly_clasico(
    prob_ganancia: float,
    ganancia_porcentaje: float,
    perdida_porcentaje: float,
) -> float:
    """Return the capped Kelly fraction for a single payoff distribution."""
    if perdida_porcentaje <= 0.0 or ganancia_porcentaje <= 0.0:
        return 0.0

    b = ganancia_porcentaje / perdida_porcentaje
    p = max(0.0, min(1.0, prob_ganancia))
    q = 1.0 - p
    fraction = (b * p - q) / b
    return float(max(0.0, min(0.5, fraction)))


def optimal_f_vince(returns: List[float]) -> float:
    """Estimate Vince's Optimal-f by maximizing mean log growth."""
    if len(returns) < 10:
        return 0.02

    values = np.asarray(returns, dtype=float)
    minimum = np.min(values)
    max_loss = abs(minimum) if minimum < 0.0 else 0.01
    if max_loss == 0.0:
        return 0.02

    f_values = np.linspace(0.01, 0.3, 15)
    best_f = 0.02
    best_growth = -np.inf
    for fraction in f_values:
        factors = 1.0 + fraction * values / max_loss
        if np.any(factors <= 0.0):
            continue
        growth = float(np.mean(np.log(factors)))
        if growth > best_growth:
            best_growth = growth
            best_f = fraction
    return round(float(best_f), 4)