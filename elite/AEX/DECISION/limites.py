"""Final position-size limits for the action execution layer."""


def calcular_tamano_final(
    tamano_kelly: float,
    tamano_optimizado: float,
    limite_defensa: float,
    energia_libre: float,
    limite_exposicion: float = 0.1,
) -> float:
    """Return the most restrictive position size after all risk limits."""
    factor_fe = max(0.1, 1.0 - (energia_libre / 20.0))
    tamano_fe = tamano_kelly * factor_fe
    return min(
        tamano_kelly,
        tamano_optimizado,
        limite_defensa,
        tamano_fe,
        limite_exposicion,
    )


def limite_por_riesgo(riesgo_total: float) -> float:
    """Return the allowed position size for the compound risk level."""
    if riesgo_total > 0.9:
        return 0.0
    if riesgo_total > 0.7:
        return 0.02
    return 0.1