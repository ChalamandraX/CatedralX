"""Shannon entropy utilities for market and operation distributions."""

from typing import List

import numpy as np


def shannon_entropy(distribucion: List[float]) -> float:
    """Return Shannon entropy in bits, ignoring zero and negative values."""
    probabilities = np.asarray(distribucion, dtype=float)
    probabilities = probabilities[probabilities > 1e-9]
    if probabilities.size == 0:
        return 0.0
    return float(-np.sum(probabilities * np.log2(probabilities)))


def entropia_tamaños(tamaños: List[float]) -> float:
    """Return Shannon entropy after normalizing operation sizes."""
    if not tamaños:
        return 0.0
    total = sum(tamaños) or 1.0
    distribucion = [float(tamaño) / total for tamaño in tamaños]
    return shannon_entropy(distribucion)