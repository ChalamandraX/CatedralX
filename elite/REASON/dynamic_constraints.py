"""Fail-closed hard constraints for the CatedralX dynamic loop.

This module evaluates governance constraints only. It does not allocate money,
create orders, or infer missing calibration values.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class DynamicConstraintInputs:
    reinvestment_surplus: Optional[float] = None
    entropy_rate: Optional[float] = None
    entropy_time_scale: Optional[float] = None
    loop_gain: Optional[float] = None
    dominant_signal_weight: Optional[float] = None
    minimum_confidence: Optional[float] = None
    signal_count: Optional[int] = None
    optimal_signal_count: Optional[int] = None
    exposure: Optional[float] = None
    max_exposure: Optional[float] = None
    resilience: Optional[float] = None
    minimum_resilience: Optional[float] = None
    degradation_rate: Optional[float] = None
    accumulated_noise: Optional[float] = None


def _finite(value: Optional[float]) -> bool:
    return value is not None and not isinstance(value, bool) and math.isfinite(float(value))


def evaluate_dynamic_constraints(inputs: DynamicConstraintInputs) -> Dict[str, Any]:
    """Evaluate only calibrated constraints; missing metrics never authorize growth.

    Entropy gate: B >= T * dS/dt. Loop stability: G < 1. Scale gate:
    N <= N*; E <= E_max; resilience >= R_min.
    """
    required = (
        "reinvestment_surplus", "entropy_rate", "entropy_time_scale", "loop_gain",
        "signal_count", "optimal_signal_count", "exposure", "max_exposure",
        "resilience", "minimum_resilience",
    )
    values = asdict(inputs)
    missing = [name for name in required if values[name] is None]
    invalid = [
        name for name, value in asdict(inputs).items()
        if value is not None and (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
        )
    ]
    issues = []
    if invalid:
        issues.append("DATOS_INVALIDOS")
    if missing:
        issues.append("METRICAS_NO_CALIBRADAS")

    entropy_ok = False
    feedback_ok = False
    scale_ok = False
    if not invalid and not missing:
        entropy_ok = float(inputs.reinvestment_surplus) >= float(inputs.entropy_time_scale) * float(inputs.entropy_rate)
        feedback_ok = float(inputs.loop_gain) < 1.0
        scale_ok = (
            int(inputs.signal_count) <= int(inputs.optimal_signal_count)
            and float(inputs.exposure) <= float(inputs.max_exposure)
            and float(inputs.resilience) >= float(inputs.minimum_resilience)
        )
        if not entropy_ok:
            issues.append("MANTENIMIENTO_ENTROPICO")
        if not feedback_ok:
            issues.append("FRENO_DINAMICO")
        if not scale_ok:
            issues.append("MODULARIZAR_O_REDUCIR_EXPOSICION")

    # Missing/invalid metrics block growth but are distinguished from measured breaches.
    growth_allowed = not invalid and not missing and entropy_ok and feedback_ok and scale_ok
    state = "CRECIMIENTO_PERMITIDO" if growth_allowed else (
        "MANTENIMIENTO" if "MANTENIMIENTO_ENTROPICO" in issues else
        "FRENO_DINAMICO" if "FRENO_DINAMICO" in issues else
        "MODULARIZAR" if "MODULARIZAR_O_REDUCIR_EXPOSICION" in issues else
        "RESTRICCIONES_NO_VERIFICADAS"
    )
    return {
        "state": state,
        "growth_allowed": growth_allowed,
        "entropy_constraint_ok": entropy_ok,
        "feedback_constraint_ok": feedback_ok,
        "scale_constraint_ok": scale_ok,
        "issues": issues,
        "missing_metrics": missing,
        "invalid_metrics": invalid,
        "degradation_rate_observed": inputs.degradation_rate,
        "accumulated_noise_observed": inputs.accumulated_noise,
        "automatic_recalibration": False,
        "automatic_modularization": False,
    }
