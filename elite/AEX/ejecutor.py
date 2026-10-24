"""Fail-closed action gate: emits review-only intent and never sends orders."""
import math
import os
from pathlib import Path
from typing import Any

ALLOWED_LABELS = {"buy", "sell", "hold"}
DEFAULT_PANIC_PATH = Path(os.path.expanduser("~/LAB/03-OUTPUT/.panic"))


def preparar_intencion(
    decision: str,
    size: float = 0.0,
    *,
    panic: bool = False,
    risk_flags=None,
    authorized: bool = False,
    price: float | None = None,
    confidence: float | None = None,
    panic_path: str | os.PathLike | None = None,
) -> dict[str, Any]:
    """Prepare a review-only intent; missing authorization/data always blocks it."""
    label = str(decision).lower()
    if label not in ALLOWED_LABELS:
        raise ValueError("decision must be buy, sell or hold")

    try:
        requested_size = float(size)
    except (TypeError, ValueError) as exc:
        raise ValueError("size must be finite and non-negative") from exc
    if not math.isfinite(requested_size) or requested_size < 0:
        raise ValueError("size must be finite and non-negative")
    if label in {"buy", "sell"} and requested_size <= 0:
        raise ValueError("buy/sell size must be positive")

    flags = list(risk_flags or [])
    marker = Path(panic_path) if panic_path is not None else DEFAULT_PANIC_PATH
    panic_active = bool(panic) or marker.exists()
    reasons = []
    if panic_active:
        reasons.append("panic")
    if flags:
        reasons.append("risk_flags")
    if label == "hold":
        reasons.append("hold_signal")
    if not authorized:
        reasons.append("explicit_authorization_missing")
    if price is None:
        reasons.append("price_missing")
    else:
        try:
            checked_price = float(price)
        except (TypeError, ValueError) as exc:
            raise ValueError("price must be finite and positive") from exc
        if not math.isfinite(checked_price) or checked_price <= 0:
            raise ValueError("price must be finite and positive")
    if confidence is None:
        reasons.append("confidence_missing")
    else:
        try:
            checked_confidence = float(confidence)
        except (TypeError, ValueError) as exc:
            raise ValueError("confidence must be finite and within [0, 1]") from exc
        if not math.isfinite(checked_confidence) or not 0 <= checked_confidence <= 1:
            raise ValueError("confidence must be finite and within [0, 1]")

    blocked = bool(reasons)
    return {
        "decision": label,
        "requested_size": requested_size,
        "status": "BLOCKED_REVIEW_ONLY" if blocked else "REVIEW_REQUIRED",
        "authorized": bool(authorized),
        "panic_active": panic_active,
        "trading_enabled": False,
        "orders_created": False,
        "orders_executed": False,
        "block_reasons": reasons,
    }


def execute_order(*args, **kwargs) -> dict[str, Any]:
    """Live execution remains deliberately unavailable, regardless of arguments."""
    return {
        "status": "DENIED",
        "reason": "Live execution is not implemented in CatedralX",
        "trading_enabled": False,
        "orders_created": False,
        "orders_executed": False,
    }
