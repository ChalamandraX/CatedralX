"""Safe action gate: emits review-only intent and never sends orders."""
ALLOWED_LABELS = {"buy", "sell", "hold"}
def preparar_intencion(decision: str, size: float = 0.0, *, panic: bool = False, risk_flags=None) -> dict:
    label = str(decision).lower()
    if label not in ALLOWED_LABELS:
        raise ValueError("decision must be buy, sell or hold")
    size = float(size)
    if size < 0:
        raise ValueError("size must be non-negative")
    flags = list(risk_flags or [])
    blocked = bool(panic or flags or label == "hold")
    return {"decision": label, "requested_size": size,
            "status": "BLOCKED_REVIEW_ONLY" if blocked else "REVIEW_REQUIRED",
            "trading_enabled": False, "orders_created": False, "orders_executed": False,
            "block_reasons": (["panic"] if panic else []) + (["risk_flags"] if flags else [])}
def execute_order(*args, **kwargs) -> dict:
    return {"status": "DENIED", "reason": "Live execution is not implemented in CatedralX",
            "trading_enabled": False, "orders_created": False, "orders_executed": False}
