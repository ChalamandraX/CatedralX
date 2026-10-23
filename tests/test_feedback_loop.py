"""Tests for prediction IDs, observed outcomes, and offline evaluation."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from FEX.FEEDBACK.feedback_loop import (
    evaluar_feedback,
    registrar_prediccion,
    registrar_resultado,
)


def stamp(offset_seconds: int = 0) -> str:
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return (base + timedelta(seconds=offset_seconds)).isoformat()


def prediction(signal="buy", regime="TREND_ALCISTA", offset=0, price=100.0):
    return {
        "decision": signal,
        "signal_strength": 0.7,
        "signal_strength_is_probability": False,
        "regime": regime,
        "reference_price": price,
        "observed_at": stamp(offset),
        "market_source": "binance_spot_public:BTCUSDT:1m",
        "trading_enabled": False,
        "orders_created": False,
        "orders_executed": False,
    }


def label(path, prediction_id, horizon, delta_pct, elapsed=None):
    seconds = {"1m": 60, "5m": 300, "15m": 900, "1h": 3600}[horizon]
    elapsed = seconds if elapsed is None else elapsed
    return registrar_resultado(
        prediction_id,
        {
            "horizon": horizon,
            "observed_price": 100 * (1 + delta_pct / 100),
            "observed_at": stamp(elapsed),
            "source": "binance_spot_public:BTCUSDT:1m",
        },
        path,
    )


def test_prediction_gets_unique_id_and_recorded_type(tmp_path):
    path = tmp_path / "feedback.jsonl"
    first = registrar_prediccion(prediction(), path)
    second = registrar_prediccion(prediction(signal="sell"), path)

    assert first != second
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    assert [row["record_type"] for row in rows] == ["prediction", "prediction"]
    assert {row["prediction_id"] for row in rows} == {first, second}


def test_prediction_id_duplicate_is_rejected(tmp_path):
    path = tmp_path / "feedback.jsonl"
    registrar_prediccion(prediction(), path, prediction_id="fixed-id")

    with pytest.raises(ValueError, match="ya existe"):
        registrar_prediccion(prediction(), path, prediction_id="fixed-id")


def test_result_requires_existing_prediction(tmp_path):
    with pytest.raises(ValueError, match="no existe"):
        registrar_resultado(
            "missing",
            {"horizon": "5m", "observed_price": 101, "observed_at": stamp(300)},
            tmp_path / "feedback.jsonl",
        )


def test_result_uses_observed_price_and_checks_horizon(tmp_path):
    path = tmp_path / "feedback.jsonl"
    identifier = registrar_prediccion(prediction(), path)

    with pytest.raises(ValueError, match="Horizonte aún no vencido"):
        label(path, identifier, "5m", 1.0, elapsed=240)

    label(path, identifier, "5m", 1.0)
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    result = rows[-1]["outcome"]
    assert result["realized_return_pct"] == pytest.approx(1.0)
    assert result["actual_signal"] == "buy"
    assert result["horizon"] == "5m"


def test_result_rejects_too_late_observation_and_duplicate_horizon(tmp_path):
    path = tmp_path / "feedback.jsonl"
    identifier = registrar_prediccion(prediction(), path)

    with pytest.raises(ValueError, match="demasiado tardía"):
        label(path, identifier, "1m", 0.5, elapsed=200)

    label(path, identifier, "1m", 0.5)
    with pytest.raises(ValueError, match="Ya existe un resultado"):
        label(path, identifier, "1m", 0.5)


def test_one_prediction_can_have_different_horizons(tmp_path):
    path = tmp_path / "feedback.jsonl"
    identifier = registrar_prediccion(prediction(), path)
    label(path, identifier, "1m", 0.6)
    label(path, identifier, "5m", -0.2)

    report = evaluar_feedback(path)
    assert report["outcomes_scored"] == 2
    assert set(report["metrics_by_horizon"]) == {"1m", "5m"}


def test_evaluator_computes_confusion_accuracy_and_regime_metrics(tmp_path):
    path = tmp_path / "feedback.jsonl"
    p1 = registrar_prediccion(prediction("buy", "TREND_ALCISTA"), path)
    p2 = registrar_prediccion(prediction("sell", "TREND_BAJISTA"), path)
    p3 = registrar_prediccion(prediction("hold", "VOLATILIDAD_EN_EXPANSION"), path)
    label(path, p1, "5m", 0.6)
    label(path, p2, "5m", -0.7)
    label(path, p3, "5m", 0.01)

    report = evaluar_feedback(path)
    metrics = report["metrics_by_horizon"]["5m"]

    assert metrics["labelled_count"] == 3
    assert metrics["accuracy"] == 1.0
    assert metrics["confusion_matrix_predicted_rows_actual_columns"]["buy"]["buy"] == 1
    assert metrics["confusion_matrix_predicted_rows_actual_columns"]["sell"]["sell"] == 1
    assert metrics["confusion_matrix_predicted_rows_actual_columns"]["hold"]["hold"] == 1
    assert "5m|TREND_ALCISTA" in report["metrics_by_horizon_and_regime"]
    assert metrics["not_portfolio_pnl"] is True
    assert report["automatic_retraining"] is False
    assert report["trading_enabled"] is False


def test_evaluator_marks_unlabeled_predictions_as_pending(tmp_path):
    path = tmp_path / "feedback.jsonl"
    registrar_prediccion(prediction(), path)
    report = evaluar_feedback(path)

    assert report["predictions_recorded"] == 1
    assert report["predictions_pending_outcome"] == 1
    assert report["outcomes_scored"] == 0
    assert report["metrics_by_horizon"] == {}


def test_evaluator_does_not_treat_strength_as_probability(tmp_path):
    path = tmp_path / "feedback.jsonl"
    identifier = registrar_prediccion(prediction(), path)
    label(path, identifier, "1m", 0.4)

    report = evaluar_feedback(path)
    metrics = report["metrics_by_horizon"]["1m"]

    assert metrics["not_probability_calibration"] is True
    assert "brier_score" not in metrics


def test_malformed_feedback_line_fails_closed(tmp_path):
    path = tmp_path / "feedback.jsonl"
    path.write_text('{"record_type":"prediction"}\ninvalid\n', encoding="utf-8")

    with pytest.raises(ValueError, match="línea 2"):
        evaluar_feedback(path)


def test_reason_output_includes_prediction_id_and_observed_reference(
    tmp_path, monkeypatch, capsys
):
    from REASON import razon

    from datetime import datetime, timezone

    observed_at = datetime.now(timezone.utc).isoformat()
    snapshot_path = tmp_path / "snapshot.json"
    snapshot_path.write_text(
        json.dumps({
            "PERCEIVE": {
                "historial_precios": [100.0 + i * 0.01 for i in range(30)],
                "precio": 100.29,
                "observed_at": observed_at,
                "source": "test:BTCUSDT:1m",
            }
        }),
        encoding="utf-8",
    )
    feedback_path = tmp_path / "history.jsonl"
    monkeypatch.setenv("CATEDRALX_SNAPSHOT_PATH", str(snapshot_path))
    monkeypatch.setenv("CATEDRALX_FEEDBACK_PATH", str(feedback_path))
    state = SimpleNamespace(
        decision="hold",
        confianza=0.0,
        regimen="INDEFINIDO",
        señal_combinada="lateral",
        free_energy=0.2,
        percepcion_espacial={
            "hurst": 0.5,
            "analisis_financiero": {"latest_price": 100.29},
            "decision_subsistema_original": "hold",
        },
    )
    monkeypatch.setattr(razon, "execute_cycle", lambda _sensory: state)

    assert razon.main() == 0
    output = json.loads(capsys.readouterr().out)
    stored = json.loads(feedback_path.read_text().splitlines()[0])

    assert output["prediction_id"] == stored["prediction_id"]
    assert output["reference_price"] == pytest.approx(100.29)
    assert output["observed_at"] == observed_at
    assert stored["prediction"]["market_source"] == "test:BTCUSDT:1m"
def test_evaluator_reports_legacy_predictions_without_ids(tmp_path):
    path = tmp_path / "legacy.jsonl"
    path.write_text(
        json.dumps({
            "timestamp": 123.0,
            "prediction": {"signal": "hold"},
            "outcome": None,
            "learning_status": "awaiting_labeled_outcome",
        }) + "\n",
        encoding="utf-8",
    )

    report = evaluar_feedback(path)

    assert report["predictions_recorded"] == 1
    assert report["legacy_unlinked_predictions"] == 1
    assert report["identified_predictions"] == 0
    assert report["predictions_pending_outcome"] == 0

def test_result_rejects_different_market_source(tmp_path):
    path = tmp_path / "feedback.jsonl"
    identifier = registrar_prediccion(prediction(), path)

    with pytest.raises(ValueError, match="no coincide"):
        registrar_resultado(
            identifier,
            {
                "horizon": "1m",
                "observed_price": 101,
                "observed_at": stamp(60),
                "source": "binance_spot_public:ETHUSDT:1m",
            },
            path,
        )
