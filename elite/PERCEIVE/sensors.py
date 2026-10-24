"""Validate observed market observations; never invent missing prices."""
from __future__ import annotations
import math
from typing import Any

def validate_price_history(values: Any, minimum: int = 30) -> list[float]:
    if not isinstance(values, (list, tuple)):
        raise ValueError("price history must be a list or tuple of observed prices")
    if len(values) < minimum:
        raise ValueError(f"at least {minimum} observed prices are required")
    result = []
    for i, value in enumerate(values):
        if isinstance(value, bool):
            raise ValueError(f"price[{i}] must be positive and finite")
        try:
            price = float(value)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError(f"price[{i}] must be positive and finite") from exc
        if not math.isfinite(price) or price <= 0:
            raise ValueError(f"price[{i}] must be positive and finite")
        result.append(price)
    return result

def normalize_market_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("market payload must be an object")
    prices = validate_price_history(payload.get("historial_precios", payload.get("historico")))
    current = payload.get("precio", prices[-1])
    if isinstance(current, bool):
        raise ValueError("precio must be positive and finite")
    current = float(current)
    if not math.isfinite(current) or current <= 0:
        raise ValueError("precio must be positive and finite")
    if prices[-1] != current:
        prices.append(current)
    gap = float(payload.get("gap", 0.0))
    inertia = float(payload.get("inercia", 0.0))
    if not math.isfinite(gap) or not math.isfinite(inertia):
        raise ValueError("gap and inertia must be finite")
    return {"historial_precios": prices, "precio": current, "gap": gap, "inercia": inertia,
            "source": str(payload.get("source", "unspecified")), "observed_at": payload.get("observed_at")}
