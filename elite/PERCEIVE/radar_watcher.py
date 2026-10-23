"""Flag unusually large single-step observed price changes."""
import math
from typing import Sequence

def detectar_movimiento(precios: Sequence[float], threshold: float = 0.002) -> dict:
    if not math.isfinite(threshold) or threshold <= 0:
        raise ValueError("threshold must be positive and finite")
    if len(precios) < 2:
        return {"detected": False, "change_fraction": 0.0, "threshold": threshold}
    previous, current = float(precios[-2]), float(precios[-1])
    if not all(math.isfinite(x) and x > 0 for x in (previous, current)):
        raise ValueError("prices must be positive and finite")
    change = current / previous - 1.0
    return {"detected": abs(change) > threshold, "change_fraction": change, "threshold": threshold}
