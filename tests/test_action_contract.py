from __future__ import annotations

import math

import pytest
from AEX.DECISION.operador import ensamblar_operacion
from AEX.DECISION.riesgo import memoria, verificar_seguridad
from AEX.ejecutor import preparar_intencion
from contracts.actions import normalizar_senal
from FEX.FEEDBACK.feedback_loop import _safe_signal


@pytest.mark.parametrize(
    ("raw", "canonical"),
    [
        ("buy", "buy"),
        ("BUY", "buy"),
        ("COMPRAR", "buy"),
        ("COMPRA", "buy"),
        ("ENTRAR_LARGO", "buy"),
        ("sell", "sell"),
        ("SELL", "sell"),
        ("VENDER", "sell"),
        ("VENTA", "sell"),
        ("ENTRAR_CORTO", "sell"),
        ("hold", "hold"),
        ("HOLD", "hold"),
        ("ESPERAR", "hold"),
        ("LATERAL", "hold"),
        ("wait", "hold"),
    ],
)
def test_action_aliases_use_one_canonical_signal(raw: str, canonical: str) -> None:
    assert normalizar_senal(raw) == canonical


@pytest.mark.parametrize("raw", [None, 3, True])
def test_non_text_action_is_rejected(raw: object) -> None:
    with pytest.raises(TypeError):
        normalizar_senal(raw)


@pytest.mark.parametrize("raw", ["", "LONG?", "execute"])
def test_unknown_action_is_rejected_not_guessed(raw: str) -> None:
    with pytest.raises(ValueError):
        normalizar_senal(raw)


@pytest.mark.parametrize(
    ("raw", "canonical", "expected_status"),
    [
        ("COMPRAR", "buy", "REVIEW_REQUIRED"),
        ("BUY", "buy", "REVIEW_REQUIRED"),
        ("ENTRAR_CORTO", "sell", "REVIEW_REQUIRED"),
        ("ESPERAR", "hold", "BLOCKED_REVIEW_ONLY"),
    ],
)
def test_action_boundary_normalizes_without_enabling_execution(
    raw: str, canonical: str, expected_status: str
) -> None:
    result = preparar_intencion(raw, 0.2)

    assert result["decision"] == canonical
    assert result["status"] == expected_status
    assert result["trading_enabled"] is False
    assert result["orders_created"] is False
    assert result["orders_executed"] is False


def test_action_boundary_fails_closed_on_panic_or_risk_flags() -> None:
    for result in (
        preparar_intencion("buy", 0.1, panic=True),
        preparar_intencion("VENDER", 0.1, risk_flags=["volatility_expansion"]),
    ):
        assert result["status"] == "BLOCKED_REVIEW_ONLY"
        assert result["trading_enabled"] is False
        assert result["orders_executed"] is False


@pytest.mark.parametrize("size", [math.nan, math.inf, -math.inf, -0.01, "not-a-number"])
def test_action_boundary_rejects_invalid_size(size: object) -> None:
    with pytest.raises(ValueError, match="size"):
        preparar_intencion("buy", size)  # type: ignore[arg-type]


def test_action_boundary_rejects_boolean_size() -> None:
    with pytest.raises(TypeError, match="size"):
        preparar_intencion("buy", True)


@pytest.mark.parametrize(
    "action",
    ["buy", "BUY", "COMPRAR", "ENTRAR_LARGO", "sell", "VENDER", "ENTRAR_CORTO"],
)
def test_risk_confidence_floor_covers_all_directional_aliases(action: str) -> None:
    allowed, reason = verificar_seguridad(action, 0.39, {})

    assert allowed is False
    assert reason.startswith("Confianza baja")


@pytest.mark.parametrize(
    "confidence", [math.nan, math.inf, -math.inf, -0.01, 1.01, True, "bad"]
)
def test_risk_gate_rejects_invalid_confidence(confidence: object) -> None:
    allowed, reason = verificar_seguridad("COMPRAR", confidence, {})  # type: ignore[arg-type]

    assert allowed is False
    assert reason == "Confianza inválida"


@pytest.mark.parametrize(
    ("metrics", "reason"),
    [
        ({"entropia": math.nan}, "Entropía inválida"),
        ({"entropia": math.inf}, "Entropía inválida"),
        ({"entropia": 1.01}, "Entropía inválida"),
        ({"entropia": "bad"}, "Entropía inválida"),
        ({"volatilidad": math.nan}, "Volatilidad inválida"),
        ({"volatilidad": math.inf}, "Volatilidad inválida"),
        ({"volatilidad": -0.01}, "Volatilidad inválida"),
        (None, "Datos de riesgo inválidos"),
    ],
)
def test_risk_gate_fails_closed_on_invalid_market_metrics(
    metrics: object, reason: str
) -> None:
    allowed, actual_reason = verificar_seguridad(
        "ENTRAR_LARGO",
        0.9,
        metrics,  # type: ignore[arg-type]
    )

    assert allowed is False
    assert actual_reason == reason


