"""Shannon entropy over categorical observations, measured in bits."""
from collections import Counter
from math import log2
def entropia(observaciones) -> float:
    values = list(observaciones)
    if not values:
        return 0.0
    counts = Counter(values)
    total = len(values)
    return -sum((count / total) * log2(count / total) for count in counts.values())
