"""Observable cognitive diagnostics for CatedralX.

These metrics are diagnostic heuristics, not calibrated trading probabilities.
The module is pure apart from the caller-supplied prior state so a cycle can be
replayed from the same inputs and prior context.
"""
from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from typing import Any, Mapping, Sequence

DIRECTION_MAP = {
    "buy": 1,
    "compra": 1,
    "alcista": 1,
    "long": 1,
    "sell": -1,
    "venta": -1,
    "bajista": -1,
    "short": -1,
    "hold": 0,
    "lateral": 0,
    "neutral": 0,
    "neutro": 0,
    "indefinido": 0,
}
REGIMES = ("TENDENCIA", "RANGO", "CAOS")
ALPHA = 1.0
MAX_PHASE_HISTORY = 100
MAX_DECISION_HISTORY = 50
MAX_OUTCOME_HISTORY = 40
DISSONANCE_HOLD_THRESHOLD = 0.40
COUNTEREVIDENCE_HOLD_THRESHOLD = 0.35
CHAOS_HOLD_THRESHOLD = 0.35
NORMALIZED_ENTROPY_HOLD_THRESHOLD = 0.80


def _clamp(value: Any, low: float = 0.0, high: float = 1.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return low
    if not math.isfinite(number):
        return low
    return max(low, min(high, number))


def _safe_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) else None


def _direction(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        number = float(value)
        if number > 0:
            return 1
        if number < 0:
            return -1
        return 0
    return DIRECTION_MAP.get(str(value).strip().lower(), 0)


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
        default=str,
    )


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def pair_agreement(
    direction_a: Any,
    direction_b: Any,
    confidence_a: float,
    confidence_b: float,
) -> float:
    """Signed confidence product; neutral or missing direction contributes zero."""
    a = _direction(direction_a)
    b = _direction(direction_b)
    ca = _clamp(confidence_a)
    cb = _clamp(confidence_b)
    if not a or not b:
        return 0.0
    return ca * cb if a == b else -(ca * cb)


def _pair_summary(signals: list[dict[str, Any]]) -> dict[str, Any]:
    directional = [
        signal
        for signal in signals
        if signal["direction"] != 0 and signal["confidence"] > 0.0
    ]
    pairs: list[dict[str, Any]] = []
    raw_numerator = 0.0
    raw_denominator = 0.0
    alignment_numerator = 0.0
    alignment_denominator = 0.0
    evidence_numerator = 0.0
    evidence_denominator = 0.0

    for index, left in enumerate(directional):
        for right in directional[index + 1 :]:
            base_weight = _clamp(left["weight"]) * _clamp(right["weight"])
            signed_score = pair_agreement(
                left["direction"],
                right["direction"],
                left["confidence"],
                right["confidence"],
            )
            pair_confidence = left["confidence"] * right["confidence"]
            if base_weight <= 0.0:
                continue
            pairs.append(
                {
                    "a": left["name"],
                    "b": right["name"],
                    "agreement": round(signed_score, 6),
                    "weight": round(base_weight, 6),
                    "same_direction": left["direction"] == right["direction"],
                }
            )
            raw_numerator += base_weight * signed_score
            raw_denominator += base_weight
            alignment_numerator += base_weight * pair_confidence * (
                1.0 if left["direction"] == right["direction"] else -1.0
            )
            alignment_denominator += base_weight * pair_confidence
            evidence_numerator += base_weight * pair_confidence
            evidence_denominator += base_weight

    raw_coherence = (
        raw_numerator / raw_denominator if raw_denominator > 0.0 else None
    )
    # Alignment isolates directional agreement from confidence magnitude.
    # Confidence magnitude is reported separately as evidence_strength.
    alignment = (
        alignment_numerator / alignment_denominator
        if alignment_denominator > 0.0
        else None
    )
    evidence_strength = (
        evidence_numerator / evidence_denominator
        if evidence_denominator > 0.0
        else None
    )
    dissonance = (1.0 - alignment) / 2.0 if alignment is not None else None
    if alignment is None:
        qualitative = "NO_EVALUABLE"
    elif alignment > 0.75:
        qualitative = "ALTO"
    elif alignment > 0.45:
        qualitative = "MEDIO"
    else:
        qualitative = "BAJO"

    return {
        "coherencia": round(raw_coherence, 6) if raw_coherence is not None else None,
        "coherencia_direccional": round(alignment, 6) if alignment is not None else None,
        "disonancia": round(dissonance, 6) if dissonance is not None else None,
        "fuerza_evidencia_pares": round(evidence_strength, 6)
        if evidence_strength is not None
        else None,
        "consenso_cualitativo": qualitative,
        "pares_evaluados": pairs,
        "senales_direccionales_evaluadas": [signal["name"] for signal in directional],
        "n_pares": len(pairs),
        "formula_version": "signed-pair-v1",
        "notes": [
            "La coherencia direccional se normaliza por la masa de confianza de los pares.",
            "La fuerza de evidencia se informa separadamente para no confundir baja confianza con contradiccion.",
            "Las señales comparten datos de precios; su independencia estadistica no esta demostrada.",
        ],
    }


