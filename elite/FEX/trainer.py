"""Catedral v4.2 supervised stochastic-gradient trainer."""

from typing import List, Tuple

import numpy as np


def sgd_paso(
    pesos: np.ndarray,
    gradiente: np.ndarray,
    tasa: float = 0.01,
) -> np.ndarray:
    """Apply one stochastic-gradient descent update."""
    return pesos - tasa * gradiente


def perdida_logistica(pred: float, real: float) -> float:
    """Return binary cross-entropy with a numerically safe prediction."""
    pred = np.clip(pred, 1e-7, 1.0 - 1e-7)
    return float(-(real * np.log(pred) + (1.0 - real) * np.log(1.0 - pred)))


def entrenar_paso(
    entradas: List[float],
    objetivo: float,
    pesos: np.ndarray,
    tasa: float = 0.01,
) -> Tuple[np.ndarray, float]:
    """Perform one logistic prediction, update and loss calculation."""
    x = np.asarray(entradas + [1.0], dtype=float)
    logits = float(np.dot(pesos, x))
    y_pred = 1.0 / (1.0 + np.exp(-logits))
    error = y_pred - objetivo
    gradiente = error * x
    nuevos_pesos = sgd_paso(pesos, gradiente, tasa)
    return nuevos_pesos, perdida_logistica(y_pred, objetivo)