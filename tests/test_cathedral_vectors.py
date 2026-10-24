from __future__ import annotations
import math
import json
from pathlib import Path
import pytest

from PERCEIVE.sensors import validate_price_history, normalize_market_payload
from PERCEIVE.percepcion import construir_sensory_input
from PERCEIVE.radar_watcher import detectar_movimiento
from MCX.OPTIMIZE.affective import actualizar_estado
from MCX.OPTIMIZE.homeostasis import parametros_homeostaticos
from MCX.OPTIMIZE.entropia import entropia
from MCX.OPTIMIZE.resico import estimar_reserva
from AEX.ejecutor import preparar_intencion, execute_order
from DSX.DEFENSE.lateral_core import rate_limited
from FEX.FEEDBACK.feedback_loop import registrar_prediccion

def test_rsx_rejects_synthetic_or_invalid_history():
    with pytest.raises(ValueError):
        validate_price_history([])
    with pytest.raises(ValueError):
        validate_price_history([100.0] * 29 + [float("nan")])

def test_rsx_builds_contract_from_observed_prices():
    prices = [100.0 + i for i in range(30)]
    sensory = construir_sensory_input({"historial_precios": prices, "precio": prices[-1], "source": "test"})
    assert sensory.precio_actual == prices[-1]
    assert len(sensory.precio_historico) == 30

def test_radar_flags_large_move():
    assert detectar_movimiento([100, 100.3])["detected"] is True
    assert detectar_movimiento([100, 100.1])["detected"] is False

def test_mcx_outputs_are_bounded_and_defensive():
    state = actualizar_estado(cortisol=0.9, dopamina=0.8, sorpresa=1.0, volatilidad=0.1)
    assert all(0 <= state[k] <= 1 for k in ("cortisol", "dopamina", "serotonina"))
    homeo = parametros_homeostaticos(state, panic=True)
    assert homeo["modo"] == "DEFENSIVO"
    assert homeo["orders_allowed"] is False

def test_entropy_and_reserve():
    assert entropia(["a", "a", "b", "b"]) == 1.0
    assert estimar_reserva(1000)["reserva_estimada"] == 20.0

def test_action_boundary_never_executes():
    intent = preparar_intencion("buy", 0.1)
    result = execute_order("buy", 0.1)
    assert intent["orders_created"] is False
    assert result["status"] == "DENIED"
    assert result["orders_executed"] is False

def test_rate_limiter_is_deterministic():
    times = []
    assert rate_limited(times, max_calls=2, window_seconds=10, now=100) is False
    assert rate_limited(times, max_calls=2, window_seconds=10, now=101) is False
    assert rate_limited(times, max_calls=2, window_seconds=10, now=102) is True

def test_feedback_is_append_only_and_outside_code(tmp_path):
    path = tmp_path / "feedback.jsonl"
    registrar_prediccion({"signal": "hold"}, path)
    row = json.loads(path.read_text().strip())
    assert row["prediction"]["signal"] == "hold"
    assert row["learning_status"] == "awaiting_labeled_outcome"

def test_bunker_refuses_to_invent_missing_prices():
    from PERCEIVE.bunker import BunkerDaemon
    with pytest.raises(ValueError):
        BunkerDaemon._construir_entrada({"PERCEIVE": {}})

def test_nexus_is_read_only_and_marks_trading_disabled():
    from bin.nexus import status
    current = status()
    assert current["trading_enabled"] is False
    assert current["orders_created"] is False
    assert current["orders_executed"] is False


def test_public_feed_adapter_keeps_only_closed_observed_candles():
    from PERCEIVE.stream_altar import build_observation_from_klines

    base = 1_800_000_000_000
    now_ms = base + 31 * 60_000
    rows = []
    for i in range(31):
        open_time = base + i * 60_000
        open_price = 100 + i
        close_price = 101 + i
        close_time = open_time + 59_999
        rows.append([open_time, str(open_price), str(close_price), str(open_price),
                     str(close_price), "1.0", close_time])
    # The final row represents a candle that has not closed yet and must be ignored.
    rows.append([now_ms, "131", "140", "130", "139", "1.0", now_ms + 59_999])

    observation = build_observation_from_klines(rows, now_ms=now_ms, symbol="BTCUSDT")
    assert len(observation["historial_precios"]) == 31
    assert observation["precio"] == 131.0
    assert observation["source"] == "binance_spot_public:BTCUSDT:1m"
    assert observation["observed_at"].endswith("+00:00")


def test_public_feed_adapter_rejects_stale_or_short_history():
    from PERCEIVE.stream_altar import build_observation_from_klines

    with pytest.raises(ValueError, match="at least 30 closed"):
        build_observation_from_klines([], now_ms=1_800_000_000_000)


def test_legacy_qubit_diagnostic_is_deterministic_and_defensive():
    from REASON.cerebellum import colapsar_qubit_determinista

    args = {
        "fuerza_tendencia": 0.8,
        "fuerza_rango": 0.2,
        "direccion": -1.0,
        "cortisol": 0.3,
    }
    assert [colapsar_qubit_determinista(**args) for _ in range(5)] == ["sell"] * 5
    assert colapsar_qubit_determinista(0.2, 0.8, -1.0, 0.3) == "buy"
    assert colapsar_qubit_determinista(0.8, 0.2, -1.0, 0.9) == "hold"


def test_financial_engine_holds_when_short_and_medium_momentum_disagree():
    import math
    from REASON.financial_engine import analyze_financial_market

    returns = [0.0] * 9 + [-0.005] * 15 + [0.01] * 5
    prices = [100.0]
    for value in returns:
        prices.append(prices[-1] * math.exp(value))

    result = analyze_financial_market(prices)
    momentum = result["momentum_scores"]
    assert momentum["short_5"] > 0.5
    assert momentum["medium_20"] < -0.5
    assert result["signal"] == "hold"
    assert result["signal_strength"] == 0.0
