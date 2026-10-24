#!/usr/bin/env python3
"""Record a governed impact-cycle event or print a read-only cycle summary."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ELITE_DIR = Path(__file__).resolve().parents[1]
if str(ELITE_DIR) not in sys.path:
    sys.path.insert(0, str(ELITE_DIR))

from FEX.GOVERNANCE.economic_cycle import (
    EVENTS,
    ledger_path,
    registrar_evento,
    resumir_ciclos,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event", choices=EVENTS, help="Etapa que se registrará")
    parser.add_argument("--payload", help="Objeto JSON con los datos de la etapa")
    parser.add_argument("--cycle-id", help="ID devuelto por la primera etapa measure")
    parser.add_argument("--path", help="Ruta opcional del ledger JSONL")
    parser.add_argument(
        "--report", action="store_true", help="Mostrar resumen de solo lectura"
    )
    args = parser.parse_args()
    try:
        if args.report:
            if args.event or args.payload or args.cycle_id:
                raise ValueError(
                    "--report no se combina con --event, --payload ni --cycle-id."
                )
            result: dict[str, Any] = resumir_ciclos(args.path)
        else:
            if not args.event or not args.payload:
                raise ValueError(
                    "Para registrar un evento se requieren --event y --payload JSON."
                )
            try:
                payload = json.loads(args.payload)
            except json.JSONDecodeError as exc:
                raise ValueError("--payload no contiene JSON válido.") from exc
            cycle_id = registrar_evento(
                args.event, payload, args.path, cycle_id=args.cycle_id
            )
            result = {
                "status": "EVENT_RECORDED_NOT_EXECUTED",
                "event_type": args.event,
                "cycle_id": cycle_id,
                "ledger_path": str(Path(args.path).expanduser())
                if args.path
                else str(ledger_path()),
                "money_moved": False,
                "trading_enabled": False,
                "automatic_reinvestment": False,
            }
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        return 0
    except (OSError, TypeError, ValueError) as exc:
        print(
            json.dumps(
                {
                    "status": "EVENT_NOT_RECORDED",
                    "reason": str(exc),
                    "money_moved": False,
                    "trading_enabled": False,
                    "automatic_reinvestment": False,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
