"""Hysteresis filter for noisy action scores."""


def decision_con_histeresis(
    score_actual: float,
    decision_anterior: str,
    umbral: float = 0.2,
) -> str:
    """Keep the previous decision inside the hysteresis band."""
    if abs(score_actual) < umbral:
        return decision_anterior
    if score_actual > umbral:
        return "buy"
    if score_actual < -umbral:
        return "sell"
    return "hold"