"""Final decision assembly after directional and risk filters.

The output expresses an analysis intent only. This module is not an executor
and must never claim that a live trade is authorized.
"""

from __future__ import annotations

import math
from typing import Any

from contracts.actions import normalizar_senal


def _finite_number(value: Any, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return default
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return default
    return number if math.isfinite(number) else default


def _safe_size(value: Any) -> float:
    """Return a usable non-negative position-size proposal."""
    numeric_value = _finite_number(value, default=-1.0)
    return max(0.0, numeric_value)


def ensamblar_operacion(
    score_direccional: float,
    confianza: float,
    fase: str,
    size_kelly: float,
    size_kelly_adapted: float,
    size_mcx: float,
    size_dsx: float,
    size_fe: float,
    size_expo: float,
) -> dict[str, Any]:
    """Collapse risk-size proposals into a normalized, review-only intent."""
    score = _finite_number(score_direccional)
    confidence = _finite_number(confianza, default=-1.0)
    if not 0.0 <= confidence <= 1.0:
        confidence = 0.0

    if score > 0.35:
        direction = "BUY"
    elif score < -0.35:
        direction = "SELL"
    else:
        direction = "HOLD"

    sizes = {
        "size_kelly": _safe_size(size_kelly),
        "size_kelly_adapted": _safe_size(size_kelly_adapted),
        "size_mcx": _safe_size(size_mcx),
        "size_dsx": _safe_size(size_dsx),
        "size_fe": _safe_size(size_fe),
        "size_expo": _safe_size(size_expo),
    }
    final_size = min(sizes.values())

    if confidence < 0.40 or direction == "HOLD":
        final_size = 0.0
        direction = "HOLD"

    if direction == "HOLD":
        decision_mode = "DEFENSIVE_HALT" if sizes["size_fe"] < 0.1 else "WATCH"
    else:
        decision_mode = (
            "TREND_LONG"
            if direction == "BUY" and fase == "TENDENCIA"
            else "MEAN_REVERSION"
        )

    canonical = normalizar_senal(direction)
    review_required = bool(final_size > 0.0 and canonical in {"buy", "sell"})
    return {
        "decision": direction,
        "decision_canonical": canonical,
        "decision_mode": decision_mode,
        "size_final": round(final_size, 4),
        "filtros_aplicados": {name: round(value, 4) for name, value in sizes.items()},
        "review_required": review_required,
        "ejecucion_autorizada": False,
        "trading_enabled": False,
        "orders_created": False,
        "orders_executed": False,
    }


if __name__ == "__main__":
    import json

    operator_output = ensamblar_operacion(
        score_direccional=0.68,
        confianza=0.85,
        fase="TENDENCIA",
        size_kelly=0.15,
        size_kelly_adapted=0.12,
        size_mcx=0.10,
        size_dsx=0.08,
        size_fe=0.05,
        size_expo=0.20,
    )
    print(json.dumps(operator_output, indent=2))
