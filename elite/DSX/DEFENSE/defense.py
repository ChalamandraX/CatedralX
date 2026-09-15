"""Quantum shield: compound risk monitoring and global panic blocking."""

import os
import time
from typing import Any, Dict, List

import psutil


PATH_PANIC = os.path.expanduser("~/LAB/03-OUTPUT/.panic")


def riesgo_compuesto(riesgo_ram: float, riesgo_codigo: float) -> float:
    """Combine RAM and code risk with the system's configured weights."""
    return 0.55 * riesgo_ram + 0.45 * riesgo_codigo


def riesgo_ram_monitor() -> float:
    """Return RAM pressure normalized to one at 90 percent usage."""
    uso = psutil.virtual_memory().percent
    return max(0.0, min(1.0, uso / 90.0))


def limitar_tasa(
    timestamps: List[float],
    max_calls: int = 10,
    ventana: int = 60,
) -> bool:
    """Record a call and report whether the rolling limit is reached."""
    ahora = time.time()
    while timestamps and ahora - timestamps[0] > ventana:
        timestamps.pop(0)
    if len(timestamps) >= max_calls:
        return True
    timestamps.append(ahora)
    return False


def activar_panic(reason: str = "RIESGO_ALTO") -> None:
    """Create the global panic marker with the supplied reason."""
    os.makedirs(os.path.dirname(PATH_PANIC), exist_ok=True)
    with open(PATH_PANIC, "w", encoding="utf-8") as panic_file:
        panic_file.write(reason)


def desactivar_panic() -> None:
    """Remove the global panic marker when it exists."""
    if os.path.exists(PATH_PANIC):
        os.remove(PATH_PANIC)


def estado_defensivo(estado_sistema: Dict[str, Any]) -> Dict[str, Any]:
    """Return normalized risk details and current blocking state."""
    riesgo_ram = riesgo_ram_monitor()
    riesgo_codigo = estado_sistema.get("entropia", 0.5)
    total = riesgo_compuesto(riesgo_ram, riesgo_codigo)
    return {
        "riesgo_total": round(total, 4),
        "riesgo_ram": round(riesgo_ram, 4),
        "riesgo_codigo": round(riesgo_codigo, 4),
        "bloqueo_activo": total > 0.85,
        "panic_activo": os.path.exists(PATH_PANIC),
    }