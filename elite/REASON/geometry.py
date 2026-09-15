"""Topological market regime from anharmonic structure and gyroscope dynamics."""

from typing import Any, Dict, List

from . import anharmonic, gyroscope


def analyze_geometry(
    precios: List[float],
    umbral_tendencia: float = 0.3,
    umbral_rango: float = 0.6,
) -> Dict[str, Any]:
    """Combine projective structure and short-term dynamics into one signal."""
    if len(precios) < 10:
        return {
            "regimen": "INDEFINIDO",
            "señal_combinada": "lateral",
            "confianza": 0.0,
            "dist_equilibrio_pct": 0.0,
            "punto_equilibrio": 0.0,
            "cr_valor": 0.0,
            "fase_dinamica": "CAOS",
        }

    cr, score_eliptico = anharmonic.analyze(precios)
    giro = gyroscope.gyro_state(precios)
    phase = giro["fase"]

    if phase == "TENDENCIA" and score_eliptico < umbral_tendencia:
        regimen = "HIPERBOLICO"
    elif phase == "RANGO" and score_eliptico > umbral_rango:
        regimen = "ELIPTICO"
    elif (phase == "CAOS" and score_eliptico > 0.4) or (
        phase in ("TENDENCIA", "RANGO")
        and umbral_tendencia <= score_eliptico <= umbral_rango
    ):
        regimen = "PARABOLICO"
    else:
        regimen = "INDEFINIDO"

    dist_cr = abs(cr + 1.0)
    dist_equilibrio_pct = min(1.0, dist_cr / 10.0)
    mean_tail = sum(float(value) for value in precios[-4:]) / 4.0
    punto_equilibrio = float(mean_tail * (1.0 + (-1.0 - cr) / 20.0))

    signal = "lateral"
    if regimen == "HIPERBOLICO":
        if giro["orientacion"] == "ALCISTA":
            signal = "compra"
        elif giro["orientacion"] == "BAJISTA":
            signal = "venta"
    elif regimen == "ELIPTICO":
        if cr < -2.0:
            signal = "venta"
        elif cr > 2.0:
            signal = "compra"
    elif regimen == "PARABOLICO" and giro["confianza"] > 0.8:
        if giro["orientacion"] == "ALCISTA":
            signal = "compra"
        elif giro["orientacion"] == "BAJISTA":
            signal = "venta"

    if regimen == "HIPERBOLICO":
        confidence = giro["confianza"] * (1.0 - score_eliptico)
    elif regimen == "ELIPTICO":
        confidence = giro["confianza"] * score_eliptico
    elif regimen == "PARABOLICO":
        confidence = giro["confianza"] * 0.5
    else:
        confidence = 0.0

    return {
        "regimen": regimen,
        "señal_combinada": signal,
        "confianza": float(max(0.0, min(1.0, confidence))),
        "dist_equilibrio_pct": float(dist_equilibrio_pct),
        "punto_equilibrio": punto_equilibrio,
        "cr_valor": float(cr),
        "score_eliptico": float(score_eliptico),
        "fase_dinamica": phase,
        "orientacion": giro["orientacion"],
    }