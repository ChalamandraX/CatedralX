"""Freshness and availability checks for local feed snapshots."""
from __future__ import annotations
import json, time
from pathlib import Path
from .data_feeder import snapshot_path

def check_snapshot(path: str | Path | None = None, max_age_seconds: float = 60.0, now: float | None = None) -> dict:
    target = Path(path) if path else snapshot_path()
    current = time.time() if now is None else float(now)
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
        age = max(0.0, current - target.stat().st_mtime)
        has_prices = isinstance(payload.get("PERCEIVE", {}).get("historial_precios"), list)
        healthy = has_prices and age <= max_age_seconds
        return {"healthy": healthy, "exists": True, "age_seconds": age, "has_prices": has_prices, "path": str(target)}
    except (OSError, ValueError, TypeError):
        return {"healthy": False, "exists": target.exists(), "age_seconds": None, "has_prices": False, "path": str(target)}
