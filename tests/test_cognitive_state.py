from __future__ import annotations

import math

from REASON.cognitive_state import (
    _pair_summary,
    _phase_context,
    build_cognitive_diagnostics,
    pair_agreement,
)


def _financial(
    signal: str = "buy",
    short: float = 0.9,
    medium: float = 0.8,
) -> dict:
    return {
        "signal": signal,
        "signal_strength": abs(0.4 * short + 0.6 * medium)
        if signal in {"buy", "sell"}
        else 0.0,
        "signal_strength_is_probability": False,
        "momentum_scores": {
            "short_5": short,
            "medium_20": medium,
            "combined": 0.4 * short + 0.6 * medium,
        },
        "regime": "TREND_ALCISTA" if signal == "buy" else "TREND_BAJISTA",
        "max_drawdown_pct": -1.0,
        "risk_flags": [],
    }


def _gyro(
    phase: str = "TENDENCIA",
    orientation: str = "ALCISTA",
    confidence: float = 0.7,
) -> dict:
    return {
        "fase": phase,
        "orientacion": orientation,
        "confianza": confidence,
        "omega": 0.1,
        "precesion": 0.1,
        "estabilidad": 0.8,
        "entropia": 0.2,
        "hurst_corto": 0.7,
        "hurst_largo": 0.6,
    }


def _build(
    prices: list[float],
    previous_context: dict | None = None,
    timestamp: int = 100,
    signal: str = "buy",
    gyro: dict | None = None,
):
    return build_cognitive_diagnostics(
        financial=_financial(signal=signal),
        gyro=gyro or _gyro(),
        hurst=0.71,
        cross_ratio=1.2,
        anharmonic_score=0.3,
        prices=prices,
        previous_context=previous_context or {},
        timestamp=timestamp,
    )


def test_pair_agreement_signs_contradictions_correctly() -> None:
    assert pair_agreement(1, 1, 0.8, 0.5) == 0.4
    assert pair_agreement(1, -1, 0.8, 0.5) == -0.4
    assert pair_agreement(1, 0, 0.8, 0.5) == 0.0


def test_perfect_contradiction_produces_maximum_dissonance() -> None:
    summary = _pair_summary(
        [
            {"name": "decision", "direction": 1, "confidence": 1.0, "weight": 1.0},
            {"name": "sensor", "direction": -1, "confidence": 1.0, "weight": 1.0},
        ]
    )
    assert summary["coherencia"] == -1.0
    assert summary["coherencia_direccional"] == -1.0
    assert summary["disonancia"] == 1.0
    assert summary["consenso_cualitativo"] == "BAJO"


def test_aligned_low_confidence_is_separated_from_directional_coherence() -> None:
    summary = _pair_summary(
        [
            {"name": "a", "direction": 1, "confidence": 0.3, "weight": 1.0},
            {"name": "b", "direction": 1, "confidence": 0.4, "weight": 1.0},
        ]
    )
    assert summary["coherencia"] == 0.12
    assert summary["coherencia_direccional"] == 1.0
    assert summary["disonancia"] == 0.0
    assert summary["fuerza_evidencia_pares"] == 0.12


def test_hurst_and_anharmonic_are_not_fabricated_as_directional_votes() -> None:
    prices = [100.0 * math.exp(0.001 * index) for index in range(60)]
    diagnostics = _build(prices)
    assert diagnostics["coherencia"]["decision_vs_hurst"]["valor"] is None
    assert diagnostics["coherencia"]["decision_vs_anharmonic"]["valor"] is None
    assert diagnostics["coherencia"]["decision_vs_gyro"]["aplicable"] is True