def _pair_field(
    decision: Any,
    direction: Any,
    decision_confidence: float,
    other_confidence: float,
    reason_if_unavailable: str | None = None,
) -> dict[str, Any]:
    decision_direction = _direction(decision)
    other_direction = _direction(direction)
    applicable = decision_direction != 0 and other_direction != 0
    return {
        "valor": round(
            pair_agreement(
                decision_direction,
                other_direction,
                decision_confidence,
                other_confidence,
            ),
            6,
        )
        if applicable
        else None,
        "aplicable": applicable,
        "motivo_no_evaluable": None
        if applicable
        else (
            reason_if_unavailable
            or "La decision o la senal no tiene direccion activa."
        ),
    }


def _counterevidence(
    decision: Any, signals: list[dict[str, Any]]
) -> dict[str, Any]:
    decision_direction = _direction(decision)
    if decision_direction == 0:
        return {
            "senales_opuestas": [],
            "fuerza_contra": None,
            "umbral_abortar": COUNTEREVIDENCE_HOLD_THRESHOLD,
            "decision_sobrevive": None,
            "evaluacion": "NO_APLICA_A_DECISION_NEUTRAL",
        }

    supporting_mass = 0.0
    opposing_mass = 0.0
    active_mass = 0.0
    opposing: list[dict[str, Any]] = []
    for signal in signals:
        direction = signal["direction"]
        confidence = signal["confidence"]
        weight = signal["weight"]
        if direction == 0 or confidence <= 0.0:
            continue
        mass = weight * confidence
        active_mass += mass
        if direction == -decision_direction:
            opposing_mass += mass
            opposing.append(
                {
                    "modulo": signal["name"],
                    "dir": "BUY" if direction > 0 else "SELL",
                    "conf": round(confidence, 6),
                    "peso": round(weight, 6),
                    "masa_contra": round(mass, 6),
                }
            )
        else:
            supporting_mass += mass

    force = opposing_mass / active_mass if active_mass > 0.0 else None
    survives = (
        force <= COUNTEREVIDENCE_HOLD_THRESHOLD if force is not None else None
    )
    return {
        "senales_opuestas": opposing,
        "masa_a_favor": round(supporting_mass, 6),
        "masa_en_contra": round(opposing_mass, 6),
        "fuerza_contra": round(force, 6) if force is not None else None,
        "umbral_abortar": COUNTEREVIDENCE_HOLD_THRESHOLD,
        "decision_sobrevive": survives,
        "evaluacion": "EVALUADA" if force is not None else "EVIDENCIA_INSUFICIENTE",
        "formula": "masa_opuesta / masa_direccional_total",
    }


