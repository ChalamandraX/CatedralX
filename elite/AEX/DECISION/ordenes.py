"""Build and persist pending BTCUSDT orders from validated decisions."""

import json
import time
from pathlib import Path
from typing import Any, Dict


COMMAND_OUTPUT = Path(__file__).parents[3] / "03-OUTPUT" / "orden.json"
STOP_LOSS_PCT = 0.02
TAKE_PROFIT_PCT = 0.04
_ACTIVE_ACTIONS = {"ENTRAR_LARGO", "ENTRAR_CORTO"}


def _guardar_memoria(decision: Dict[str, Any]) -> None:
    """Persist a compact decision history without requiring another module."""
    history_path = COMMAND_OUTPUT.with_name("decisiones.jsonl")
    history_path.parent.mkdir(parents=True, exist_ok=True)
    with history_path.open("a", encoding="utf-8") as history_file:
        history_file.write(
            json.dumps(
                {
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "accion": decision["accion"],
                    "confianza": decision["confianza"],
                    "razon": decision["razon"],
                },
                ensure_ascii=False,
            )
            + "\n"
        )


def generar_orden(decision: Dict[str, Any], precio_actual: float) -> Dict[str, Any] | None:
    """Create and persist an order, or return ``None`` for ``ESPERAR``."""
    accion = decision.get("accion")
    if accion == "ESPERAR":
        return None
    if accion not in _ACTIVE_ACTIONS:
        raise ValueError(f"Acción no soportada: {accion!r}")

    precio = float(precio_actual)
    if precio <= 0.0:
        raise ValueError("precio_actual debe ser positivo")
    tamano = float(decision.get("tamano", 0.0))
    confianza = float(decision.get("confianza", 0.0))
    if tamano < 0.0 or confianza < 0.0:
        raise ValueError("tamano y confianza no pueden ser negativos")

    if accion == "ENTRAR_LARGO":
        stop_loss = round(precio * (1.0 - STOP_LOSS_PCT), 2)
        take_profit = round(precio * (1.0 + TAKE_PROFIT_PCT), 2)
    else:
        stop_loss = round(precio * (1.0 + STOP_LOSS_PCT), 2)
        take_profit = round(precio * (1.0 - TAKE_PROFIT_PCT), 2)

    orden = {
        "id": int(time.time() * 1000),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "activo": "BTCUSDT",
        "accion": accion,
        "tamano": tamano,
        "precio_referencia": precio,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "confianza": confianza,
        "motivo": str(decision.get("razon", "")),
        "estado": "PENDIENTE",
    }

    COMMAND_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = COMMAND_OUTPUT.with_suffix(".tmp")
    temporary_path.write_text(json.dumps(orden, indent=2, ensure_ascii=False), encoding="utf-8")
    temporary_path.replace(COMMAND_OUTPUT)
    _guardar_memoria(decision)
    return orden