"""One-shot SCX entry point. Requires a real, validated RSX snapshot."""
from __future__ import annotations
import json, os, sys
from pathlib import Path

ELITE_DIR = Path(__file__).resolve().parents[1]
if str(ELITE_DIR) not in sys.path:
    sys.path.insert(0, str(ELITE_DIR))

from PERCEIVE.percepcion import from_snapshot
from PERCEIVE.api_pulse import validate_snapshot_payload
from REASON.orchestrator import execute_cycle, SNAPSHOT_PATH
from FEX.FEEDBACK.feedback_loop import registrar_prediccion

def main() -> int:
    path = Path(os.environ.get("CATEDRALX_SNAPSHOT_PATH", str(SNAPSHOT_PATH))).expanduser()
    try:
        snapshot = json.loads(path.read_text(encoding="utf-8"))
        freshness = validate_snapshot_payload(snapshot)
        if not freshness["healthy"]:
            raise ValueError("Snapshot rechazado: " + str(freshness["reason"]))
        sensory = from_snapshot(snapshot)
        state = execute_cycle(sensory)
    except (OSError, ValueError, TypeError) as exc:
        print(json.dumps({"status": "NO_CYCLE", "reason": str(exc),
                          "trading_enabled": False, "orders_created": False,
                          "orders_executed": False}, ensure_ascii=False, indent=2))
        return 2
    financial = state.percepcion_espacial.get("analisis_financiero", {})
    result = {
        "status": "ANALYSIS_COMPLETE",
        "decision": state.decision,
        "signal_strength": state.confianza,
        "signal_strength_is_probability": False,
        "regime": state.regimen,
        "combined_signal": state.señal_combinada,
        "hurst": state.percepcion_espacial.get("hurst"),
        "free_energy": state.free_energy,
        "financial_analysis": financial,
        "dynamic_constraints": state.percepcion_espacial.get("dynamic_constraints", {}),
        "growth_allowed": state.percepcion_espacial.get("growth_allowed", False),
        "reference_price": snapshot["PERCEIVE"].get("precio"),
        "observed_at": snapshot["PERCEIVE"].get("observed_at"),
        "market_source": snapshot["PERCEIVE"].get("source"),
        "legacy_diagnostic_signal": state.percepcion_espacial.get("decision_subsistema_original"),
        "legacy_diagnostic_role": "diagnostico_no_autoritativo",
        "legacy_diagnostic_is_stochastic": False,
        "trading_enabled": False,
        "orders_created": False,
        "orders_executed": False,
    }
    result["prediction_id"] = registrar_prediccion(result)
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
