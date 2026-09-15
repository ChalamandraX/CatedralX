"""Homeostatic sensitivity and reinforcement-learning primitives."""

from typing import Any, Dict, List, Tuple

import numpy as np


def palanca_beta(
    dopamina: float,
    cortisol: float,
    serotonina: float,
    volatilidad: float,
    gap_norm: float,
) -> float:
    """Calculate bounded beta sensitivity from hormones and market risk."""
    riesgo = (volatilidad / 100.0) + (abs(gap_norm) / 50.0)
    beta = (dopamina / (cortisol + 0.2)) * (1.0 / (1.0 + riesgo))
    beta *= 0.5 + serotonina * 0.5
    return float(max(0.1, min(5.0, beta)))


def softmax(q_values: List[float], beta: float) -> List[float]:
    """Transform Q-values into numerically stable action probabilities."""
    q = np.asarray(q_values, dtype=np.float64)
    if q.size == 0:
        return []
    q_shifted = q - np.max(q)
    exp_q = np.exp(beta * q_shifted)
    return (exp_q / np.sum(exp_q)).tolist()


def q_learning_actualizar(
    q_actual: float,
    recompensa: float,
    max_q_futuro: float,
    alpha: float = 0.1,
    gamma: float = 0.95,
) -> float:
    """Apply one bounded Bellman Q-learning update."""
    nuevo_q = q_actual + alpha * (
        recompensa + gamma * max_q_futuro - q_actual
    )
    return float(max(-1.0, min(1.0, nuevo_q)))


def homeostasis_lqr(
    estado: np.ndarray,
    Q: np.ndarray,
    R: np.ndarray,
) -> Tuple[float, float]:
    """Return the simplified scalar LQR gain and control signal."""
    p_matrix = Q
    gain = p_matrix / (p_matrix + R)
    control = -float(gain * estado[0])
    return float(gain), control


def estado_homeostatico(
    hormonas: Dict[str, float],
    mercado: Dict[str, float],
) -> Dict[str, Any]:
    """Build the optimizer state consumed by the orchestrator."""
    beta = palanca_beta(
        hormonas.get("dopamina_D", 0.5),
        hormonas.get("cortisol_C", 0.3),
        hormonas.get("serotonina_S", 0.5),
        mercado.get("volatilidad", 0.01),
        mercado.get("gap", 0.0),
    )
    return {
        "beta_precision": round(beta, 4),
        "modo": (
            "AGRESIVO"
            if beta > 1.5
            else "CONSERVADOR"
            if beta < 0.5
            else "EQUILIBRADO"
        ),
        "sensibilidad": round(1.0 / (1.0 + beta), 4),
    }