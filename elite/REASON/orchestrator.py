#!/usr/bin/env python3
"""Main reasoning loop: reads PERCEIVE and writes the shared Cathedral state."""

import json
import time
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

from . import anharmonic, cerebellum, free_energy, gyroscope, hurst_analyzer, mental_power
from . import geometry
from .hamiltonian import HamiltonianEngine
from .procesador import TransductorEndocrino
from .schemas import CathedralState, SensoryInput

SNAPSHOT_PATH = Path("/dev/shm/cathedral_snapshot.json")
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


def generar_decisiones(neurovector: List[float], regimen: str) -> List[Dict[str, Any]]:
    """Generate a market action from the compressed vector and regime."""
    señal = neurovector[3]
    estabilidad = neurovector[2]
    if estabilidad <= 0.5:
        return []
    if señal > 0.6 and "TENDENCIA" in regimen:
        return [{"accion": "COMPRAR", "confianza": señal, "modo": "MERCADO"}]
    if señal < -0.6 and "TENDENCIA" in regimen:
        return [{"accion": "VENDER", "confianza": abs(señal), "modo": "MERCADO"}]
    return []


class Orchestrator:
    def __init__(self) -> None:
        self.transductor = TransductorEndocrino()
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
        precios = [float(value) for value in perceive.get("historial_precios", [])]
        if not precios:
            precios = (60000.0 + np.random.normal(0, 100, 60)).tolist()
        return SensoryInput(
            precio_historico=precios,
            precio_actual=float(perceive.get("precio", precios[-1])),
            gap=float(perceive.get("gap", 0.0)),
            inercia=float(perceive.get("inercia", 0.0)),
            free_energy_prev=self.ultimo_fe,
        )

    def ejecutar_ciclo(self, entrada: SensoryInput) -> CathedralState:
        precios = entrada.precio_historico
        h_val = hurst_analyzer.hurst_exponent(precios)
        cr_val, score_anarmonico = anharmonic.analyze(precios)
        giro = gyroscope.gyro_state(precios, self._gyro_filter_state)
        self._gyro_filter_state = giro.pop("_estado_filtro", None)

        volatilidad = float(np.std(np.diff(np.log(np.maximum(precios[-20:], 1e-12))))) if len(precios) > 20 else 0.01
        retorno = float(np.log(max(precios[-1], 1e-12) / max(precios[-2], 1e-12))) if len(precios) > 1 else 0.0
        fe = free_energy.free_energy(
            prediccion_tendencia=0.5 + (h_val - 0.5),
            realidad_gap=abs(entrada.gap),
            inercia_observada=entrada.inercia,
            retorno_actual=retorno,
            coherencia_previa=max(0.0, 1.0 - self.ultimo_fe / 20.0),
        )
        self.ultimo_fe = fe

        direccion = 1.0 if precios[-1] > precios[0] else -1.0 if precios[-1] < precios[0] else 0.0
        decision = cerebellum.colapsar_qubit(
            fuerza_tendencia=abs(h_val - 0.5) * 2.0,
            fuerza_rango=score_anarmonico,
            direccion=direccion,
            cortisol=0.3,
        )
        confianza = round(max(abs(h_val - 0.5) * 2.0, score_anarmonico), 4)
        carga_mental = mental_power.evaluate_stress(0.3, fe)
        hamiltoniano = self.hamiltonian_engine.compute(
            {
                "volatilidad_local": volatilidad,
                "gap": entrada.gap,
                "sentimiento_riesgo": carga_mental,
            }
        )
        if abs(hamiltoniano) > HAMILTONIAN_PROTECTION_LIMIT:
            decision = "EMERGENCY_FLATTEN"
            confianza = 1.0
        paquete = {
            "timestamp": int(time.time()),
            "contexto": {
                "market_phase": "TENDENCIA" if h_val > 0.55 else "REVERSION" if h_val < 0.45 else "LATERAL",
                "geometry_regime": "ELIPTICO" if score_anarmonico > 0.6 else "HIPERBOLICO",
                "senal_combinada": decision,
                "last_decision": decision,
                "carga_mental": carga_mental,
                "hamiltoniano": hamiltoniano,
                "modo": "PROTECCION" if decision == "EMERGENCY_FLATTEN" else "NORMAL",
            },
            "percepcion_espacial": {"hurst": round(h_val, 4), "gap_detectado": round(entrada.gap, 6), "inercia": round(entrada.inercia, 6), "free_energy": round(fe, 4)},
            "giroscopio": giro,
            "razon_anarmonica": {"cross_ratio": round(cr_val, 6), "score": round(score_anarmonico, 4), "senal": decision, "zona": "estable" if score_anarmonico > 0.7 else "indefinido"},
        }
        self.transductor.volcar_estado_quimico(paquete)
        return CathedralState(
            int(time.time()),
            decision,
            confianza,
            round(fe, 4),
            self.transductor.leer_estado_actual().get("concentracion_actual", {}),
            giro,
            paquete["razon_anarmonica"],
            paquete["percepcion_espacial"],
            hamiltoniano,
            carga_mental,
        )

    def bucle_infinito(self) -> None:
        print("Orchestrator v4.0 - Bucle principal iniciado")
        while True:
            try:
                datos = self._leer_snapshot_percibido()
                if not datos:
                    time.sleep(2)
                    continue
                estado = self.ejecutar_ciclo(self._construir_sensory_input(datos))
                datos["REASON"] = {
                    "decision": estado.decision,
                    "confianza": estado.confianza,
                    "hurst": estado.percepcion_espacial["hurst"],
                    "free_energy": estado.free_energy,
                    "hamiltoniano": estado.hamiltoniano,
                    "energia_cognitiva": estado.energia_cognitiva,
                    "giroscopio": estado.giroscopio,
                    "razon_anarmonica": estado.razon_anarmonica,
                }
                SNAPSHOT_PATH.write_text(json.dumps(datos, indent=2), encoding="utf-8")
                print(f"Ciclo completado | Decision: {estado.decision} | Hurst: {estado.percepcion_espacial['hurst']:.4f}")
                time.sleep(3)
            except Exception as error:
                print(f"Error en ciclo: {error}")
                time.sleep(2)


