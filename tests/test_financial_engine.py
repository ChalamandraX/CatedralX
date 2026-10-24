from __future__ import annotations

import math

import pytest

from REASON.financial_engine import analyze_financial_market


def test_upward_momentum_is_deterministic_and_analysis_only() -> None:
    prices = [100.0 * math.exp(0.001 * index) for index in range(60)]
    first = analyze_financial_market(prices)
    second = analyze_financial_market(prices)

    assert first == second
    assert first["signal"] == "buy"
    assert first["combined_signal"] == "compra"
    assert first["regime"] == "TREND_ALCISTA"
    assert first["signal_strength_is_probability"] is False
    assert first["analysis_only"] is True
    assert first["trading_enabled"] is False
    assert first["orders_created"] is False
    assert first["orders_executed"] is False


def test_downward_momentum_is_classified_sell() -> None:
    prices = [100.0 * math.exp(-0.001 * index) for index in range(60)]
    result = analyze_financial_market(prices)

    assert result["signal"] == "sell"
    assert result["combined_signal"] == "venta"
    assert result["regime"] == "TREND_BAJISTA"
    assert result["max_drawdown_pct"] < 0


def test_flat_series_returns_hold_and_zero_strength() -> None:
    result = analyze_financial_market([1.1] * 60)

    assert result["signal"] == "hold"
    assert result["combined_signal"] == "lateral"
    assert result["signal_strength"] == 0.0
    assert result["orders_created"] is False


def test_volatility_expansion_blocks_a_directional_label() -> None:
    prices = [100.0 * math.exp(0.0005 * index) for index in range(40)]
    current = prices[-1]
    for change in [0.03, -0.025, 0.035, -0.03, 0.025, -0.035, 0.03, -0.025, 0.035, -0.03]:
        current *= math.exp(change)
        prices.append(current)

    result = analyze_financial_market(prices)

    assert result["volatility_expansion"] is True
    assert "volatility_expansion" in result["risk_flags"]
    assert result["signal"] == "hold"
    assert result["regime"] == "VOLATILIDAD_EN_EXPANSION"
    assert result["proposed_signal_before_risk_gate"] in {"buy", "sell", "hold"}


@pytest.mark.parametrize("prices", [[1.0] * 29, [1.0] * 29 + [0], [1.0] * 29 + [float("nan")], [1.0] * 29 + [float("inf")]])
def test_invalid_or_short_history_is_rejected(prices: list[float]) -> None:
    with pytest.raises(ValueError):
        analyze_financial_market(prices)


def test_bool_price_is_not_accepted_as_numeric() -> None:
    with pytest.raises(ValueError):
        analyze_financial_market([1.0] * 29 + [True])


def test_public_execute_cycle_uses_financial_layer_and_persists_outside_repo(tmp_path) -> None:
    import json

    from REASON import orchestrator
    from REASON.schemas import SensoryInput

    state_path = tmp_path / "state" / "hormonas.json"
    orchestrator._think_orchestrator.transductor.output_path = state_path
    prices = [100.0 * math.exp(0.001 * index) for index in range(60)]
    sensory = SensoryInput(precio_historico=prices, precio_actual=prices[-1])

    first = orchestrator.execute_cycle(sensory)
    second = orchestrator.execute_cycle(sensory)

    assert first.decision == second.decision == "buy"
    assert first.señal_combinada == second.señal_combinada == "compra"
    assert first.percepcion_espacial["analisis_financiero"] == second.percepcion_espacial["analisis_financiero"]
    assert first.percepcion_espacial["analisis_financiero"]["trading_enabled"] is False
    persisted = json.loads(state_path.read_text(encoding="utf-8"))
    assert persisted["contexto"]["decision_financiera"] == "buy"
    assert persisted["contexto"]["trading_enabled"] is False
    assert persisted["contexto"]["orders_executed"] is False


def test_runtime_input_refuses_to_synthesize_missing_market_prices() -> None:
    from REASON.orchestrator import Orchestrator

    with pytest.raises(ValueError, match="No hay historial de precios observado"):
        Orchestrator()._construir_sensory_input({"PERCEIVE": {}})
