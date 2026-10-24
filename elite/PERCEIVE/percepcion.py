"""Translate validated RSX payloads into the SCX sensory contract."""
from __future__ import annotations
from typing import Any
from REASON.schemas import SensoryInput
from .sensors import normalize_market_payload

def construir_sensory_input(payload: dict[str, Any], free_energy_prev: float = 0.0) -> SensoryInput:
    data = normalize_market_payload(payload)
    return SensoryInput(precio_historico=data["historial_precios"], precio_actual=data["precio"],
                        gap=data["gap"], inercia=data["inercia"], free_energy_prev=free_energy_prev)

def from_snapshot(snapshot: dict[str, Any], free_energy_prev: float = 0.0) -> SensoryInput:
    if not isinstance(snapshot, dict) or not isinstance(snapshot.get("PERCEIVE"), dict):
        raise ValueError("snapshot must contain a PERCEIVE object")
    return construir_sensory_input(snapshot["PERCEIVE"], free_energy_prev)
