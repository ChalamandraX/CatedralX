"""Final operation assembly after directional and risk filters."""

import math
from typing import Any, Dict


def _safe_size(value: float) -> float:
    """Return a usable non-negative position size."""
    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        return 0.0
    return numeric_value if math.isfinite(numeric_value) and numeric_value > 0.0 else 0.0


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
) -> Dict[str, Any]:
    """Collapse directional and risk thresholds into the final operator block."""
    if score_direccional > 0.35:
        direccion = "BUY"
    elif score_direccional < -0.35:
        direccion = "SELL"
    else:
        direccion = "HOLD"

    sizes = {
        "size_kelly": _safe_size(size_kelly),
        "size_kelly_adapted": _safe_size(size_kelly_adapted),
        "size_mcx": _safe_size(size_mcx),
        "size_dsx": _safe_size(size_dsx),
        "size_fe": _safe_size(size_fe),
        "size_expo": _safe_size(size_expo),
    }
    size_final = min(sizes.values())

    if confianza < 0.40 or direccion == "HOLD":
        size_final = 0.0
        direccion = "HOLD"

    if direccion == "HOLD":
        decision_mode = "DEFENSIVE_HALT" if sizes["size_fe"] < 0.1 else "WATCH"
    else:
        decision_mode = "TREND_LONG" if direccion == "BUY" and fase == "TENDENCIA" else "MEAN_REVERSION"

    return {
        "decision": direccion,
        "decision_mode": decision_mode,
        "size_final": round(size_final, 4),
        "filtros_aplicados": {name: round(value, 4) for name, value in sizes.items()},
        "ejecucion_autorizada": bool(size_final > 0.0 and direccion != "HOLD"),
    }


if __name__ == "__main__":
    import json

    operador = ensamblar_operacion(
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
    print(json.dumps(operador, indent=2))