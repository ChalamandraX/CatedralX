#!/usr/bin/env python3
"""Daemon RSX: reads perceived data and records the reasoning state."""

import asyncio
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

BASE_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = BASE_DIR.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from REASON.orchestrator import Orchestrator
from REASON.schemas import SensoryInput
from PERCEIVE.percepcion import from_snapshot
from DSX.DEFENSE.guardian_ram import hay_suficiente_recurso


RITMO_SEGUNDOS = 15
HURST_MIN_PUNTOS = 30
SNAPSHOT_PATH = Path(__import__("os").environ.get("CATEDRALX_SNAPSHOT_PATH", "/dev/shm/cathedral_snapshot.json"))
OUTPUT_DIR = PROJECT_DIR / "03-OUTPUT"
HORMONAS_PATH = OUTPUT_DIR / "hormonas.json"
logger = logging.getLogger("rsx.bunker")


class BunkerDaemon:
    """Continuously process the latest PERCEIVE snapshot."""

    def __init__(self, ritmo: int = RITMO_SEGUNDOS) -> None:
        self.orchestrator = Orchestrator()
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

        sensory = self._construir_entrada(snapshot)
        state = self.orchestrator.ejecutar_ciclo(sensory)
        self._guardar_hormonas(state)
        snapshot["REASON"] = {
            "decision": state.decision,
            "confianza": state.confianza,
            "hurst": state.percepcion_espacial.get("hurst", 0.5),
            "free_energy": state.free_energy,
            "giroscopio": state.giroscopio,
            "razon_anarmonica": state.razon_anarmonica,
        }
        SNAPSHOT_PATH.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
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

    @staticmethod
    def _guardar_hormonas(state: Any) -> None:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        vector = state.neurovector if isinstance(state.neurovector, dict) else {}
        data = {
            "neurovector": vector,
            "timestamp": time.time(),
            "decision": state.decision,
            "confidence": state.confianza,
            "free_energy": state.free_energy,
            "hurst": state.percepcion_espacial.get("hurst", 0.5),
            "trading_enabled": False,
            "orders_created": False,
            "orders_executed": False,
        }
        HORMONAS_PATH.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )


async def main() -> None:
    await BunkerDaemon().heartbeat()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("RSX heartbeat stopped")