def _phase_context(
    gyro: Mapping[str, Any],
    financial: Mapping[str, Any],
    previous_context: Mapping[str, Any],
    record_observation: bool = True,
) -> dict[str, Any]:
    previous_cognitive = previous_context.get("contexto_cognitivo", {})
    if not isinstance(previous_cognitive, Mapping):
        previous_cognitive = {}
    prior_history = previous_cognitive.get("historial_fases", [])
    if not isinstance(prior_history, list):
        prior_history = []
    prior_history = [str(item) for item in prior_history if str(item) in REGIMES]
    current_phase = str(gyro.get("fase", "CAOS")).upper()
    if current_phase not in REGIMES:
        current_phase = "CAOS"
    current_financial_regime = str(financial.get("regime", "INDEFINIDO"))

    history_before = prior_history[-MAX_PHASE_HISTORY:]
    previous_phase = history_before[-1] if history_before else None
    transition = (
        f"{previous_phase}→{current_phase}"
        if previous_phase and record_observation
        else None
    )
    history = (
        (history_before + [current_phase])[-MAX_PHASE_HISTORY:]
        if record_observation
        else history_before
    )

    def count_transitions(items: Sequence[str]) -> Counter[tuple[str, str]]:
        counts: Counter[tuple[str, str]] = Counter()
        for source, target in zip(items, items[1:]):
            if source in REGIMES and target in REGIMES:
                counts[(source, target)] += 1
        return counts

    historical_counts = count_transitions(history_before)
    updated_counts = count_transitions(history)
    matrix: dict[str, dict[str, float]] = {}
    row_counts: dict[str, int] = {}
    for source in REGIMES:
        row_total = sum(updated_counts[(source, target)] for target in REGIMES)
        row_counts[source] = row_total
        denominator = row_total + ALPHA * len(REGIMES)
        matrix[source] = {
            target: (updated_counts[(source, target)] + ALPHA) / denominator
            for target in REGIMES
        }

    # Estimate whether the most recent transition was surprising using only
    # observations available before that transition, to avoid self-inclusion.
    anomalies = list(previous_cognitive.get("anomalias", []))
    historical_row_total = (
        sum(historical_counts[(previous_phase, target)] for target in REGIMES)
        if previous_phase
        else 0
    )
    if record_observation and previous_phase and historical_row_total >= 10:
        expected = (
            historical_counts[(previous_phase, current_phase)] + ALPHA
        ) / (historical_row_total + ALPHA * len(REGIMES))
        standard_deviation = math.sqrt(max(expected * (1.0 - expected), 1e-12))
        z_score = (1.0 - expected) / standard_deviation
        if expected < 0.05 and z_score > 2.0:
            anomalies.append(
                {
                    "transicion": transition,
                    "probabilidad_esperada": round(expected, 6),
                    "z_score_evento": round(z_score, 6),
                    "muestras_previas_fila": historical_row_total,
                }
            )
    anomalies = anomalies[-10:]

    updated_row_count = sum(updated_counts[(current_phase, target)] for target in REGIMES)
    alpha_denominator = updated_row_count + ALPHA * len(REGIMES)
    transition_row = {
        target: (updated_counts[(current_phase, target)] + ALPHA) / alpha_denominator
        for target in REGIMES
    }
    entropy_nats = -sum(
        probability * math.log(probability)
        for probability in transition_row.values()
        if probability > 0.0
    )
    entropy_bits = entropy_nats / math.log(2.0)
    entropy_normalized = entropy_nats / math.log(len(REGIMES))
    time_in_regime = 0
    for phase in reversed(history):
        if phase != current_phase:
            break
        time_in_regime += 1
    sample_sufficient = updated_row_count >= 5
    uncertain = (
        sample_sufficient
        and entropy_normalized > NORMALIZED_ENTROPY_HOLD_THRESHOLD
    )

    return {
        "fase_actual": current_phase,
        "fase_anterior": previous_phase,
        "transicion": transition,
        "regimen_financiero": current_financial_regime,
        "tiempo_en_regimen_ciclos": time_in_regime,
        "P_salida": round(1.0 - transition_row[current_phase], 6),
        "matriz_transicion": {
            row: {col: round(value, 6) for col, value in values.items()}
            for row, values in matrix.items()
        },
        "entropia_nats": round(entropy_nats, 6),
        "entropia_bits": round(entropy_bits, 6),
        "entropia_normalizada": round(entropy_normalized, 6),
        "muestras_transicion_fase_actual": updated_row_count,
        "muestras_suficientes": sample_sufficient,
        "fase_mal_definida": uncertain,
        "anomalias": anomalies,
        "historial_fases": history,
        "suavizado_laplace_alpha": ALPHA,
        "base_entropia": "e; entropia_bits se convierte dividiendo por ln(2)",
        "nota_umbral": (
            "El umbral se aplica a entropia normalizada; 0.69 nats no equivale "
            "a dos bits, y dos bits son imposibles con solo tres regímenes."
        ),
    }


