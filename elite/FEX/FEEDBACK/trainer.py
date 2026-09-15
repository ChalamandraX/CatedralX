"""Gradient-descent trainer for a single logistic model."""

from typing import List, Tuple

import numpy as np


def sgd_step(
    theta: np.ndarray,
    gradiente: np.ndarray,
    tasa_aprendizaje: float = 0.01,
) -> np.ndarray:
    """Apply one stochastic-gradient descent update."""
    return theta - tasa_aprendizaje * gradiente


def perdida_logistica(y_pred: float, y_real: float) -> float:
    """Return binary cross-entropy with clipped prediction probability."""
    y_pred = np.clip(y_pred, 1e-7, 1.0 - 1e-7)
    return float(-(y_real * np.log(y_pred) + (1.0 - y_real) * np.log(1.0 - y_pred)))


def actualizar_modelo(
    entradas: List[float],
    objetivo: float,
    pesos: np.ndarray,
    tasa: float = 0.01,
) -> Tuple[np.ndarray, float]:
    """Perform one logistic prediction, gradient and weight update."""
    x = np.asarray(entradas + [1.0], dtype=float)
    logits = float(np.dot(pesos, x))
    y_pred = 1.0 / (1.0 + np.exp(-logits))
    error = y_pred - objetivo
    gradiente = error * x
    nuevos_pesos = sgd_step(pesos, gradiente, tasa)
    perdida = perdida_logistica(y_pred, objetivo)
    return nuevos_pesos, perdida