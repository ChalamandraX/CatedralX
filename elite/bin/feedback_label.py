#!/usr/bin/env python3
"""Label one prediction from a fresh observed snapshot; no orders."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ELITE_DIR = Path(__file__).resolve().parents[1]
if str(ELITE_DIR) not in sys.path:
    sys.path.insert(0, str(ELITE_DIR))

from FEX.FEEDBACK.feedback_loop import HORIZONS_SECONDS, registrar_resultado
from PERCEIVE.api_pulse import validate_snapshot_payload
from PERCEIVE.data_feeder import snapshot_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prediction_id", help="ID emitido por razon.py")
    parser.add_argument("--horizon", choices=tuple(HORIZONS_SECONDS), required=True)
    parser.add_argument("--snapshot", help="Ruta opcional del snapshot a etiquetar")
    parser.add_argument(
        "--neutral-threshold-pct",
        type=float,
        default=0.05,
        help="Retorno absoluto porcentual <= umbral se etiqueta hold (default: 0.05)",
    )
    args = parser.parse_args()

    target = Path(args.snapshot).expanduser() if args.snapshot else snapshot_path()
    try:
        snapshot = json.loads(target.read_text(encoding="utf-8"))
        freshness = validate_snapshot_payload(snapshot)
        if not freshness["healthy"]:
            raise ValueError("Snapshot rechazado: " + str(freshness["reason"]))
        perceive = snapshot["PERCEIVE"]
        feedback_path = registrar_resultado(
            args.prediction_id,
            {
                "horizon": args.horizon,
                "observed_price": perceive.get("precio"),
                "observed_at": perceive.get("observed_at"),
                "source": perceive.get("source"),
                "neutral_threshold_pct": args.neutral_threshold_pct,
            },
        )
        print(json.dumps({
            "status": "OUTCOME_RECORDED_NOT_RETRAINED",
            "prediction_id": args.prediction_id,
            "horizon": args.horizon,
            "feedback_path": str(feedback_path),
            "observed_at": perceive.get("observed_at"),
            "trading_enabled": False,
            "orders_created": False,
            "orders_executed": False,
        }, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({
            "status": "OUTCOME_NOT_RECORDED",
            "reason": str(exc),
            "trading_enabled": False,
            "orders_created": False,
            "orders_executed": False,
        }, ensure_ascii=False, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