def _summarize_memory(
    decisions: list[dict[str, Any]],
    outcomes: list[dict[str, Any]],
    pending: dict[str, Any] | None,
    latest_price: float,
    timestamp: int,
    drawdown_pct: float | None,
) -> dict[str, Any]:
    decisions = decisions[-MAX_DECISION_HISTORY:]
    outcomes = outcomes[-MAX_OUTCOME_HISTORY:]
    last_20_decisions = decisions[-20:]
    last_20_outcomes = outcomes[-20:]
    evaluable = [item for item in last_20_outcomes if isinstance(item.get("hit"), bool)]
    accuracy = (
        sum(1 for item in evaluable if item["hit"]) / len(evaluable)
        if evaluable
        else None
    )
    directional_decisions = [
        item for item in last_20_decisions if _direction(item.get("decision")) != 0
    ]
    buys = sum(1 for item in directional_decisions if _direction(item["decision"]) > 0)
    sells = sum(1 for item in directional_decisions if _direction(item["decision"]) < 0)
    directional_bias = (
        (buys - sells) / (buys + sells) if (buys + sells) else None
    )
    counts = Counter(
        str(item.get("decision", "hold")).lower()
        for item in last_20_decisions
        if str(item.get("decision", "hold")).lower() in {"buy", "sell", "hold"}
    )
    count_total = sum(counts.values())
    entropy_decisions = (
        -sum((count / count_total) * math.log(count / count_total) for count in counts.values())
        if count_total
        else None
    )
    max_entropy = math.log(3.0)
    normalized_decision_entropy = (
        entropy_decisions / max_entropy if entropy_decisions is not None else None
    )

    streak_hits = 0
    streak_errors = 0
    if evaluable:
        latest_hit = evaluable[-1]["hit"]
        for outcome in reversed(evaluable):
            if outcome["hit"] != latest_hit:
                break
            if latest_hit:
                streak_hits += 1
            else:
                streak_errors += 1

    return {
        "ultimas_decisiones": [
            str(item.get("decision", "hold")).upper() for item in last_20_decisions
        ],
        "precision_20_ciclos": round(accuracy, 6) if accuracy is not None else None,
        "resultados_direccionales_resueltos": len(evaluable),
        "rachas": {
            "racha_aciertos": streak_hits,
            "racha_errores": streak_errors,
        },
        "peor_drawdown_observado_pct": (
            round(float(drawdown_pct), 6) if drawdown_pct is not None else None
        ),
        "sesgo_direccional": (
            round(directional_bias, 6) if directional_bias is not None else None
        ),
        "sesgo_muestra_direccional": buys + sells,
        "entropia_decisiones_nats": (
            round(entropy_decisions, 6) if entropy_decisions is not None else None
        ),
        "entropia_decisiones_normalizada": (
            round(normalized_decision_entropy, 6)
            if normalized_decision_entropy is not None
            else None
        ),
        "memoria_decisiones": decisions,
        "resultados_resueltos": outcomes,
        "prediccion_pendiente": pending,
        "ultimo_precio_observado": latest_price,
        "ultimo_timestamp": timestamp,
        "nota_precision": (
            "La precision compara direccion pronosticada con el cambio entre "
            "observaciones de entrada; no es P&L ni demuestra rentabilidad."
        ),
    }


