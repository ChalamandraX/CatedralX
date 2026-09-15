"""Bounded cognitive-load estimate for the endocrine decision layer."""


def evaluate_stress(cortisol: float, free_energy: float) -> float:
    """Combine endocrine stress and surprise into a value in ``[0, 1]``."""
    cortisol_load = max(0.0, min(1.0, float(cortisol)))
    energy_load = max(0.0, min(1.0, float(free_energy) / 20.0))
    return round(cortisol_load * 0.6 + energy_load * 0.4, 4)