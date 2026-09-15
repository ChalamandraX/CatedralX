"""Endocrine homeostasis processor for the reasoning layer."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import numpy as np


OUTPUT_DIR = Path(__file__).parents[2] / "03-OUTPUT"
RUTA_HORMONAS = OUTPUT_DIR / "hormonas.json"

PARAMS = {
    "prod_O": 0.05, "prod_D": 0.08, "prod_S": 0.06, "prod_C": 0.005,
    "prod_A": 0.03, "prod_M": 0.01, "decay_O": 0.15, "decay_D": 0.12,
    "decay_S": 0.10, "decay_C": 0.25, "decay_A": 0.20, "decay_M": 0.05,
    "alpha1": 0.3, "alpha2": 0.2, "gamma1": 0.4, "gamma2": 0.1,
    "beta1": 0.05, "beta2": 0.15, "lam": 0.1, "theta": 0.05,
}


def _s(value: Any) -> Any:
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    return value


class ProcesadorEndocrino:
    """Translate surprise and market dynamics into hormone concentrations."""

    def __init__(self, output_path: Path | None = None) -> None:
        self.output_path = output_path or RUTA_HORMONAS
        self.conc: Dict[str, float] = {
            "oxitocina_O": 0.45, "dopamina_D": 0.60, "serotonina_S": 0.50,
            "cortisol_C": 0.30, "adrenalina_A": 0.40, "melatonina_M": 0.20,
        }
        self.contexto: Dict[str, Any] = {"market_phase": "desconocido", "señal_combinada": "LATERAL"}
        self._estado: Dict[str, Any] = {"concentracion_actual": self.conc.copy()}
        self._cargar()

    def _cargar(self) -> None:
        try:
            data = json.loads(self.output_path.read_text(encoding="utf-8"))
            loaded = data.get("concentracion_actual", {})
            if isinstance(loaded, dict):
                for name in self.conc:
                    if name in loaded:
                        self.conc[name] = float(np.clip(float(loaded[name]), 0.0, 1.0))
            if isinstance(data.get("contexto"), dict):
                self.contexto.update(data["contexto"])
            self._estado = data
        except (FileNotFoundError, OSError, json.JSONDecodeError, TypeError, ValueError):
            return

    def actualizar(self, inputs: Dict[str, Any]) -> Dict[str, float]:
        """Advance hormone concentrations by one homeostatic step."""
        sorpresa = min(abs(float(inputs.get("sorpresa", 0.0))), 2.0)
        gap = min(abs(float(inputs.get("gap", 0.0))), 0.05)
        inercia = min(abs(float(inputs.get("inercia", 0.0))), 1.0)
        cortisol = self.conc["cortisol_C"]
        self.conc["cortisol_C"] = float(np.clip(self.conc["cortisol_C"] + PARAMS["prod_C"] + PARAMS["beta1"] * sorpresa - PARAMS["decay_C"] * cortisol, 0.0, 1.0))
        self.conc["adrenalina_A"] = float(np.clip(self.conc["adrenalina_A"] + PARAMS["prod_A"] + PARAMS["beta2"] * gap + PARAMS["gamma1"] * cortisol - PARAMS["decay_A"] * self.conc["adrenalina_A"], 0.0, 1.0))
        self.conc["dopamina_D"] = float(np.clip(self.conc["dopamina_D"] + PARAMS["prod_D"] - PARAMS["alpha1"] * cortisol - PARAMS["decay_D"] * self.conc["dopamina_D"], 0.0, 1.0))
        self.conc["serotonina_S"] = float(np.clip(self.conc["serotonina_S"] + PARAMS["prod_S"] + PARAMS["lam"] * inercia - PARAMS["alpha2"] * cortisol - PARAMS["decay_S"] * self.conc["serotonina_S"], 0.0, 1.0))
        self.conc["oxitocina_O"] = float(np.clip(self.conc["oxitocina_O"] + PARAMS["prod_O"] - PARAMS["decay_O"] * self.conc["oxitocina_O"], 0.0, 1.0))
        self.conc["melatonina_M"] = float(np.clip(self.conc["melatonina_M"] + PARAMS["prod_M"] - PARAMS["decay_M"] * self.conc["melatonina_M"], 0.0, 1.0))
        return self.conc.copy()

    def guardar(self) -> Dict[str, Any]:
        """Persist the current endocrine state atomically."""
        data = {
            "timestamp": datetime.now().isoformat(),
            "concentracion_actual": {key: round(float(_s(value)), 4) for key, value in self.conc.items()},
            "estres_critico": self.conc["cortisol_C"] > 0.7,
            "contexto": self.contexto,
        }
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = self.output_path.with_suffix(".tmp")
        temporary_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        temporary_path.replace(self.output_path)
        self._estado = data
        return data

    def volcar_estado_quimico(self, inputs_entorno: Dict[str, Any]) -> None:
        """Compatibility entry point used by the reasoning orchestrator."""
        perception = inputs_entorno.get("percepcion_espacial", {})
        self.contexto = inputs_entorno.get("contexto", self.contexto)
        self.actualizar({
            "sorpresa": perception.get("free_energy", 0.0),
            "gap": perception.get("gap_detectado", 0.0),
            "inercia": perception.get("inercia", 0.0),
        })
        self.guardar()

    def leer_estado_actual(self) -> Dict[str, Any]:
        return self._estado


def procesar_estado_integrado(inputs_entorno: Dict[str, Any]) -> Dict[str, Any]:
    """Update and persist the process-wide endocrine state."""
    procesador.volcar_estado_quimico(inputs_entorno)
    return procesador.leer_estado_actual()


procesador = ProcesadorEndocrino()
TransductorEndocrino = ProcesadorEndocrino