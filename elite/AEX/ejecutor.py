"""Safe action gate: emits review-only intent and never sends orders."""

from __future__ import annotations

import math
from collections.abc import Iterable
from typing import Any

from contracts.actions import normalizar_senal

ALLOWED_LABELS = {"buy", "sell", "hold"}


def preparar_intencion(
    decision: str,
    size: float = 0.0,
    *,
    panic: bool = False,
    risk_flags: Iterable[Any] | None = None,
) -> dict[str, Any]:
    """Normalize a signal and produce review-only metadata, never an order."""
    label = normalizar_senal(decision)
    if isinstance(size, bool):
        raise TypeError("size debe ser numérico, finito y no negativo.")
    try:
        numeric_size = float(size)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("size debe ser numérico, finito y no negativo.") from exc
    if not math.isfinite(numeric_size) or numeric_size < 0:
        raise ValueError("size debe ser numérico, finito y no negativo.")

    if risk_flags is None:
        flags: list[Any] = []
    elif isinstance(risk_flags, (str, bytes)):
        flags = [risk_flags]
    else:
        try:
            flags = list(risk_flags)
        except TypeError as exc:
            raise ValueError("risk_flags debe ser una colección de alertas.") from exc

    block_reasons = []
    if panic:
        block_reasons.append("panic")
    if flags:
        block_reasons.append("risk_flags")
    if label == "hold":
        block_reasons.append("hold_signal")
    blocked = bool(block_reasons)

    return {
        "decision": label,
        "requested_size": numeric_size,
        "status": "BLOCKED_REVIEW_ONLY" if blocked else "REVIEW_REQUIRED",
        "trading_enabled": False,
        "orders_created": False,
        "orders_executed": False,
        "block_reasons": block_reasons,
    }


def execute_order(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Fail closed: live execution is deliberately not implemented."""
    return {
        "status": "DENIED",
        "reason": "Live execution is not implemented in CatedralX",
        "trading_enabled": False,
        "orders_created": False,
        "orders_executed": False,
    }
