"""Canonical signal vocabulary shared by reasoning, risk, action and feedback.

This module only normalizes labels. It never authorizes, creates, or executes
orders. Unknown labels must be rejected instead of guessed.
"""

from __future__ import annotations

from typing import Any

ALIASES: dict[str, str] = {
    # Canonical English signal labels.
    "BUY": "buy",
    "SELL": "sell",
    "HOLD": "hold",
    # Existing Spanish reasoning labels.
    "COMPRAR": "buy",
    "COMPRA": "buy",
    "VENDER": "sell",
    "VENTA": "sell",
    "ESPERAR": "hold",
    "LATERAL": "hold",
    # Legacy action/order vocabulary, normalized for analysis only.
    "ENTRAR_LARGO": "buy",
    "ENTRAR_CORTO": "sell",
    "WAIT": "hold",
}


def normalizar_senal(value: Any) -> str:
    """Return canonical 'buy'/'sell'/'hold'; reject ambiguous input."""
    if not isinstance(value, str):
        raise TypeError("La señal debe ser texto: buy, sell o hold.")
    key = "_".join(value.strip().upper().replace("-", "_").split())
    try:
        return ALIASES[key]
    except KeyError as exc:
        raise ValueError(f"Señal no reconocida: {value!r}") from exc
