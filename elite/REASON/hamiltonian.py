"""Instantaneous thermodynamic Hamiltonian for the reasoning cycle."""

import numpy as np


class HamiltonianEngine:
    """Calculate total energy as kinetic activity plus accumulated risk."""

    def __init__(self, masa: float = 1.0) -> None:
        if not np.isfinite(masa) or masa < 0.0:
            raise ValueError("masa must be finite and non-negative")
        self.masa = float(masa)

    def calcular_hamiltoniano(self, state: dict) -> float:
        """Return ``H = 0.5 * masa * volatilidad**2 + abs(gap) + riesgo``."""
        try:
            volatilidad = float(state.get("volatilidad_local", 0.0))
            gap = float(state.get("gap", 0.0))
            riesgo = float(state.get("sentimiento_riesgo", 0.0))
            if not np.all(np.isfinite([volatilidad, gap, riesgo])):
                return 0.0
            energia_cinetica = 0.5 * self.masa * volatilidad**2
            energia_potencial = abs(gap) + riesgo
            return float(energia_cinetica + energia_potencial)
        except (AttributeError, TypeError, ValueError, OverflowError):
            return 0.0

    compute = calcular_hamiltoniano


engine = HamiltonianEngine()