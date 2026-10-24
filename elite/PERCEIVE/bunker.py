#!/usr/bin/env python3
"""Daemon RSX: reads perceived data and records the reasoning state."""

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from REASON.orchestrator import execute_cycle
from REASON.schemas import SensoryInput
from PERCEIVE.percepcion import from_snapshot
from PERCEIVE.api_pulse import validate_snapshot_payload
from PERCEIVE.data_feeder import snapshot_path
from DSX.DEFENSE.guardian_ram import hay_suficiente_recurso


RITMO_SEGUNDOS = 15
SNAPSHOT_PATH = snapshot_path()
logger = logging.getLogger("rsx.bunker")


class BunkerDaemon:
    """Continuously process validated snapshots through the shared engine."""

    def __init__(self, ritmo: int = RITMO_SEGUNDOS) -> None:
        self.ritmo = ritmo

    async def heartbeat(self) -> None:
        logger.info("RSX heartbeat started")
        while True:
            if not hay_suficiente_recurso():
                logger.warning("Resources constrained; pausing for 30 seconds")
                await asyncio.sleep(30)
                continue

            try:
                self._ciclo()
            except Exception:
                logger.exception("Error in RSX cycle")
            await asyncio.sleep(self.ritmo)

    def _ciclo(self) -> Optional[Dict[str, Any]]:
        snapshot = self._leer_snapshot()
        if not snapshot:
            logger.debug("No PERCEIVE snapshot available")
            return None

        freshness = validate_snapshot_payload(snapshot)
        if not freshness["healthy"]:
            raise ValueError("Snapshot rechazado: " + str(freshness["reason"]))

        sensory = self._construir_entrada(snapshot)
        state = execute_cycle(sensory)

        # The returned value may include diagnostics, but the source snapshot
        # remains read-only. The shared engine owns canonical state persistence.
        snapshot["REASON"] = {
            "decision": state.decision,
            "confianza": state.confianza,
            "signal_strength": state.confianza,
            "signal_strength_is_probability": False,
            "regime": state.regimen,
            "combined_signal": state.señal_combinada,
            "hurst": state.percepcion_espacial.get("hurst", 0.5),
            "free_energy": state.free_energy,
            "hamiltoniano": state.hamiltoniano,
            "energia_cognitiva": state.energia_cognitiva,
            "giroscopio": state.giroscopio,
            "razon_anarmonica": state.razon_anarmonica,
            "analisis_financiero": state.percepcion_espacial.get(
                "analisis_financiero", {}
            ),
            "trading_enabled": False,
            "orders_created": False,
            "orders_executed": False,
        }
        logger.info(
            "BTC: %,.2f | decision: %s | hurst: %.3f",
            sensory.precio_actual,
            state.decision,
            state.percepcion_espacial.get("hurst", 0.5),
        )
        return snapshot

    @staticmethod
    def _leer_snapshot() -> Dict[str, Any]:
        try:
            return json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    @staticmethod
    def _construir_entrada(snapshot: Dict[str, Any]) -> SensoryInput:
        # No fallback prices: missing or insufficient observations fail closed.
        return from_snapshot(snapshot)


async def main() -> None:
    await BunkerDaemon().heartbeat()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("RSX heartbeat stopped")