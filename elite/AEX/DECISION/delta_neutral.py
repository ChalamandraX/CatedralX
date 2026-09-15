"""Delta-neutral hedge recommendations for the execution layer."""

import time
from typing import Any, Dict


class DeltaNeutral:
    """Estimate and offset net delta for a spot position."""

    def __init__(self) -> None:
        self.posicion_neta = 0.0
        self.delta_total = 0.0
        self.gamma_total = 0.0
        self.hedge_ratio = 0.0
        self.ultimo_ajuste = 0

    def calcular_delta(self, precio: float, hurst: float, volatilidad: float) -> float:
        """Return an approximate delta based on the market regime."""
        if hurst > 0.65:
            return 0.85 if precio > 75000 else -0.85
        if hurst < 0.45:
            return 0.35
        return 0.15 * (1.0 - abs(volatilidad * 100.0))

    def ajustar_hedge(
        self,
        posicion_spot: float,
        hurst: float,
        volatilidad: float,
        precio: float,
    ) -> Dict[str, Any]:
        """Calculate and store the hedge required to offset spot delta."""
        self.posicion_neta = float(posicion_spot)
        delta = self.calcular_delta(float(precio), float(hurst), float(volatilidad))
        self.delta_total = delta * self.posicion_neta
        self.hedge_ratio = -self.delta_total
        self.ultimo_ajuste = int(time.time())

        return {
            "posicion_actual": round(self.posicion_neta, 6),
            "delta_neto": round(self.delta_total, 4),
            "hedge_recomendado": round(self.hedge_ratio, 6),
            "accion": "REDUCIR" if abs(self.delta_total) > 0.15 else "MANTENER",
            "regimen": (
                "TENDENCIA" if hurst > 0.65 else "REVERSIVA" if hurst < 0.45 else "LATERAL"
            ),
            "timestamp": self.ultimo_ajuste,
        }

    def estado(self) -> Dict[str, Any]:
        """Return the current hedge state."""
        return {
            "delta_total": round(self.delta_total, 4),
            "hedge_ratio": round(self.hedge_ratio, 4),
            "exposicion_neta": round(abs(self.posicion_neta), 6),
            "neutral": abs(self.delta_total) < 0.08,
        }