def test_risk_gate_applies_volatility_limit_to_english_and_spanish_actions() -> None:
    for action in ("BUY", "COMPRAR", "ENTRAR_LARGO", "SELL", "VENDER", "ENTRAR_CORTO"):
        allowed, reason = verificar_seguridad(action, 0.9, {"volatilidad": 0.051})
        assert allowed is False
        assert reason == "Volatilidad extrema"


def test_risk_gate_allows_valid_directional_intent_for_review() -> None:
    assert verificar_seguridad(
        "COMPRAR", 0.7, {"entropia": 0.2, "volatilidad": 0.01}
    ) == (
        True,
        "OK",
    )


def test_risk_gate_fails_closed_when_internal_daily_result_is_non_finite(
    monkeypatch,
) -> None:
    monkeypatch.setitem(memoria.estadisticas, "ganancia_acumulada", math.nan)

    assert verificar_seguridad("buy", 0.9, {}) == (
        False,
        "Estadísticas de riesgo inválidas",
    )


def test_operator_never_claims_live_execution_is_authorized() -> None:
    result = ensamblar_operacion(
        score_direccional=0.8,
        confianza=0.9,
        fase="TENDENCIA",
        size_kelly=0.15,
        size_kelly_adapted=0.12,
        size_mcx=0.1,
        size_dsx=0.08,
        size_fe=0.2,
        size_expo=0.2,
    )

    assert result["decision"] == "BUY"
    assert result["decision_canonical"] == "buy"
    assert result["review_required"] is True
    assert result["ejecucion_autorizada"] is False
    assert result["trading_enabled"] is False
    assert result["orders_created"] is False
    assert result["orders_executed"] is False


def test_operator_bad_confidence_forces_hold() -> None:
    result = ensamblar_operacion(
        score_direccional=0.9,
        confianza=math.nan,
        fase="TENDENCIA",
        size_kelly=0.15,
        size_kelly_adapted=0.12,
        size_mcx=0.1,
        size_dsx=0.08,
        size_fe=0.2,
        size_expo=0.2,
    )

    assert result["decision"] == "HOLD"
    assert result["decision_canonical"] == "hold"
    assert result["size_final"] == 0.0
    assert result["ejecucion_autorizada"] is False


@pytest.mark.parametrize(
    ("raw", "canonical"),
    [("COMPRAR", "buy"), ("VENDER", "sell"), ("ESPERAR", "hold"), ("BUY", "buy")],
)
def test_feedback_uses_the_same_signal_contract(raw: str, canonical: str) -> None:
    assert _safe_signal({"decision": raw}) == canonical
    assert _safe_signal({"signal": raw}) == canonical


def test_feedback_drops_unknown_action_labels() -> None:
    assert _safe_signal({"decision": "PLACE_ORDER_NOW"}) is None


def test_reasoning_decision_risk_and_feedback_share_one_signal_contract(
    tmp_path, monkeypatch
) -> None:
    from REASON import orchestrator
    from REASON.schemas import SensoryInput

    state_path = tmp_path / "cathedral-state.json"
    monkeypatch.setattr(
        orchestrator._think_orchestrator.transductor, "output_path", state_path
    )
    prices = [100.0 * math.exp(0.001 * index) for index in range(60)]
    state = orchestrator.execute_cycle(
        SensoryInput(precio_historico=prices, precio_actual=prices[-1])
    )

    financial = state.percepcion_espacial["analisis_financiero"]
    canonical = normalizar_senal(state.decision)
    assert canonical in {"buy", "sell", "hold"}
    assert financial["trading_enabled"] is False
    assert financial["orders_created"] is False
    assert financial["orders_executed"] is False

    if canonical in {"buy", "sell"} and not financial["risk_flags"]:
        assert state.decisiones
        action_label = state.decisiones[0]["accion"]
    else:
        action_label = "ESPERAR"

    intent = preparar_intencion(
        action_label,
        state.confianza,
        risk_flags=financial["risk_flags"],
    )
    assert intent["decision"] == canonical
    assert _safe_signal({"decision": action_label}) == canonical
    assert intent["trading_enabled"] is False
    assert intent["orders_created"] is False
    assert intent["orders_executed"] is False

    allowed, _reason = verificar_seguridad(
        action_label,
        state.confianza,
        {
            "entropia": 0.1,
            "volatilidad": financial["realized_volatility_per_observation"],
        },
    )
    assert allowed is (canonical == "hold" or state.confianza >= 0.40)
