"""Quantum homeostasis and reinforcement optimization primitives."""

from typing import List, Tuple

import numpy as np


def calcular_beta(
    dopamina: float,
    cortisol: float,
    serotonina: float,
    volatilidad: float,
    gap_norm: float,
) -> float:
    """Calculate bounded learning sensitivity beta."""
    riesgo = (volatilidad / 100.0) + (abs(gap_norm) / 50.0)
    beta = (dopamina / (cortisol + 0.2)) * (1.0 / (1.0 + riesgo))
    beta *= 0.5 + serotonina * 0.5
    return float(max(0.1, min(5.0, beta)))


def softmax(q_values: List[float], beta: float) -> List[float]:
    """Convert Q-values to numerically stable action probabilities."""
    q = np.asarray(q_values, dtype=float)
    if q.size == 0:
        return []
    exp_q = np.exp(beta * (q - np.max(q)))
    return (exp_q / np.sum(exp_q)).tolist()


def q_learning_update(
    q_actual: float,
    recompensa: float,
    max_q_futuro: float,
    alpha: float = 0.1,
    gamma: float = 0.95,
) -> float:
    """Apply one bounded Bellman Q-learning update."""
    nuevo_q = q_actual + alpha * (recompensa + gamma * max_q_futuro - q_actual)
    return float(max(-1.0, min(1.0, nuevo_q)))


def optimal_f(returns: List[float], max_loss: float = 0.1) -> float:
    """Estimate Kelly/Optimal-f by a small grid search."""
    if not returns or max_loss == 0:
        return 0.02

    f_range = np.linspace(0.01, 0.5, 20)
    best_f = 0.02
    best_growth = -np.inf
    returns_array = np.asarray(returns, dtype=float)
    for fraction in f_range:
        factors = 1.0 + fraction * returns_array / max_loss
        if np.any(factors <= 0.0):
            continue
        growth = np.sum(np.log(factors))
        if growth > best_growth:
            best_growth = growth
            best_f = fraction
    return round(float(best_f), 4)


def homeostasis_lqr(
    estado: np.ndarray,
    q_matrix: np.ndarray,
    r_matrix: np.ndarray,
) -> Tuple[float, float]:
    """Return the scalar LQR gain and control signal for the first state."""
    p_matrix = q_matrix
    gain = p_matrix / (p_matrix + r_matrix)
    control = -float(gain * estado[0])
    return float(gain), control