"""Append-only, human-governed cycle for value, impact, and reinvestment proposals.

This ledger records evidence and approvals; it does not move money, place orders,
change model parameters, or claim causal impact from correlation alone.
"""

from __future__ import annotations

import json
import math
import os
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
EVENTS = ("measure", "evaluate", "propose", "authorize", "verify", "feedback")
NEXT_EVENT = {
    "measure": "evaluate",
    "evaluate": "propose",
    "propose": "authorize",
    "authorize": "verify",
    "verify": "feedback",
}


def ledger_path() -> Path:
    return Path(
        os.environ.get(
            "CATEDRALX_IMPACT_LEDGER_PATH",
            str(Path.home() / ".local/state/chalamandra/catedralx/impact_cycle.jsonl"),
        )
    ).expanduser()


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} debe ser texto no vacío.")
    return value.strip()


def _timestamp(value: Any, field: str) -> str:
    text_value = _text(value, field)
    try:
        parsed = datetime.fromisoformat(text_value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} debe ser ISO-8601.") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} debe incluir zona horaria.")
    return text_value


def _number(value: Any, field: str) -> float:
    if isinstance(value, bool):
        raise TypeError(f"{field} debe ser un número finito.")
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{field} debe ser un número finito.") from exc
    if not math.isfinite(result):
        raise ValueError(f"{field} debe ser un número finito.")
    return result


def _read(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as stream:
        for line_no, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Ledger de impacto inválido en línea {line_no}."
                ) from exc
            if not isinstance(item, dict):
                raise TypeError(f"Registro de impacto inválido en línea {line_no}.")
            records.append(item)
    return records


def _append(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(
            json.dumps(record, ensure_ascii=False, allow_nan=False, sort_keys=True)
            + "\n"
        )


def registrar_evento(
    event_type: str,
    payload: dict[str, Any],
    path: str | Path | None = None,
    *,
    cycle_id: str | None = None,
) -> str:
    """Validate and append one governed event. Each cycle advances one stage at a time."""
    kind = _text(event_type, "event_type")
    if kind not in EVENTS:
        raise ValueError("event_type debe ser uno de: " + ", ".join(EVENTS))
    if not isinstance(payload, dict):
        raise TypeError("payload debe ser un objeto.")
    target = Path(path).expanduser() if path else ledger_path()
    records = _read(target)
    identifier = _text(cycle_id, "cycle_id") if cycle_id else str(uuid.uuid4())
    existing = [row for row in records if row.get("cycle_id") == identifier]

    if kind == "measure":
        if existing:
            raise ValueError(
                "El ciclo ya existe; measure debe iniciar un cycle_id nuevo."
            )
        for field in ("metric", "source", "period", "unit", "formula"):
            _text(payload.get(field), field)
        _number(payload.get("value"), "value")
        if payload.get("target") is not None:
            _number(payload["target"], "target")
        if payload.get("uncertainty") is not None:
            uncertainty = _number(payload["uncertainty"], "uncertainty")
            if uncertainty < 0:
                raise ValueError("uncertainty no puede ser negativa.")
        _timestamp(payload.get("observed_at"), "observed_at")
    else:
        if not existing:
            raise ValueError("El ciclo no existe; primero registra measure.")
        last = existing[-1]
        expected = NEXT_EVENT.get(last["event_type"])
        if kind != expected:
            raise ValueError(
                f"Transición inválida: después de {last['event_type']} se requiere {expected}."
            )
        if kind == "evaluate":
            _text(payload.get("assessment"), "assessment")
            _text(payload.get("evidence"), "evidence")
            if payload.get("causal_claim") is True and not _text(
                payload.get("causal_method"), "causal_method"
            ):
                raise ValueError(
                    "Una afirmación causal requiere causal_method explícito."
                )
        elif kind == "propose":
            _text(payload.get("proposal"), "proposal")
            _text(payload.get("expected_outcome"), "expected_outcome")
            _text(payload.get("verification_plan"), "verification_plan")
            if "allocation_pct" in payload or "allocation_percent" in payload:
                raise ValueError(
                    "No se aceptan porcentajes de asignación arbitrarios; aporta evidencia y aprobación explícita."
                )
        elif kind == "authorize":
            _text(payload.get("approver"), "approver")
            _text(payload.get("rationale"), "rationale")
            if payload.get("approved") is not True:
                raise ValueError(
                    "authorize requiere approved=true; para rechazar, registra la decisión fuera de este ciclo aprobado."
                )
        elif kind == "verify":
            _text(payload.get("evidence"), "evidence")
            _text(payload.get("result"), "result")
            _timestamp(payload.get("verified_at"), "verified_at")
        elif kind == "feedback":
            _text(payload.get("lesson"), "lesson")
            _text(payload.get("next_action"), "next_action")

    event_id = str(uuid.uuid4())
    _append(
        target,
        {
            "schema_version": SCHEMA_VERSION,
            "event_id": event_id,
            "cycle_id": identifier,
            "event_type": kind,
            "recorded_at_epoch": time.time(),
            "payload": dict(payload),
            "controls": {
                "human_approval_required": kind == "authorize",
                "money_moved": False,
                "trading_enabled": False,
                "automatic_retraining": False,
            },
        },
    )
    return identifier


def resumir_ciclos(path: str | Path | None = None) -> dict[str, Any]:
    """Return a read-only summary of stages and governance controls."""
    target = Path(path).expanduser() if path else ledger_path()
    records = _read(target)
    cycles: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        identifier = record.get("cycle_id")
        if not isinstance(identifier, str):
            raise TypeError("Registro sin cycle_id válido.")
        cycles.setdefault(identifier, []).append(record)
    summary = []
    for identifier, events in cycles.items():
        kinds = [event.get("event_type") for event in events]
        summary.append(
            {
                "cycle_id": identifier,
                "stage": kinds[-1],
                "events": kinds,
                "complete": kinds[-1] == "feedback",
                "human_authorized": "authorize" in kinds,
                "money_moved": False,
                "trading_enabled": False,
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "cycles_recorded": len(summary),
        "cycles_complete": sum(row["complete"] for row in summary),
        "cycles_pending": sum(not row["complete"] for row in summary),
        "cycles": summary,
        "read_only": True,
        "automatic_reinvestment": False,
        "automatic_retraining": False,
        "trading_enabled": False,
    }
