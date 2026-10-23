"""Append-only prediction/outcome records; no automatic model updates."""
from __future__ import annotations
import json, os, time
from pathlib import Path

def history_path() -> Path:
    return Path(os.environ.get("CATEDRALX_FEEDBACK_PATH",
        str(Path.home()/".local/state/chalamandra/catedralx/feedback.jsonl"))).expanduser()

def registrar_prediccion(prediction: dict, path: str | Path | None = None) -> Path:
    target = Path(path).expanduser() if path else history_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    record = {"timestamp": time.time(), "prediction": dict(prediction), "outcome": None,
              "learning_status": "awaiting_labeled_outcome"}
    with target.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n")
    return target

def registrar_resultado(prediction_id: str, outcome: dict, path: str | Path | None = None) -> Path:
    target = Path(path).expanduser() if path else history_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    record = {"timestamp": time.time(), "prediction_id": str(prediction_id), "outcome": dict(outcome),
              "learning_status": "labeled_outcome_recorded_not_retrained"}
    with target.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n")
    return target
