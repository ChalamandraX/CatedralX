"""Bounded deterministic internal state; not a biological measurement."""
from __future__ import annotations
import math

def actualizar_estado(cortisol: float = 0.3, dopamina: float = 0.5, sorpresa: float = 0.0,
                      volatilidad: float = 0.0) -> dict[str, float]:
    values = [cortisol, dopamina, sorpresa, volatilidad]
    if not all(math.isfinite(float(v)) for v in values):
        raise ValueError("affective inputs must be finite")
    risk = min(1.0, max(0.0, abs(float(sorpresa)) * 0.25 + abs(float(volatilidad)) * 5.0))
    c = min(1.0, max(0.0, 0.7 * float(cortisol) + 0.3 * risk))
    d = min(1.0, max(0.0, 0.8 * float(dopamina) + 0.2 * (1.0 - risk)))
    return {"cortisol": round(c, 6), "dopamina": round(d, 6),
            "serotonina": round(min(1.0, max(0.0, 1.0 - risk * 0.5)), 6),
            "riesgo_estimado": round(risk, 6)}
