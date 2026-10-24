#!/usr/bin/env python3
"""Print a read-only offline report of labeled CatedralX predictions."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ELITE_DIR = Path(__file__).resolve().parents[1]
if str(ELITE_DIR) not in sys.path:
    sys.path.insert(0, str(ELITE_DIR))

from FEX.FEEDBACK.feedback_loop import evaluar_feedback


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", help="Ruta opcional del historial feedback.jsonl")
    args = parser.parse_args()
    try:
        print(json.dumps(
            evaluar_feedback(args.path),
            ensure_ascii=False,
            indent=2,
            allow_nan=False,
        ))
        return 0
    except (OSError, ValueError) as exc:
        print(json.dumps({
            "report_status": "error",
            "reason": str(exc),
            "automatic_retraining": False,
            "trading_enabled": False,
        }, ensure_ascii=False, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