def test_markov_entropy_exposes_nats_bits_and_normalized_units() -> None:
    history = [
        "TENDENCIA", "TENDENCIA", "RANGO", "TENDENCIA", "CAOS",
        "TENDENCIA", "RANGO", "TENDENCIA", "CAOS", "TENDENCIA",
        "TENDENCIA", "RANGO", "TENDENCIA", "CAOS", "TENDENCIA",
        "TENDENCIA", "RANGO", "TENDENCIA", "CAOS", "TENDENCIA",
    ]
    result = _phase_context(
        _gyro(),
        _financial(),
        {"contexto_cognitivo": {"historial_fases": history}},
        record_observation=True,
    )
    assert 0.0 <= result["entropia_normalizada"] <= 1.0
    assert result["entropia_bits"] < 2.0
    assert result["base_entropia"].startswith("e;")
    assert result["muestras_suficientes"] is True


def test_repeated_identical_input_does_not_fake_a_new_markov_transition() -> None:
    prices = [100.0 * math.exp(0.001 * index) for index in range(60)]
    first = _build(prices, timestamp=100)
    prior = {
        "cognitive_state_version": 1,
        "cognitive_input_hash": first["cognitive_input_hash"],
        "contexto_cognitivo": first["contexto_cognitivo"],
        "memory": first["memory"],
    }
    second = _build(prices, previous_context=prior, timestamp=101)
    assert first["new_observation"] is True
    assert second["new_observation"] is False
    assert len(second["contexto_cognitivo"]["historial_fases"]) == len(
        first["contexto_cognitivo"]["historial_fases"]
    )
    assert second["contexto_cognitivo"]["transicion"] is None


def test_memory_resolves_previous_directional_forecast_against_next_price() -> None:
    first_prices = [100.0 * math.exp(0.0002 * index) for index in range(60)]
    first = _build(first_prices, timestamp=100)
    prior = {
        "cognitive_state_version": 1,
        "cognitive_input_hash": first["cognitive_input_hash"],
        "contexto_cognitivo": first["contexto_cognitivo"],
        "memory": first["memory"],
    }

    second_prices = list(first_prices)
    second_prices[-1] = first_prices[-1] * 1.01
    second = _build(second_prices, previous_context=prior, timestamp=101)

    outcomes = second["memory"]["resultados_resueltos"]
    assert len(outcomes) == 1
    assert outcomes[0]["hit"] is True
    assert second["memory"]["precision_20_ciclos"] == 1.0
    assert second["memory"]["resultados_direccionales_resueltos"] == 1
    assert "no es P&L" in second["memory"]["nota_precision"]


def test_provenance_does_not_invent_versions_or_probability_calibration() -> None:
    prices = [100.0 * math.exp(0.001 * index) for index in range(60)]
    diagnostics = _build(prices)
    assert diagnostics["sources"]["decision"]["version"] is None
    assert diagnostics["sources"]["decision"]["brier_local"] is None
    assert diagnostics["metacognicion"]["brecha_calibracion"] is None
    assert diagnostics["metacognicion"]["senal_actual_es_probabilidad"] is False
    assert len(diagnostics["cognitive_input_hash"]) == 64


def test_orchestrator_exposes_and_persists_all_cognitive_modules(tmp_path, monkeypatch) -> None:
    import json

    from REASON.orchestrator import Orchestrator
    from REASON.schemas import SensoryInput

    state_path = tmp_path / "catedralx-cognitive-state.json"
    monkeypatch.setenv("CATEDRALX_STATE_PATH", str(state_path))
    prices = [100.0 * math.exp(0.001 * index) for index in range(60)]

    state = Orchestrator().ejecutar_ciclo(
        SensoryInput(precio_historico=prices, precio_actual=prices[-1])
    )
    persisted = json.loads(state_path.read_text(encoding="utf-8"))
    cognitive_keys = {
        "coherencia",
        "metacognicion",
        "contexto_cognitivo",
        "memory",
        "contraevidencia",
        "sources",
    }

    assert cognitive_keys.issubset(state.percepcion_espacial)
    assert cognitive_keys.issubset(persisted["contexto"])
    assert cognitive_keys.issubset(
        {key for key in cognitive_keys if getattr(state, key, None) is not None}
    )
    assert persisted["contexto"]["trading_enabled"] is False
    assert persisted["contexto"]["orders_created"] is False
    assert persisted["contexto"]["orders_executed"] is False
    assert persisted["contexto"]["sources"]["decision"]["brier_local"] is None
