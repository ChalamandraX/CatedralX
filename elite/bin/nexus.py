"""Read-only status summary for CatedralX."""
from __future__ import annotations
import json, sys, time
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
from PERCEIVE.api_pulse import check_snapshot
from REASON.state_paths import canonical_state_path

def state_path() -> Path:
    return canonical_state_path()

def status() -> dict:
    target = state_path()
    try:
        state = json.loads(target.read_text(encoding="utf-8"))
        age = max(0.0, time.time() - target.stat().st_mtime)
        available = isinstance(state, dict)
    except (OSError, ValueError):
        state, age, available = {}, None, False
    return {"project": "CatedralX", "state_available": available, "state_age_seconds": age,
            "feed": check_snapshot(), "trading_enabled": False, "orders_created": False,
            "orders_executed": False, "state_preview": state.get("contexto", {}) if available else {}}

if __name__ == "__main__":
    print(json.dumps(status(), indent=2, ensure_ascii=False))
