"""Translate validated RSX payloads into the SCX sensory contract."""
from __future__ import annotations
from typing import Any
from REASON.schemas import SensoryInput
from .sensors import normalize_market_payload

def construir_sensory_input(payload: dict[str, Any], free_energy_prev: float = 0.0) -> SensoryInput:
    data = normalize_market_payload(payload)
    constraints = payload.get("DYNAMIC_CONSTRAINTS", {})
    if not isinstance(constraints, dict):
        raise ValueError("DYNAMIC_CONSTRAINTS debe ser un objeto cuando se proporciona")
    return SensoryInput(precio_historico=data["historial_precios"], precio_actual=data["precio"],
                        gap=data["gap"], inercia=data["inercia"], free_energy_prev=free_energy_prev,
                        dynamic_constraints=constraints)

def from_snapshot(snapshot: dict[str, Any], free_energy_prev: float = 0.0) -> SensoryInput:
    if not isinstance(snapshot, dict) or not isinstance(snapshot.get("PERCEIVE"), dict):
        raise ValueError("snapshot must contain a PERCEIVE object")
    payload = dict(snapshot["PERCEIVE"])
    constraints = snapshot.get("DYNAMIC_CONSTRAINTS", {})
    if not isinstance(constraints, dict):
        raise ValueError("DYNAMIC_CONSTRAINTS debe ser un objeto cuando se proporciona")
    payload["DYNAMIC_CONSTRAINTS"] = constraints
    return construir_sensory_input(payload, free_energy_prev)
