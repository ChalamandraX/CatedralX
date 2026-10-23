"""Reserve estimator. Configured rate is a planning assumption, not tax advice."""
def estimar_reserva(ingreso: float, tasa: float = 0.02) -> dict:
    ingreso, tasa = float(ingreso), float(tasa)
    if ingreso < 0 or not 0 <= tasa <= 1:
        raise ValueError("ingreso must be >= 0 and tasa must be between 0 and 1")
    return {"ingreso": round(ingreso, 2), "tasa_configurada": tasa,
            "reserva_estimada": round(ingreso * tasa, 2),
            "disclaimer": "Estimación configurable; no determina la obligación fiscal real."}
