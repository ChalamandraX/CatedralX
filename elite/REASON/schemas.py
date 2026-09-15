"""Data contracts exchanged by the reasoning orchestrator."""

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class ReasonState:
    """Unified market, risk and decision state for the reasoning layer."""

    precio: float = 0.0
    historico: List[float] = field(default_factory=list)
    volatilidad_local: float = 0.0
    gap: float = 0.0
    microtrend: float = 0.0
    funding_rate: float = 0.0
    open_interest: float = 0.0
    kelly: float = 0.0
    iv: float = 0.0
    gamma: float = 0.0
    free_energy: float = 0.0
    hamiltoniano: float = 0.0
    sentimiento_riesgo: float = 0.0
    decision: str = "HOLD"
    decision_mode: str = "NEUTRAL"
    confianza: float = 0.0
    size_final: float = 0.0
    timestamp: float = 0.0


@dataclass
class SensoryInput:
    precio_historico: List[float]
    precio_actual: float
    gap: float = 0.0
    inercia: float = 0.0
    free_energy_prev: float = 0.0


@dataclass
class CathedralState:
    timestamp: int
    decision: str
    confianza: float
    free_energy: float
    neurovector: Any = field(default_factory=dict)
    giroscopio: Dict[str, Any] = field(default_factory=dict)
    razon_anarmonica: Dict[str, Any] = field(default_factory=dict)
    percepcion_espacial: Dict[str, Any] = field(default_factory=dict)
    hamiltoniano: float = 0.0
    energia_cognitiva: float = 0.0
    decisiones: List[Dict[str, Any]] = field(default_factory=list)
    regimen: str = "INDEFINIDO"
    señal_combinada: str = "lateral"