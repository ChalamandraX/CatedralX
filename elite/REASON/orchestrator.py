#!/usr/bin/env python3
"""Main reasoning loop: reads PERCEIVE and writes the shared Cathedral state."""

import json
import math
import os
import time
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

from . import anharmonic, cerebellum, free_energy, gyroscope, hurst_analyzer, mental_power
from . import geometry
from .financial_engine import analyze_financial_market
from .hamiltonian import HamiltonianEngine
from .procesador import TransductorEndocrino
from .schemas import CathedralState, SensoryInput

SNAPSHOT_PATH = Path(os.environ.get("CATEDRALX_SNAPSHOT_PATH", "/dev/shm/cathedral_snapshot.json")).expanduser()
HAMILTONIAN_PROTECTION_LIMIT = 45.0


def construir_neurovector(
    gyro: Dict[str, Any],
    geo: Dict[str, Any],
    hurst: float,
    energia_libre: float,
) -> List[float]:
    """Build a compact state vector from the repository's dict-based outputs."""
    señal = geo.get("señal_combinada", "lateral")
    señal_valor = {"compra": 1.0, "venta": -1.0}.get(señal, 0.0)
    return [
        float(gyro.get("omega", 0.0)),
        float(gyro.get("precesion", 0.0)),
        float(gyro.get("estabilidad", 0.5)),
        señal_valor,
        float(hurst),
        float(energia_libre),
    ]


