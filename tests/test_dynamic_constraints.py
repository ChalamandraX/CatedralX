"""Hard governance gates for the dynamic Cathedral loop."""

import math

from REASON.dynamic_constraints import (
    DynamicConstraintInputs,
    evaluate_dynamic_constraints,
)


def _safe_inputs():
    return DynamicConstraintInputs(
        reinvestment_surplus=10.0,
        entropy_rate=1.0,
        entropy_time_scale=2.0,
        loop_gain=0.7,
        dominant_signal_weight=0.4,
        minimum_confidence=0.8,
        signal_count=4,
        optimal_signal_count=5,
        exposure=0.2,
        max_exposure=0.5,
        resilience=0.9,
        minimum_resilience=0.7,
        degradation_rate=0.01,
        accumulated_noise=0.02,
    )


def test_all_hard_constraints_must_pass_before_growth():
    result = evaluate_dynamic_constraints(_safe_inputs())
    assert result["state"] == "CRECIMIENTO_PERMITIDO"
    assert result["growth_allowed"] is True
    assert result["automatic_recalibration"] is False
    assert result["automatic_modularization"] is False


def test_entropy_shortfall_enters_maintenance():
    inputs = _safe_inputs()
    inputs = DynamicConstraintInputs(**{**inputs.__dict__, "reinvestment_surplus": 1.0})
    result = evaluate_dynamic_constraints(inputs)
    assert result["state"] == "MANTENIMIENTO"
    assert result["growth_allowed"] is False
    assert "MANTENIMIENTO_ENTROPICO" in result["issues"]


def test_loop_gain_at_or_above_one_activates_dynamic_brake():
    inputs = DynamicConstraintInputs(**{**_safe_inputs().__dict__, "loop_gain": 1.0})
    result = evaluate_dynamic_constraints(inputs)
    assert result["state"] == "FRENO_DINAMICO"
    assert result["growth_allowed"] is False
    assert "FRENO_DINAMICO" in result["issues"]


def test_scale_breach_requires_modularization_or_lower_exposure():
    inputs = DynamicConstraintInputs(**{**_safe_inputs().__dict__, "signal_count": 6})
    result = evaluate_dynamic_constraints(inputs)
    assert result["state"] == "MODULARIZAR"
    assert result["growth_allowed"] is False


def test_missing_or_nonfinite_metrics_never_authorize_growth():
    missing = evaluate_dynamic_constraints(DynamicConstraintInputs())
    assert missing["growth_allowed"] is False
    assert "METRICAS_NO_CALIBRADAS" in missing["issues"]

    invalid = DynamicConstraintInputs(**{**_safe_inputs().__dict__, "loop_gain": math.nan})
    result = evaluate_dynamic_constraints(invalid)
    assert result["growth_allowed"] is False
    assert "DATOS_INVALIDOS" in result["issues"]


def test_orchestrator_holds_directional_signal_on_measured_hard_breach(tmp_path):
    import math
    from REASON import orchestrator
    from REASON.schemas import SensoryInput

    orchestrator._think_orchestrator.transductor.output_path = tmp_path / "state.json"
    prices = [100.0 * math.exp(0.001 * index) for index in range(60)]
    constraints = {
        "reinvestment_surplus": 1.0,
        "entropy_rate": 1.0,
        "entropy_time_scale": 2.0,
        "loop_gain": 0.7,
        "dominant_signal_weight": 0.4,
        "minimum_confidence": 0.8,
        "signal_count": 4,
        "optimal_signal_count": 5,
        "exposure": 0.2,
        "max_exposure": 0.5,
        "resilience": 0.9,
        "minimum_resilience": 0.7,
        "degradation_rate": 0.01,
        "accumulated_noise": 0.02,
    }
    state = orchestrator.execute_cycle(SensoryInput(
        precio_historico=prices, precio_actual=prices[-1], dynamic_constraints=constraints
    ))
    assert state.decision == "hold"
    assert state.percepcion_espacial["dynamic_constraints"]["state"] == "MANTENIMIENTO"
    assert state.percepcion_espacial["growth_allowed"] is False
    assert state.percepcion_espacial["analisis_financiero"]["trading_enabled"] is False