def _build_memory(
    previous_context: Mapping[str, Any],
    decision: str,
    latest_price: float,
    timestamp: int,
    drawdown_pct: float | None,
) -> dict[str, Any]:
    previous_memory = previous_context.get("memory", {})
    if not isinstance(previous_memory, Mapping):
        previous_memory = {}
    decisions = list(previous_memory.get("memoria_decisiones", []))
    outcomes = list(previous_memory.get("resultados_resueltos", []))
    pending_value = previous_memory.get("prediccion_pendiente")
    pending = dict(pending_value) if isinstance(pending_value, Mapping) else None
    prior_price_value = previous_memory.get("ultimo_precio_observado")
    try:
        prior_price = float(prior_price_value) if prior_price_value is not None else None
    except (TypeError, ValueError, OverflowError):
        prior_price = None
    if prior_price is not None and not math.isfinite(prior_price):
        prior_price = None

    price_changed = prior_price is None or not math.isclose(
        latest_price, prior_price, rel_tol=1e-12, abs_tol=1e-12
    )
    if price_changed and prior_price is not None and pending:
        pending_price = _safe_float(pending.get("precio"))
        predicted_direction = _direction(pending.get("decision"))
        if pending_price is not None and latest_price != pending_price and predicted_direction != 0:
            realized_direction = 1 if latest_price > pending_price else -1
            outcomes.append(
                {
                    "timestamp_pronostico": pending.get("timestamp"),
                    "precio_inicial": pending_price,
                    "precio_final": latest_price,
                    "direccion_pronosticada": predicted_direction,
                    "direccion_realizada": realized_direction,
                    "hit": predicted_direction == realized_direction,
                    "retorno_observado_pct": round(
                        (latest_price / pending_price - 1.0) * 100.0, 8
                    ),
                }
            )
        pending = None

    normalized_decision = str(decision).lower()
    append_decision = (
        not decisions
        or price_changed
        or str(decisions[-1].get("decision", "")).lower() != normalized_decision
    )
    if append_decision:
        decisions.append(
            {
                "timestamp": timestamp,
                "decision": normalized_decision,
                "precio": latest_price,
                "nueva_observacion": price_changed,
            }
        )

    if pending is None and _direction(normalized_decision) != 0:
        pending = {
            "timestamp": timestamp,
            "decision": normalized_decision,
            "precio": latest_price,
        }

    return _summarize_memory(
        decisions, outcomes, pending, latest_price, timestamp, drawdown_pct
    )


def reconcile_final_decision(
    memory: dict[str, Any],
    final_decision: str,
    candidate_decision: str,
    latest_price: float,
    timestamp: int,
) -> dict[str, Any]:
    """Record the actually retained label and cancel only a same-cycle candidate."""
    final_value = str(final_decision).lower()
    candidate_value = str(candidate_decision).lower()
    decisions = list(memory.get("memoria_decisiones", []))
    if decisions and decisions[-1].get("timestamp") == timestamp:
        decisions[-1] = {**decisions[-1], "decision": final_value}
    elif not decisions or str(decisions[-1].get("decision", "")).lower() != final_value:
        decisions.append(
            {
                "timestamp": timestamp,
                "decision": final_value,
                "precio": latest_price,
                "nueva_observacion": False,
                "motivo": "resultado_final_del_gate_cognitivo",
            }
        )

    pending_value = memory.get("prediccion_pendiente")
    pending = dict(pending_value) if isinstance(pending_value, Mapping) else None
    if pending and pending.get("timestamp") == timestamp and final_value != candidate_value:
        if _direction(final_value) == 0:
            pending = None
        else:
            pending["decision"] = final_value

    return _summarize_memory(
        decisions,
        list(memory.get("resultados_resueltos", [])),
        pending,
        latest_price,
        timestamp,
        memory.get("peor_drawdown_observado_pct"),
    )