class Orchestrator:
    def __init__(self) -> None:
        configured_state = os.getenv("CATEDRALX_STATE_PATH")
        state_path = (
            Path(configured_state).expanduser()
            if configured_state
            else Path.home() / ".local" / "state" / "chalamandra" / "catedralx" / "hormonas.json"
        ).resolve()
        repo_root = Path(__file__).resolve().parents[2]
        if state_path == repo_root or repo_root in state_path.parents:
            raise ValueError("CATEDRALX_STATE_PATH debe estar fuera del repositorio de CatedralX.")
        self.transductor = TransductorEndocrino(output_path=state_path)
        self.ultimo_fe = 0.0
        self._gyro_filter_state = None
        self.hamiltonian_engine = HamiltonianEngine()

    def _leer_snapshot_percibido(self) -> Dict[str, Any]:
        try:
            return json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _construir_sensory_input(self, datos_percibidos: Dict[str, Any]) -> SensoryInput:
        perceive = datos_percibidos.get("PERCEIVE", {})
        if not isinstance(perceive, dict):
            raise ValueError("PERCEIVE debe ser un objeto con precios observados.")
        raw_prices = perceive.get("historial_precios", [])
        if not isinstance(raw_prices, list) or not raw_prices:
            raise ValueError("No hay historial de precios observado; se cancela el ciclo sin datos sintéticos.")
        precios: list[float] = []
        for index, value in enumerate(raw_prices):
            if isinstance(value, bool):
                raise ValueError(f"historial_precios[{index}] debe ser positivo y finito.")
            price = float(value)
            if not math.isfinite(price) or price <= 0:
                raise ValueError(f"historial_precios[{index}] debe ser positivo y finito.")
            precios.append(price)
        precio_actual = float(perceive.get("precio", precios[-1]))
        if not math.isfinite(precio_actual) or precio_actual <= 0:
            raise ValueError("PERCEIVE.precio debe ser positivo y finito.")
        if not precios or precios[-1] != precio_actual:
            precios.append(precio_actual)
        if len(precios) < 30:
            raise ValueError(f"Historial insuficiente: se requieren al menos 30 precios; hay {len(precios)}.")
        gap = float(perceive.get("gap", 0.0))
        inercia = float(perceive.get("inercia", 0.0))
        if not math.isfinite(gap) or not math.isfinite(inercia):
            raise ValueError("gap e inercia deben ser valores finitos.")
        return SensoryInput(
            precio_historico=precios,
            precio_actual=precio_actual,
            gap=gap,
            inercia=inercia,
            free_energy_prev=self.ultimo_fe,
        )

    def ejecutar_ciclo(self, entrada: SensoryInput) -> CathedralState:
        """Run one financial-analysis cycle and persist only its canonical state."""
        raw_prices = list(entrada.precio_historico)
        current = float(entrada.precio_actual)
        if not math.isfinite(current) or current <= 0:
            raise ValueError("precio_actual debe ser positivo y finito.")
        if raw_prices and raw_prices[-1] != current:
            raw_prices.append(current)

        # Financial validation happens before any cognitive state is advanced or saved.
        financial = analyze_financial_market(raw_prices)
        prices = [float(value) for value in raw_prices]
        gap = float(entrada.gap)
        inertia = float(entrada.inercia)
        if not math.isfinite(gap) or not math.isfinite(inertia):
            raise ValueError("gap e inercia deben ser valores finitos.")

        h_val = hurst_analyzer.hurst_exponent(prices)
        cr_val, score_anarmonico = anharmonic.analyze(prices)
        giro = gyroscope.gyro_state(prices, self._gyro_filter_state)
        self._gyro_filter_state = giro.pop("_estado_filtro", None)

        volatility = float(np.std(np.diff(np.log(np.maximum(prices[-20:], 1e-12)))) if len(prices) > 20 else 0.01)
        retorno = float(np.log(max(prices[-1], 1e-12) / max(prices[-2], 1e-12))) if len(prices) > 1 else 0.0
        fe = free_energy.free_energy(
            prediccion_tendencia=0.5 + (h_val - 0.5),
            realidad_gap=abs(gap),
            inercia_observada=inertia,
            retorno_actual=retorno,
            coherencia_previa=max(0.0, 1.0 - self.ultimo_fe / 20.0),
        )
        self.ultimo_fe = fe

        direction = 1.0 if prices[-1] > prices[0] else -1.0 if prices[-1] < prices[0] else 0.0
        # The legacy qubit uses random sampling. Keep its diagnostic role but
        # use deterministic argmax in the canonical cycle so repeated analyses
        # of identical data do not persist different legacy labels.
        legacy_decision = cerebellum.colapsar_qubit_determinista(
            fuerza_tendencia=abs(h_val - 0.5) * 2.0,
            fuerza_rango=score_anarmonico,
            direccion=direction,
            cortisol=0.3,
        )
        legacy_confidence = round(max(abs(h_val - 0.5) * 2.0, score_anarmonico), 4)
        cognitive_load = mental_power.evaluate_stress(0.3, fe)
        hamiltonian = self.hamiltonian_engine.compute(
            {
                "volatilidad_local": volatility,
                "gap": gap,
                "sentimiento_riesgo": cognitive_load,
            }
        )

        # Hamiltonian protection is a review/hold gate, not an order to flatten:
        # position and portfolio context are not available to this analysis-only motor.
        if abs(hamiltonian) > HAMILTONIAN_PROTECTION_LIMIT:
            financial["risk_flags"] = list(financial["risk_flags"])
            if "hamiltonian_protection_triggered" not in financial["risk_flags"]:
                financial["risk_flags"].append("hamiltonian_protection_triggered")
            financial["signal"] = "hold"
            financial["combined_signal"] = "lateral"
            financial["regime"] = "RISK_PROTECTION_HOLD"
            financial["signal_strength"] = 0.0
            financial["decision_reason"] = (
                "Se bloqueó la etiqueta direccional por el umbral de protección "
                "hamiltoniana; se requiere revisión manual."
            )

        decision = str(financial["signal"])
        signal_strength = float(financial["signal_strength"])
        decisions: List[Dict[str, Any]] = []
        if decision == "buy" and not financial["risk_flags"]:
            decisions = [{
                "accion": "COMPRAR",
                "confianza": signal_strength,
                "modo": "ANALISIS_FINANCIERO",
            }]
        elif decision == "sell" and not financial["risk_flags"]:
            decisions = [{
                "accion": "VENDER",
                "confianza": signal_strength,
                "modo": "ANALISIS_FINANCIERO",
            }]

        package = {
            "timestamp": int(time.time()),
            "contexto": {
                "market_phase": financial["regime"],
                "geometry_regime": "ELIPTICO" if score_anarmonico > 0.6 else "HIPERBOLICO",
                "señal_combinada": financial["combined_signal"],
                "last_decision": decision,
                "decision_financiera": decision,
                "decision_subsistema_original": legacy_decision,
                "confianza_subsistema_original": legacy_confidence,
                "decision_subsistema_original_rol": "diagnostico_no_autoritativo",
                "decision_subsistema_original_es_estocastico": False,
                "signal_strength": signal_strength,
                "signal_strength_is_probability": False,
                "financial_risk_flags": financial["risk_flags"],
                "carga_mental": cognitive_load,
                "hamiltoniano": hamiltonian,
                "modo": "PROTECCION" if financial["risk_flags"] else "ANALISIS_FINANCIERO",
                "trading_enabled": False,
                "orders_created": False,
                "orders_executed": False,
            },
            "percepcion_espacial": {
                "hurst": round(h_val, 4),
                "gap_detectado": round(gap, 6),
                "inercia": round(inertia, 6),
                "free_energy": round(fe, 4),
                "analisis_financiero": financial,
                "decision_subsistema_original": legacy_decision,
                "decision_subsistema_original_rol": "diagnostico_no_autoritativo",
                "decision_subsistema_original_es_estocastico": False,
            },
            "giroscopio": giro,
            "razon_anarmonica": {
                "cross_ratio": round(cr_val, 6),
                "score": round(score_anarmonico, 4),
                "senal": legacy_decision,
                "zona": "estable" if score_anarmonico > 0.7 else "indefinido",
            },
        }
        self.transductor.volcar_estado_quimico(package)
        state = CathedralState(
            int(time.time()),
            decision,
            signal_strength,
            round(fe, 4),
            self.transductor.leer_estado_actual().get("concentracion_actual", {}),
            giro,
            package["razon_anarmonica"],
            package["percepcion_espacial"],
            hamiltonian,
            cognitive_load,
        )
        state.decisiones = decisions
        state.regimen = str(financial["regime"])
        state.señal_combinada = str(financial["combined_signal"])
        return state

    def bucle_infinito(self) -> None:
        print("CatedralX Motor Financiero v1 - análisis sin ejecución de órdenes")
        while True:
            try:
                datos = self._leer_snapshot_percibido()
                if not datos:
                    time.sleep(2)
                    continue
                entrada = self._construir_sensory_input(datos)
                estado = think(entrada, entrada.precio_historico, int(time.time()))
                datos["REASON"] = {
                    "decision": estado.decision,
                    "signal_strength": estado.confianza,
                    "signal_strength_is_probability": False,
                    "regime": estado.regimen,
                    "combined_signal": estado.señal_combinada,
                    "hurst": estado.percepcion_espacial.get("hurst"),
                    "free_energy": estado.free_energy,
                    "hamiltoniano": estado.hamiltoniano,
                    "energia_cognitiva": estado.energia_cognitiva,
                    "giroscopio": estado.giroscopio,
                    "razon_anarmonica": estado.razon_anarmonica,
                    "analisis_financiero": estado.percepcion_espacial.get("analisis_financiero"),
                    "orders_created": False,
                    "orders_executed": False,
                    "trading_enabled": False,
                }
                SNAPSHOT_PATH.write_text(json.dumps(datos, indent=2), encoding="utf-8")
                print(f"Ciclo completado | Decision: {estado.decision} | Hurst: {estado.percepcion_espacial['hurst']:.4f}")
                time.sleep(3)
            except Exception as error:
                print(f"Error en ciclo: {error}")
                time.sleep(2)


