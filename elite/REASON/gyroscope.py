"""Angular market state with a two-state extended Kalman filter."""

from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from . import hurst_analyzer as hurst


def extended_kalman_filter(
    omega_bruto: float,
    x_prev: np.ndarray,
    p_prev: np.ndarray,
    dt: float = 1.0,
) -> Tuple[np.ndarray, np.ndarray, float]:
    """Estimate angular velocity and bias from a raw angular observation."""
    transition = np.array([[1.0, -dt], [0.0, 1.0]])
    process_noise = np.diag([0.01, 0.001])
    x_pred = transition @ x_prev
    p_pred = transition @ p_prev @ transition.T + process_noise

    observation_matrix = np.array([[1.0, 0.0]])
    measurement_noise = np.array([[0.05]])
    innovation = np.array([omega_bruto]) - observation_matrix @ x_pred
    innovation_covariance = (
        observation_matrix @ p_pred @ observation_matrix.T + measurement_noise
    )
    kalman_gain = p_pred @ observation_matrix.T @ np.linalg.inv(innovation_covariance)

    x_new = x_pred + kalman_gain @ innovation
    p_new = (np.eye(2) - kalman_gain @ observation_matrix) @ p_pred
    return x_new, p_new, float(x_new[0])


def gyro_state(
    precios: List[float],
    estado_previo: Optional[Tuple[np.ndarray, np.ndarray]] = None,
) -> Dict[str, Any]:
    """Return phase, direction, angular velocity and Hurst diagnostics."""
    if len(precios) < 10:
        return {
            "fase": "CAOS",
            "orientacion": "NEUTRO",
            "omega": 0.0,
            "precesion": 0.0,
            "estabilidad": 0.5,
            "entropia": 0.5,
            "confianza": 0.0,
            "hurst_corto": 0.5,
            "hurst_largo": 0.5,
        }

    h_short = hurst.hurst_exponent(precios[-20:], max_lag=10) if len(precios) >= 20 else 0.5
    h_long = hurst.hurst_exponent(precios[-60:], max_lag=30) if len(precios) >= 60 else 0.5
    omega_bruto = h_short - h_long

    if estado_previo is None:
        x_prev = np.array([omega_bruto, 0.0])
        p_prev = np.eye(2) * 0.1
    else:
        x_prev, p_prev = estado_previo

    x_new, p_new, omega = extended_kalman_filter(omega_bruto, x_prev, p_prev)
    omega = max(-1.0, min(1.0, omega * 2.0))

    estabilidad = min(1.0, abs(h_short - 0.5) * 2.0)
    entropia = 1.0 - estabilidad
    if h_short > 0.7:
        fase = "TENDENCIA"
    elif h_short < 0.4:
        fase = "RANGO"
    else:
        fase = "CAOS"

    recent = np.asarray(precios[-5:], dtype=float)
    slope = np.polyfit(np.arange(5), recent, 1)[0]
    normalized_slope = slope / (np.mean(np.abs(recent)) + 1e-9)
    if normalized_slope > 0.002:
        orientacion = "ALCISTA"
    elif normalized_slope < -0.002:
        orientacion = "BAJISTA"
    else:
        orientacion = "NEUTRO"

    precesion = omega * estabilidad
    confianza = estabilidad * (1.0 - abs(omega))
    return {
        "fase": fase,
        "orientacion": orientacion,
        "omega": float(omega),
        "precesion": float(precesion),
        "estabilidad": float(estabilidad),
        "entropia": float(entropia),
        "confianza": float(confianza),
        "hurst_corto": float(h_short),
        "hurst_largo": float(h_long),
        "_estado_filtro": (x_new, p_new),
    }