def _learning_status(outcomes: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    evaluable = [item for item in outcomes if isinstance(item.get("hit"), bool)][-20:]
    if len(evaluable) < 20:
        return {
            "estado": "EVIDENCIA_INSUFICIENTE",
            "error_reciente": None,
            "deriva_error": None,
            "muestras": len(evaluable),
        }
    older = evaluable[:10]
    recent = evaluable[10:]
    old_error = 1.0 - sum(bool(item["hit"]) for item in older) / len(older)
    recent_error = 1.0 - sum(bool(item["hit"]) for item in recent) / len(recent)
    delta = recent_error - old_error
    if delta < -0.05:
        status = "MEJORANDO"
    elif delta > 0.05:
        status = "DEGRADANDO"
    else:
        status = "ESTABLE"
    return {
        "estado": status,
        "error_reciente": round(recent_error, 6),
        "deriva_error": round(delta, 6),
        "muestras": len(evaluable),
    }


def build_cognitive_diagnostics(
    *,
    financial: Mapping[str, Any],
    gyro: Mapping[str, Any],
    hurst: float,
    cross_ratio: float,
    anharmonic_score: float,
    prices: Sequence[float],
    previous_context: Mapping[str, Any] | None = None,
    timestamp: int | None = None,
) -> dict[str, Any]:
    """Build coherent, traceable diagnostics without inventing probabilities."""
    previous = previous_context if isinstance(previous_context, Mapping) else {}
    cycle_timestamp = int(timestamp or 0)
    checked_prices = [float(price) for price in prices]
    candidate = str(financial.get("signal", "hold")).lower()
    momentum = financial.get("momentum_scores", {})
    if not isinstance(momentum, Mapping):
        momentum = {}

    short_score = _clamp(abs(float(momentum.get("short_5", 0.0))), 0.0, 1.0)
    medium_score = _clamp(abs(float(momentum.get("medium_20", 0.0))), 0.0, 1.0)
    decision_strength = _clamp(financial.get("signal_strength", 0.0))
    gyro_confidence = _clamp(gyro.get("confianza", 0.0))
    gyro_direction = _direction(gyro.get("orientacion", "neutro"))
    decision_direction = _direction(candidate)
    short_direction = _direction(momentum.get("short_5", 0.0))
    medium_direction = _direction(momentum.get("medium_20", 0.0))

    evidence_signals = [
        {
            "name": "decision_financiera",
            "direction": decision_direction,
            "confidence": decision_strength,
            "weight": 1.0,
        },
        {
            "name": "momentum_corto",
            "direction": short_direction,
            "confidence": short_score,
            "weight": 1.0,
        },
        {
            "name": "momentum_medio",
            "direction": medium_direction,
            "confidence": medium_score,
            "weight": 1.0,
        },
        {
            "name": "giroscopio",
            "direction": gyro_direction,
            "confidence": gyro_confidence,
            "weight": 1.0,
        },
    ]
    coherence = _pair_summary(evidence_signals)
    coherence["decision_vs_gyro"] = _pair_field(
        candidate,
        gyro_direction,
        decision_strength,
        gyro_confidence,
        "El giroscopio no aporta una orientacion direccional.",
    )
    # Hurst estimates persistence/regime, not up/down direction.
    coherence["decision_vs_hurst"] = {
        "valor": None,
        "aplicable": False,
        "motivo_no_evaluable": "Hurst estima persistencia; no determina direccion.",
        "hurst_observado": round(float(hurst), 6),
    }
    # The current anharmonic score describes structure, not a directional vote.
    coherence["decision_vs_anharmonic"] = {
        "valor": None,
        "aplicable": False,
        "motivo_no_evaluable": "El score anarmonico es estructural, no una direccion BUY/SELL.",
        "score_anarmonico": round(float(anharmonic_score), 6),
        "cross_ratio": round(float(cross_ratio), 6),
    }

    counter = _counterevidence(
        candidate,
        [signal for signal in evidence_signals if signal["name"] != "decision_financiera"],
    )
    previous_cognitive = previous.get("contexto_cognitivo", {})
    if not isinstance(previous_cognitive, Mapping):
        previous_cognitive = {}
    gyro_signature = {
        key: gyro.get(key)
        for key in (
            "fase", "orientacion", "omega", "precesion", "estabilidad",
            "entropia", "confianza", "hurst_corto", "hurst_largo",
        )
    }
    cognitive_input_hash = _sha256(
        {
            "prices": checked_prices,
            "financial": dict(financial),
            "gyro": gyro_signature,
            "hurst": float(hurst),
            "cross_ratio": float(cross_ratio),
            "anharmonic_score": float(anharmonic_score),
        }
    )
    record_observation = previous.get("cognitive_input_hash") != cognitive_input_hash
    context = _phase_context(
        gyro, financial, previous, record_observation=record_observation
    )
    context["nueva_observacion"] = record_observation
    max_drawdown = financial.get("max_drawdown_pct")
    try:
        drawdown_pct = float(max_drawdown) if max_drawdown is not None else None
    except (TypeError, ValueError, OverflowError):
        drawdown_pct = None
    memory = _build_memory(
        previous,
        candidate,
        checked_prices[-1],
        cycle_timestamp,
        drawdown_pct,
    )

    expected_source_count = 4
    available_source_count = sum(
        [
            isinstance(financial, Mapping) and bool(financial),
            isinstance(gyro, Mapping) and bool(gyro),
            math.isfinite(float(hurst)),
            math.isfinite(float(cross_ratio)) and math.isfinite(float(anharmonic_score)),
        ]
    )
    coverage = available_source_count / expected_source_count
    pair_evidence = coherence.get("fuerza_evidencia_pares")
    dissonance = coherence.get("disonancia")
    active_confidences = [
        signal["confidence"]
        for signal in evidence_signals
        if signal["direction"] != 0 and signal["confidence"] > 0.0
    ]
    mean_signal_confidence = (
        sum(active_confidences) / len(active_confidences)
        if active_confidences
        else 0.0
    )
    uncertainty_components: list[tuple[float, float]] = [
        (0.25, 1.0 - coverage),
        (0.25, 1.0 - mean_signal_confidence),
    ]
    if dissonance is not None:
        uncertainty_components.append((0.50, dissonance))
    uncertainty_weight = sum(weight for weight, _ in uncertainty_components)
    uncertainty_proxy = (
        sum(weight * value for weight, value in uncertainty_components) / uncertainty_weight
        if uncertainty_weight
        else None
    )

    outcomes = memory.get("resultados_resueltos", [])
    resolved = [item for item in outcomes if isinstance(item.get("hit"), bool)]
    historical_accuracy = (
        sum(1 for item in resolved if item["hit"]) / len(resolved)
        if resolved
        else None
    )
    # Only use historical accuracy as a risk term after a minimum sample.
    chaos_terms: list[tuple[float, float]] = []
    if dissonance is not None:
        chaos_terms.append((0.50, dissonance))
    if uncertainty_proxy is not None:
        chaos_terms.append((0.30, uncertainty_proxy))
    if len(resolved) >= 10 and historical_accuracy is not None:
        chaos_terms.append((0.20, 1.0 - historical_accuracy))
    chaos_weight = sum(weight for weight, _ in chaos_terms)
    chaos_risk = (
        sum(weight * value for weight, value in chaos_terms) / chaos_weight
        if chaos_weight
        else None
    )
    metacognition = {
        "incertidumbre_total": None,
        "incertidumbre_epistemica": None,
        "incertidumbre_aleatoria": None,
        "motivo_incertidumbre_no_calibrada": (
            "El motor no expone distribuciones predictivas ni sigma epistemica/aleatoria calibradas."
        ),
        "incertidumbre_proxy": round(uncertainty_proxy, 6)
        if uncertainty_proxy is not None
        else None,
        "disonancia": dissonance,
        "confianza_historica": round(historical_accuracy, 6)
        if historical_accuracy is not None
        else None,
        "muestras_historicas_resueltas": len(resolved),
        "brecha_calibracion": None,
        "brier_local": None,
        "calibracion_estado": "NO_EVALUABLE_SIN_PROBABILIDADES_CALIBRADAS",
        "senal_actual_es_probabilidad": False,
        "aprendizaje": _learning_status(outcomes),
        "capacidad_adaptativa": None,
        "fatiga": None,
        "riesgo_caos": round(chaos_risk, 6) if chaos_risk is not None else None,
        "riesgo_caos_calibrado": False,
        "umbral_riesgo_caos": CHAOS_HOLD_THRESHOLD,
        "cobertura_fuentes": round(coverage, 6),
        "confianza_media_senales_heuristica": round(mean_signal_confidence, 6),
        "nota": (
            "No se usa signal_strength como probabilidad. Los umbrales de riesgo "
            "son guardas heuristicas, no umbrales estadisticamente calibrados."
        ),
    }

    prices_payload = {"prices": checked_prices}
    input_hash = _sha256(prices_payload)
    sources = {
        "financial_momentum": {
            "modulo": "elite.REASON.financial_engine.analyze_financial_market",
            "version": None,
            "version_status": "NO_DECLARADA",
            "timestamp": cycle_timestamp,
            "input_hash": input_hash,
            "output": {
                "signal": financial.get("signal"),
                "signal_strength": financial.get("signal_strength"),
                "signal_strength_is_probability": financial.get("signal_strength_is_probability", False),
                "momentum_scores": dict(momentum),
            },
            "confidence_semantics": "fuerza heuristica; no probabilidad calibrada",
            "brier_local": None,
        },
        "hurst": {
            "modulo": "elite.REASON.hurst_analyzer.hurst_exponent",
            "version": None,
            "version_status": "NO_DECLARADA",
            "timestamp": cycle_timestamp,
            "input_hash": input_hash,
            "output": round(float(hurst), 6),
            "interpretation": "persistencia/regimen; no direccion",
            "brier_local": None,
        },
        "gyroscope": {
            "modulo": "elite.REASON.gyroscope.gyro_state",
            "version": None,
            "version_status": "NO_DECLARADA",
            "timestamp": cycle_timestamp,
            "input_hash": input_hash,
            "output": {
                "fase": gyro.get("fase"),
                "orientacion": gyro.get("orientacion"),
                "confianza": gyro.get("confianza"),
                "omega": gyro.get("omega"),
                "estabilidad": gyro.get("estabilidad"),
            },
            "confidence_semantics": "heuristica interna; no probabilidad calibrada",
            "brier_local": None,
        },
        "anharmonic": {
            "modulo": "elite.REASON.anharmonic.analyze",
            "version": None,
            "version_status": "NO_DECLARADA",
            "timestamp": cycle_timestamp,
            "input_hash": input_hash,
            "output": {
                "cross_ratio": round(float(cross_ratio), 6),
                "score": round(float(anharmonic_score), 6),
            },
            "interpretation": "rasgo estructural; no voto direccional",
            "brier_local": None,
        },
        "decision": {
            "modulo": "elite.REASON.orchestrator.Orchestrator.ejecutar_ciclo",
            "version": None,
            "version_status": "NO_DECLARADA",
            "timestamp": cycle_timestamp,
            "input_hash": input_hash,
            "inputs_used": ["financial_momentum", "short_5", "medium_20", "gyroscope"],
            "rules": [
                "BUY requiere score corto y medio >= 0.5 y ausencia de bloqueos de riesgo",
                "SELL requiere score corto y medio <= -0.5 y ausencia de bloqueos de riesgo",
                "disonancia > 0.40 bloquea salida direccional",
                "fuerza_contra > 0.35 bloquea salida direccional",
                "riesgo_caos > 0.35 bloquea salida direccional",
            ],
            "candidate_decision": candidate,
            "confidence": decision_strength,
            "confidence_semantics": "signal_strength heuristico; no probabilidad",
            "brier_local": None,
        },
    }

    return {
        "coherencia": coherence,
        "contraevidencia": counter,
        "metacognicion": metacognition,
        "contexto_cognitivo": context,
        "memory": memory,
        "sources": sources,
        "candidate_decision": candidate,
        "gate_reasons": [],
        "cognitive_state_version": 1,
        "cognitive_input_hash": cognitive_input_hash,
        "new_observation": record_observation,
    }


def apply_final_decision(
    diagnostics: dict[str, Any],
    final_decision: str,
    latest_price: float,
    timestamp: int,
) -> None:
    """Keep the logged and pending prediction aligned with the final analysis label."""
    candidate = str(diagnostics.get("candidate_decision", "hold")).lower()
    final_value = str(final_decision).lower()
    diagnostics["final_decision"] = final_value
    diagnostics["sources"]["decision"]["final_decision"] = final_value
    diagnostics["sources"]["decision"]["blocked_by"] = list(diagnostics.get("gate_reasons", []))
    diagnostics["memory"] = reconcile_final_decision(
        diagnostics["memory"],
        final_value,
        candidate,
        latest_price,
        timestamp,
    )
    outcomes = diagnostics["memory"].get("resultados_resueltos", [])
    resolved = [item for item in outcomes if isinstance(item.get("hit"), bool)]
    historical_accuracy = (
        sum(1 for item in resolved if item["hit"]) / len(resolved)
        if resolved
        else None
    )
    diagnostics["metacognicion"]["confianza_historica"] = (
        round(historical_accuracy, 6) if historical_accuracy is not None else None
    )
    diagnostics["metacognicion"]["muestras_historicas_resueltas"] = len(resolved)
    diagnostics["metacognicion"]["aprendizaje"] = _learning_status(outcomes)
