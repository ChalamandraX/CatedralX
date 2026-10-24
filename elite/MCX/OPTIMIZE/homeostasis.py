"""Convert internal bounded state into conservative analysis thresholds."""
def parametros_homeostaticos(neuro: dict, panic: bool = False) -> dict:
    cortisol = min(1.0, max(0.0, float(neuro.get("cortisol", 1.0))))
    dopamina = min(1.0, max(0.0, float(neuro.get("dopamina", 0.0))))
    defensive = panic or cortisol >= 0.7
    return {"modo": "DEFENSIVO" if defensive else "NORMAL",
            "agresividad": 0.0 if defensive else round(dopamina * (1.0 - cortisol), 4),
            "umbral_minimo": 1.0 if defensive else round(0.4 + cortisol * 0.4, 4),
            "orders_allowed": False}
