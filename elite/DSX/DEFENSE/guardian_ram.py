"""System resource monitor for RAM and CPU availability."""

import psutil


def uso_ram_porcentaje() -> float:
    """Return current RAM usage percentage."""
    return float(psutil.virtual_memory().percent)


def uso_cpu_porcentaje() -> float:
    """Return CPU usage percentage measured over a short interval."""
    return float(psutil.cpu_percent(interval=0.1))


def hay_suficiente_recurso(
    umbral_ram: float = 85.0,
    umbral_cpu: float = 90.0,
) -> bool:
    """Return whether RAM and CPU usage remain below their thresholds."""
    ram = uso_ram_porcentaje()
    cpu = uso_cpu_porcentaje()
    return ram < umbral_ram and cpu < umbral_cpu


def memoria_disponible_mb() -> float:
    """Return available memory in mebibytes."""
    return float(psutil.virtual_memory().available / (1024 * 1024))