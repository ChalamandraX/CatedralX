"""Append-only prediction/outcome ledger and offline evaluation.

Outcomes are labeled from observed prices at fixed horizons. This module
computes reports only; it never retrains a model or submits orders.
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

from contracts.actions import normalizar_senal

SCHEMA_VERSION = 1
HORIZONS_SECONDS = {"1m": 60, "5m": 300, "15m": 900, "1h": 3600}
MAX_HORIZON_OVERRUN_SECONDS = 120
DEFAULT_NEUTRAL_THRESHOLD_PCT = 0.05
SIGNALS = ("buy", "sell", "hold")


def history_path() -> Path:
    return Path(
        os.environ.get(
            "CATEDRALX_FEEDBACK_PATH",
            str(Path.home() / ".local/state/chalamandra/catedralx/feedback.jsonl"),
        )
    ).expanduser()


def _target_path(path: str | Path | None) -> Path:
    return Path(path).expanduser() if path else history_path()


def _read_records(target: Path) -> list[dict[str, Any]]:
    if not target.exists():
        return []
    records: list[dict[str, Any]] = []
    with target.open("r", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Feedback JSONL inválido en línea {line_number}."
                ) from exc
            if not isinstance(record, dict):
                raise ValueError(
                    f"Registro de feedback no es objeto en línea {line_number}."
                )
            # Backward compatibility with the initial append-only format.
            if "record_type" not in record:
                if isinstance(record.get("prediction"), dict):
                    record["record_type"] = "prediction"
                elif record.get("prediction_id") and isinstance(
                    record.get("outcome"), dict
                ):
                    record["record_type"] = "outcome"
            records.append(record)
    return records


def _append_record(target: Path, record: dict[str, Any]) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as stream:
        stream.write(
            json.dumps(record, ensure_ascii=False, allow_nan=False, sort_keys=True)
            + "\n"
        )


def _nonblank(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} debe ser texto no vacío.")
    return value.strip()


def _finite_positive(value: Any, name: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{name} debe ser positivo y finito.")
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} debe ser positivo y finito.") from exc
    if not math.isfinite(number) or number <= 0:
        raise ValueError(f"{name} debe ser positivo y finito.")
    return number


def _parse_aware_timestamp(value: Any, name: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} debe ser una fecha ISO-8601 con zona horaria.")
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} no es una fecha ISO-8601 válida.") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{name} requiere zona horaria.")
    return parsed


def _prediction_for_id(records: list[dict[str, Any]], prediction_id: str) -> dict[str, Any]:
    matches = [
        record
        for record in records
        if record.get("record_type") == "prediction"
        and record.get("prediction_id") == prediction_id
        and isinstance(record.get("prediction"), dict)
    ]
    if not matches:
        raise ValueError("prediction_id no existe en el historial de feedback.")
    if len(matches) != 1:
        raise ValueError("prediction_id duplicado; el historial requiere revisión.")
    return matches[0]


def registrar_prediccion(
    prediction: dict[str, Any],
    path: str | Path | None = None,
    *,
    prediction_id: str | None = None,
) -> str:
    """Append one prediction and return its stable ID for future labeling."""
    if not isinstance(prediction, dict):
        raise ValueError("prediction debe ser un objeto.")
    target = _target_path(path)
    identifier = (
        _nonblank(prediction_id, "prediction_id")
        if prediction_id
        else str(uuid.uuid4())
    )
    records = _read_records(target)
    if any(
        record.get("record_type") == "prediction"
        and record.get("prediction_id") == identifier
        for record in records
    ):
        raise ValueError("prediction_id ya existe en el historial.")
    _append_record(
        target,
        {
            "schema_version": SCHEMA_VERSION,
            "record_type": "prediction",
            "prediction_id": identifier,
            "recorded_at_epoch": time.time(),
            "prediction": dict(prediction),
            "learning_status": "awaiting_labeled_outcome",
        },
    )
    return identifier


def registrar_resultado(
    prediction_id: str,
    outcome: dict[str, Any],
    path: str | Path | None = None,
) -> Path:
    """Append an observed-price outcome linked to a prediction and fixed horizon.

    Required input keys: horizon, observed_price, observed_at. Reference price
    and timestamp come from the stored prediction, never from caller input.
    """
    identifier = _nonblank(prediction_id, "prediction_id")
    if not isinstance(outcome, dict):
        raise ValueError("outcome debe ser un objeto.")
    target = _target_path(path)
    records = _read_records(target)
    prediction_record = _prediction_for_id(records, identifier)
    prediction = prediction_record["prediction"]

    horizon = _nonblank(outcome.get("horizon"), "horizon")
    if horizon not in HORIZONS_SECONDS:
        raise ValueError("horizon debe ser uno de: " + ", ".join(HORIZONS_SECONDS))

    prior_outcomes = [
        record
        for record in records
        if record.get("record_type") == "outcome"
        and record.get("prediction_id") == identifier
        and (
            record.get("horizon")
            or (record.get("outcome") or {}).get("horizon")
        ) == horizon
    ]
    if prior_outcomes:
        raise ValueError(f"Ya existe un resultado etiquetado para el horizonte {horizon}.")

    reference_price = prediction.get("reference_price")
    if reference_price is None:
        reference_price = (prediction.get("financial_analysis") or {}).get("latest_price")
    reference_price = _finite_positive(reference_price, "reference_price")
    observed_price = _finite_positive(outcome.get("observed_price"), "observed_price")
    expected_source = prediction.get("market_source") or prediction.get("source")
    observed_source = outcome.get("source")
    if expected_source:
        if not isinstance(observed_source, str) or not observed_source.strip():
            raise ValueError("outcome.source requerido para vincular la fuente de mercado.")
        if observed_source.strip() != expected_source:
            raise ValueError(
                "La fuente de mercado del resultado no coincide con la predicción."
            )
    reference_time = _parse_aware_timestamp(
        prediction.get("observed_at"), "prediction.observed_at"
    )
    observed_time = _parse_aware_timestamp(outcome.get("observed_at"), "outcome.observed_at")
    elapsed_seconds = (observed_time - reference_time).total_seconds()
    target_seconds = HORIZONS_SECONDS[horizon]
    if elapsed_seconds < target_seconds:
        raise ValueError(
            f"Horizonte aún no vencido: {elapsed_seconds:.1f}s observados; "
            f"se requieren {target_seconds}s para {horizon}."
        )
    if elapsed_seconds > target_seconds + MAX_HORIZON_OVERRUN_SECONDS:
        raise ValueError(
            f"Observación demasiado tardía para {horizon}: {elapsed_seconds:.1f}s; "
            f"tolerancia adicional {MAX_HORIZON_OVERRUN_SECONDS}s."
        )

    threshold = outcome.get("neutral_threshold_pct", DEFAULT_NEUTRAL_THRESHOLD_PCT)
    if isinstance(threshold, bool):
        raise ValueError("neutral_threshold_pct debe ser un número positivo y finito.")
    try:
        threshold = float(threshold)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(
            "neutral_threshold_pct debe ser un número positivo y finito."
        ) from exc
    if not math.isfinite(threshold) or threshold <= 0:
        raise ValueError("neutral_threshold_pct debe ser un número positivo y finito.")

    realized_return_pct = (observed_price / reference_price - 1.0) * 100.0
    if not math.isfinite(realized_return_pct):
        raise ValueError("El rendimiento observado no es finito.")
    if realized_return_pct >= threshold:
        actual_signal = "buy"
    elif realized_return_pct <= -threshold:
        actual_signal = "sell"
    else:
        actual_signal = "hold"

    labeled_outcome = {
        "horizon": horizon,
        "reference_price": reference_price,
        "observed_price": observed_price,
        "source": observed_source,
        "reference_observed_at": reference_time.isoformat(),
        "observed_at": observed_time.isoformat(),
        "elapsed_seconds": round(elapsed_seconds, 3),
        "realized_return_pct": round(realized_return_pct, 8),
        "neutral_threshold_pct": threshold,
        "actual_signal": actual_signal,
        "label_definition": (
            "buy if realized return >= threshold; sell if <= -threshold; "
            "hold otherwise"
        ),
    }
    _append_record(
        target,
        {
            "schema_version": SCHEMA_VERSION,
            "record_type": "outcome",
            "prediction_id": identifier,
            "horizon": horizon,
            "recorded_at_epoch": time.time(),
            "outcome": labeled_outcome,
            "learning_status": "labeled_outcome_recorded_not_retrained",
        },
    )
    return target


def _safe_signal(prediction: dict[str, Any]) -> str | None:
    signal = prediction.get("decision", prediction.get("signal"))
    try:
        normalized = normalizar_senal(signal)
    except (TypeError, ValueError):
        return None
    return normalized if normalized in SIGNALS else None


def _safe_return(outcome: dict[str, Any]) -> float | None:
    value = outcome.get("realized_return_pct")
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) else None


def _metric_bundle(rows: list[dict[str, Any]]) -> dict[str, Any]:
    confusion = {pred: {actual: 0 for actual in SIGNALS} for pred in SIGNALS}
    correct = 0
    returns: list[float] = []
    aligned_returns: list[float] = []

    for row in rows:
        predicted = row["predicted_signal"]
        actual = row["actual_signal"]
        confusion[predicted][actual] += 1
        correct += int(predicted == actual)
        realized = row["realized_return_pct"]
        returns.append(realized)
        if predicted == "buy":
            aligned_returns.append(realized)
        elif predicted == "sell":
            aligned_returns.append(-realized)

    count = len(rows)
    per_signal: dict[str, Any] = {}
    for signal in SIGNALS:
        tp = confusion[signal][signal]
        predicted_total = sum(confusion[signal].values())
        actual_total = sum(confusion[predicted][signal] for predicted in SIGNALS)
        per_signal[signal] = {
            "precision": round(tp / predicted_total, 6) if predicted_total else None,
            "recall": round(tp / actual_total, 6) if actual_total else None,
            "support": actual_total,
            "predicted_count": predicted_total,
        }

    return {
        "labelled_count": count,
        "accuracy": round(correct / count, 6) if count else None,
        "correct_count": correct,
        "confusion_matrix_predicted_rows_actual_columns": confusion,
        "per_signal": per_signal,
        "realized_return_mean_pct": round(sum(returns) / count, 8) if count else None,
        "mean_signal_aligned_return_pct_directional_only": (
            round(sum(aligned_returns) / len(aligned_returns), 8)
            if aligned_returns
            else None
        ),
        "directional_signal_sample_count_excluding_hold": len(aligned_returns),
        "not_portfolio_pnl": True,
        "not_probability_calibration": True,
    }


def evaluar_feedback(path: str | Path | None = None) -> dict[str, Any]:
    """Compute offline reproducible statistics; no training or external writes."""
    records = _read_records(_target_path(path))
    predictions: dict[str, dict[str, Any]] = {}
    prediction_count = 0
    legacy_unlinked_predictions = 0
    duplicate_prediction_ids = 0
    raw_outcomes: list[dict[str, Any]] = []
    legacy_unlinked_outcomes = 0

    for record in records:
        record_type = record.get("record_type")
        if record_type == "prediction":
            prediction_count += 1
            identifier = record.get("prediction_id")
            prediction = record.get("prediction")
            if not isinstance(identifier, str) or not identifier.strip():
                legacy_unlinked_predictions += 1
                continue
            if not isinstance(prediction, dict):
                continue
            if identifier in predictions:
                duplicate_prediction_ids += 1
                continue
            predictions[identifier] = prediction
        elif record_type == "outcome":
            if not isinstance(record.get("prediction_id"), str):
                legacy_unlinked_outcomes += 1
                continue
            raw_outcomes.append(record)

    valid_rows: list[dict[str, Any]] = []
    unscored_outcomes = 0
    duplicate_outcomes = 0
    seen_keys: set[tuple[str, str]] = set()
    labeled_predictions: set[str] = set()

    for record in raw_outcomes:
        identifier = record["prediction_id"]
        outcome = record.get("outcome")
        horizon = record.get("horizon") or (
            outcome.get("horizon") if isinstance(outcome, dict) else None
        )
        prediction = predictions.get(identifier)
        if not prediction or not isinstance(horizon, str) or not isinstance(outcome, dict):
            unscored_outcomes += 1
            continue
        key = (identifier, horizon)
        if key in seen_keys:
            duplicate_outcomes += 1
            continue
        seen_keys.add(key)
        predicted_signal = _safe_signal(prediction)
        actual_signal = outcome.get("actual_signal")
        realized = _safe_return(outcome)
        if (
            horizon not in HORIZONS_SECONDS
            or predicted_signal is None
            or actual_signal not in SIGNALS
            or realized is None
        ):
            unscored_outcomes += 1
            continue
        financial = prediction.get("financial_analysis")
        if not isinstance(financial, dict):
            financial = {}
        regime = str(prediction.get("regime") or financial.get("regime") or "UNKNOWN")
        valid_rows.append({
            "prediction_id": identifier,
            "horizon": horizon,
            "predicted_signal": predicted_signal,
            "actual_signal": actual_signal,
            "realized_return_pct": realized,
            "regime": regime,
        })
        labeled_predictions.add(identifier)

    by_horizon: dict[str, Any] = {}
    by_horizon_and_regime: dict[str, Any] = {}
    for horizon in HORIZONS_SECONDS:
        horizon_rows = [row for row in valid_rows if row["horizon"] == horizon]
        if horizon_rows:
            by_horizon[horizon] = _metric_bundle(horizon_rows)
        regimes = sorted({row["regime"] for row in horizon_rows})
        for regime in regimes:
            subset = [row for row in horizon_rows if row["regime"] == regime]
            by_horizon_and_regime[f"{horizon}|{regime}"] = _metric_bundle(subset)

    identified_predictions = len(predictions)
    return {
        "schema_version": SCHEMA_VERSION,
        "report_status": "ok",
        "predictions_recorded": prediction_count,
        "identified_predictions": identified_predictions,
        "legacy_unlinked_predictions": legacy_unlinked_predictions,
        "duplicate_prediction_ids": duplicate_prediction_ids,
        "predictions_with_at_least_one_valid_label": len(labeled_predictions),
        "predictions_pending_outcome": max(0, identified_predictions - len(labeled_predictions)),
        "outcomes_recorded": len(raw_outcomes) + legacy_unlinked_outcomes,
        "outcomes_scored": len(valid_rows),
        "outcomes_unscored_or_unlinked": unscored_outcomes + legacy_unlinked_outcomes,
        "duplicate_outcomes": duplicate_outcomes,
        "metrics_by_horizon": by_horizon,
        "metrics_by_horizon_and_regime": by_horizon_and_regime,
        "legacy_unlinked_outcomes": legacy_unlinked_outcomes,
        "neutral_threshold_pct_default": DEFAULT_NEUTRAL_THRESHOLD_PCT,
        "supported_horizons_seconds": HORIZONS_SECONDS,
        "automatic_retraining": False,
        "trading_enabled": False,
        "orders_created": False,
        "orders_executed": False,
        "disclaimer": (
            "Resultados descriptivos de etiquetas observadas; no son rentabilidad de "
            "cartera, probabilidad calibrada ni prueba de ventaja predictiva. El retorno "
            "alineado omite hold y no incluye costes."
        ),
    }
