"""Atomic snapshot writer. Callers must supply observed data."""
from __future__ import annotations
import json, os, tempfile
from pathlib import Path
from typing import Any
from .sensors import normalize_market_payload

def snapshot_path() -> Path:
    return Path(os.environ.get("CATEDRALX_SNAPSHOT_PATH", "/dev/shm/cathedral_snapshot.json")).expanduser()

def write_observation(payload: dict[str, Any], path: str | Path | None = None) -> Path:
    data = normalize_market_payload(payload)
    target = Path(path).expanduser() if path else snapshot_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    envelope = {"PERCEIVE": data}
    fd, tmp = tempfile.mkstemp(prefix=target.name + ".", dir=str(target.parent), text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(envelope, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, target)
    except Exception:
        try: os.unlink(tmp)
        except OSError: pass
        raise
    return target
