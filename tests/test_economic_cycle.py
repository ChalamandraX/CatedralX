"""Governance, auditability, and fail-closed tests for the impact cycle."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from FEX.GOVERNANCE.economic_cycle import registrar_evento, resumir_ciclos


def measure(path):
    return registrar_evento(
        "measure",
        {
            "metric": "personas_atendidas",
            "source": "registro_servicio_v1",
            "period": "2026-Q3",
            "unit": "personas",
            "formula": "conteo_unico_de_personas",
            "value": 120,
            "target": 150,
            "uncertainty": 3,
            "observed_at": "2026-10-23T10:00:00Z",
        },
        path,
    )


def test_cycle_requires_ordered_explicit_approval_and_stays_non_operational(tmp_path):
    path = tmp_path / "impact.jsonl"
    cycle = measure(path)
    with pytest.raises(ValueError, match="se requiere evaluate"):
        registrar_evento(
            "propose",
            {
                "proposal": "Mejorar cobertura",
                "expected_outcome": "Más personas atendidas",
                "verification_plan": "Comparar conteo trimestral",
            },
            path,
            cycle_id=cycle,
        )

    registrar_evento(
        "evaluate",
        {"assessment": "Por debajo del objetivo", "evidence": "registro_servicio_v1"},
        path,
        cycle_id=cycle,
    )
    registrar_evento(
        "propose",
        {
            "proposal": "Piloto de ampliación",
            "expected_outcome": "Aumentar cobertura",
            "verification_plan": "Medir conteo y coste por persona",
        },
        path,
        cycle_id=cycle,
    )
    with pytest.raises(ValueError, match="approved=true"):
        registrar_evento(
            "authorize",
            {"approved": False, "approver": "comité", "rationale": "pendiente"},
            path,
            cycle_id=cycle,
        )
    registrar_evento(
        "authorize",
        {
            "approved": True,
            "approver": "comité",
            "rationale": "Piloto acotado con revisión",
        },
        path,
        cycle_id=cycle,
    )
    registrar_evento(
        "verify",
        {
            "evidence": "informe de piloto",
            "result": "medición posterior registrada",
            "verified_at": "2026-11-01T00:00:00Z",
        },
        path,
        cycle_id=cycle,
    )
    registrar_evento(
        "feedback",
        {
            "lesson": "Medir coste por persona además del alcance",
            "next_action": "Revisar con nueva evidencia",
        },
        path,
        cycle_id=cycle,
    )

    report = resumir_ciclos(path)
    assert report["cycles_complete"] == 1
    assert report["automatic_reinvestment"] is False
    assert report["trading_enabled"] is False
    assert report["cycles"][0]["human_authorized"] is True
    assert all(
        json.loads(line)["controls"]["money_moved"] is False
        for line in path.read_text().splitlines()
    )


def test_measure_requires_traceable_metric_and_timezone(tmp_path):
    with pytest.raises(ValueError, match="source"):
        registrar_evento(
            "measure",
            {
                "metric": "x",
                "period": "Q3",
                "unit": "n",
                "formula": "count",
                "value": 2,
                "observed_at": "2026-10-23T10:00:00Z",
            },
            tmp_path / "ledger.jsonl",
        )
    with pytest.raises(ValueError, match="zona horaria"):
        registrar_evento(
            "measure",
            {
                "metric": "x",
                "source": "db",
                "period": "Q3",
                "unit": "n",
                "formula": "count",
                "value": 2,
                "observed_at": "2026-10-23T10:00:00",
            },
            tmp_path / "ledger.jsonl",
        )


def test_no_arbitrary_allocation_percentages_or_unsupported_causal_claim(tmp_path):
    path = tmp_path / "impact.jsonl"
    cycle = measure(path)
    with pytest.raises(ValueError, match="causal_method"):
        registrar_evento(
            "evaluate",
            {
                "assessment": "Subió la métrica",
                "evidence": "dashboard",
                "causal_claim": True,
            },
            path,
            cycle_id=cycle,
        )
    registrar_evento(
        "evaluate",
        {
            "assessment": "Subió la métrica",
            "evidence": "dashboard; no prueba causalidad",
        },
        path,
        cycle_id=cycle,
    )
    with pytest.raises(ValueError, match="porcentajes"):
        registrar_evento(
            "propose",
            {
                "proposal": "Reinvertir",
                "expected_outcome": "Más capacidad",
                "verification_plan": "Medir",
                "allocation_pct": 20,
            },
            path,
            cycle_id=cycle,
        )


def test_malformed_ledger_fails_closed(tmp_path):
    path = tmp_path / "impact.jsonl"
    path.write_text("not-json\n", encoding="utf-8")
    with pytest.raises(ValueError, match="línea 1"):
        resumir_ciclos(path)


def test_catedral_cli_exposes_governed_impact_report(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    ledger = tmp_path / "cli-impact.jsonl"
    completed = subprocess.run(
        [
            "bash",
            str(repo_root / "BIN/catedral"),
            "impact-cycle",
            "--report",
            "--path",
            str(ledger),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert completed.returncode == 0, completed.stderr
    report = json.loads(completed.stdout)
    assert report["read_only"] is True
    assert report["cycles_recorded"] == 0
    assert report["automatic_reinvestment"] is False
    assert report["trading_enabled"] is False
