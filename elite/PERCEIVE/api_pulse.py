"""Validate snapshot schema and market-observation freshness."""
from __future__ import annotations

from datetime import datetime
import json
import math
import time
from pathlib import Path

from .data_feeder import snapshot_path

DEFAULT_MAX_AGE_SECONDS = 120.0
FUTURE_CLOCK_TOLERANCE_SECONDS = 5.0


def validate_snapshot_payload(
    payload: object,
    max_age_seconds: float = DEFAULT_MAX_AGE_SECONDS,
    now: float | None = None,
) -> dict:
    """Validate observed price history and its source timestamp, not file mtime."""
    current = time.time() if now is None else float(now)

    def rejected(reason: str, *, age=None, observed_at=None, has_prices=False) -> dict:
        return {
            "healthy": False,
            "reason": reason,
            "age_seconds": age,
            "observed_at": observed_at,
            "has_prices": has_prices,
            "max_age_seconds": max_age_seconds,
        }

    if (
        not math.isfinite(current)
        or not math.isfinite(float(max_age_seconds))
        or max_age_seconds <= 0
    ):
        return rejected("invalid_time_configuration")

    if not isinstance(payload, dict):
        return rejected("invalid_snapshot_schema")

    perceive = payload.get("PERCEIVE")
    if not isinstance(perceive, dict):
        return rejected("missing_perceive_section")

    prices = perceive.get("historial_precios")
    if not isinstance(prices, list) or len(prices) < 30:
        return rejected("insufficient_price_history")

    try:
        for price in prices:
            if isinstance(price, bool):
                raise ValueError
            value = float(price)
            if not math.isfinite(value) or value <= 0:
                raise ValueError
        latest = float(perceive.get("precio", prices[-1]))
        if not math.isfinite(latest) or latest <= 0:
            raise ValueError
    except (TypeError, ValueError, OverflowError):
        return rejected("invalid_price_history", has_prices=True)

    observed_at = perceive.get("observed_at")
    if not isinstance(observed_at, str) or not observed_at.strip():
        return rejected("missing_observed_at", has_prices=True)

    try:
        parsed = datetime.fromisoformat(observed_at.strip().replace("Z", "+00:00"))
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            return rejected(
                "observed_at_requires_timezone",
                observed_at=observed_at,
                has_prices=True,
            )
        age = current - parsed.timestamp()
    except (ValueError, TypeError, OverflowError, OSError):
        return rejected(
            "invalid_observed_at",
            observed_at=observed_at,
            has_prices=True,
        )

    if age < -FUTURE_CLOCK_TOLERANCE_SECONDS:
        return rejected(
            "observation_from_future",
            age=age,
            observed_at=observed_at,
            has_prices=True,
        )

    age = max(0.0, age)
    if age > max_age_seconds:
        return rejected(
            "stale_observation",
            age=age,
            observed_at=observed_at,
            has_prices=True,
        )

    return {
        "healthy": True,
        "reason": "ok",
        "age_seconds": age,
        "observed_at": observed_at,
        "has_prices": True,
        "max_age_seconds": max_age_seconds,
    }


def check_snapshot(
    path: str | Path | None = None,
    max_age_seconds: float = DEFAULT_MAX_AGE_SECONDS,
    now: float | None = None,
) -> dict:
    """Read and validate the snapshot using market time, not file modification time."""
    target = Path(path) if path else snapshot_path()
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {
            "healthy": False, "reason": "snapshot_not_found",
            "exists": False, "age_seconds": None,
            "has_prices": False, "path": str(target),
        }
    except (OSError, ValueError, TypeError):
        return {
            "healthy": False, "reason": "snapshot_unreadable",
            "exists": target.exists(), "age_seconds": None,
            "has_prices": False, "path": str(target),
        }

    result = validate_snapshot_payload(payload, max_age_seconds, now)
    result["exists"] = True
    result["path"] = str(target)
    return result