def execute_cycle(sensory_data: SensoryInput) -> CathedralState:
    """Public entry point routed through deterministic financial analysis."""
    return think(sensory_data, sensory_data.precio_historico, int(time.time()))

_think_orchestrator = Orchestrator()


def think(
    sensory_input: SensoryInput,
    historial_precios: List[float],
    ciclo_id: int,
) -> CathedralState:
    """Run deterministic financial analysis plus optional geometry diagnostics."""
    raw_prices = list(historial_precios)
    current = float(sensory_input.precio_actual)
    if not math.isfinite(current) or current <= 0:
        raise ValueError("precio_actual debe ser positivo y finito.")
    if raw_prices and raw_prices[-1] != current:
        raw_prices.append(current)
    gap_value = float(sensory_input.gap)
    inertia_value = float(sensory_input.inercia)
    if not math.isfinite(gap_value) or not math.isfinite(inertia_value):
        raise ValueError("gap e inercia deben ser valores finitos.")

    entrada = SensoryInput(
        precio_historico=raw_prices,
        precio_actual=current,
        gap=gap_value,
        inercia=inertia_value,
        free_energy_prev=sensory_input.free_energy_prev,
    )
    # ejecutar_ciclo validates financial inputs before touching persistent state.
    state = _think_orchestrator.ejecutar_ciclo(entrada)
    # Financial validation has passed in ejecutar_ciclo; normalize only for diagnostics.
    prices = [float(value) for value in raw_prices]
    try:
        geo_state = geometry.analyze_geometry(prices)
    except Exception as exc:
        # The financial output remains usable if this exploratory diagnostic fails.
        geo_state = {
            "regimen": "INDEFINIDO",
            "señal_combinada": "lateral",
            "diagnostic_error": type(exc).__name__,
        }
    neurovector = construir_neurovector(
        state.giroscopio,
        geo_state,
        state.percepcion_espacial.get("hurst", 0.5),
        state.free_energy,
    )
    state.neurovector = neurovector
    state.percepcion_espacial["diagnostico_geometrico"] = {
        key: value for key, value in geo_state.items() if key != "diagnostic_error"
    }
    if "diagnostic_error" in geo_state:
        state.percepcion_espacial["diagnostico_geometrico_error"] = geo_state["diagnostic_error"]
    state.percepcion_espacial["ciclo_id"] = ciclo_id
    state.percepcion_espacial["neurovector"] = neurovector
    return state

if __name__ == "__main__":
    Orchestrator().bucle_infinito()
