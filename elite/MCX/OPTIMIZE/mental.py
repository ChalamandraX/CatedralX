"""Operational fatigue proxy based on cycle count and risk pressure."""
def estado_mental(ciclos: int, cortisol: float) -> dict:
    if ciclos < 0:
        raise ValueError("ciclos must be non-negative")
    cortisol = min(1.0, max(0.0, float(cortisol)))
    fatigue = min(1.0, ciclos / 1000.0 * 0.5 + cortisol * 0.5)
    return {"fatiga": round(fatigue, 6), "energia": round(1.0 - fatigue, 6),
            "is_proxy_metric": True}