if __name__ == "__main__":
    Orchestrator().bucle_infinito()


def execute_cycle(sensory_data: SensoryInput) -> CathedralState:
    """Public functional entry point for a single reasoning cycle."""
    return Orchestrator().ejecutar_ciclo(sensory_data)


_think_orchestrator = Orchestrator()


def think(
    sensory_input: SensoryInput,
    historial_precios: List[float],
    ciclo_id: int,
) -> CathedralState:
    """Run the complete reasoning flow using the repository's current APIs."""
    entrada = SensoryInput(
        precio_historico=historial_precios,
        precio_actual=sensory_input.precio_actual,
        gap=sensory_input.gap,
        inercia=sensory_input.inercia,
        free_energy_prev=sensory_input.free_energy_prev,
    )
    estado = _think_orchestrator.ejecutar_ciclo(entrada)
    geo_state = geometry.analyze_geometry(historial_precios)
    neurovector = construir_neurovector(
        estado.giroscopio,
        geo_state,
        estado.percepcion_espacial.get("hurst", 0.5),
        estado.free_energy,
    )
    decisiones = generar_decisiones(neurovector, geo_state.get("regimen", "INDEFINIDO"))
    if estado.decision == "EMERGENCY_FLATTEN":
        decisiones = [{"accion": "EMERGENCY_FLATTEN", "confianza": 1.0, "modo": "PROTECCION"}]
    elif estado.energia_cognitiva > 0.8:
        decisiones = []

    estado.decisiones = decisiones
    estado.neurovector = neurovector
    estado.regimen = str(geo_state.get("regimen", "INDEFINIDO"))
    estado.señal_combinada = str(geo_state.get("señal_combinada", "lateral"))
    estado.percepcion_espacial["ciclo_id"] = ciclo_id
    estado.percepcion_espacial["neurovector"] = neurovector
    return estado