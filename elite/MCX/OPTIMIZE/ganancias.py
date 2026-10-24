"""Append-only results ledger; this module never places orders."""
from __future__ import annotations
import json, os
from pathlib import Path
def ledger_path() -> Path:
    return Path(os.environ.get("CATEDRALX_LEDGER_PATH", str(Path.home()/".local/state/chalamandra/catedralx/ledger.jsonl"))).expanduser()
def registrar_resultado(record: dict, path: str | Path | None = None) -> Path:
    target = Path(path).expanduser() if path else ledger_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    safe = dict(record)
    safe["orders_executed_by_this_module"] = False
    with target.open("a", encoding="utf-8") as f:
        f.write(json.dumps(safe, ensure_ascii=False, allow_nan=False) + "\n")
    return target
