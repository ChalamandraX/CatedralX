"""Estimador del exponente de Hurst mediante analisis R/S."""

from typing import List, Union

import numpy as np

SerieNumerica = Union[List[float], np.ndarray]


def calcular_hurst(serie: SerieNumerica) -> float:
    """Calcula H sobre los retornos logaritmicos de una serie de precios."""
    try:
        precios = np.asarray(serie, dtype=np.float64)
    except (TypeError, ValueError):
        return 0.5

    if precios.ndim != 1 or precios.size < 20 or not np.all(np.isfinite(precios)):
        return 0.5
    if np.any(precios <= 0.0):
        return 0.5

    retornos = np.diff(np.log(precios))
    desviacion = float(np.std(retornos))
    if retornos.size < 2 or desviacion < 1e-10:
        return 0.5

    desviaciones_acumuladas = np.cumsum(retornos - np.mean(retornos))
    rango = float(np.ptp(desviaciones_acumuladas))
    if rango <= 0.0:
        return 0.5

    hurst = np.log(rango / desviacion) / np.log(retornos.size)
    return float(np.clip(hurst, 0.0, 1.0))


def hurst_exponent(precios: SerieNumerica, max_lag: int = 10) -> float:
    """Alias compatible con los consumidores existentes del repositorio."""
    del max_lag
    return calcular_hurst(precios)


class HurstAnalyzer:
    """Analizador de Hurst con una ventana de precios configurable."""

    def __init__(self, ventana: int = 168) -> None:
        self.ventana = max(20, int(ventana))

    def calcular(self, serie: SerieNumerica) -> float:
        """Calcula H usando como maximo los ultimos ``ventana`` puntos."""
        try:
            precios = np.asarray(serie, dtype=np.float64)
        except (TypeError, ValueError):
            return 0.5
        if precios.ndim != 1 or precios.size == 0:
            return 0.5
        return calcular_hurst(precios[-self.ventana :])

    def compute(self, serie: SerieNumerica) -> float:
        """Alias en ingles para compatibilidad."""
        return self.calcular(serie)

    def tendencia_hurst(self, serie: SerieNumerica, window_meta: int = 5) -> str:
        """Describe si H aumenta o disminuye entre ventanas consecutivas."""
        if window_meta < 2:
            return "indeterminado"
        try:
            precios = np.asarray(serie, dtype=np.float64)
        except (TypeError, ValueError):
            return "indeterminado"

        required = self.ventana * window_meta
        if precios.ndim != 1 or precios.size < required:
            return "indeterminado"

        valores = [
            calcular_hurst(precios[index - self.ventana : index])
            for index in range(self.ventana, precios.size + 1, self.ventana)
        ]
        if len(valores) < 2:
            return "indeterminado"

        diferencia = valores[-1] - valores[0]
        if diferencia > 0.08:
            return "fortaleciendo_tendencia"
        if diferencia < -0.08:
            return "debilitando_tendencia"
        return "estable"

    def __repr__(self) -> str:
        return f"HurstAnalyzer(ventana={self.ventana})"


if __name__ == "__main__":
    import sys

    precios = [float(value) for value in sys.argv[1:]]
    if not precios:
        np.random.seed(42)
        precios = (65000.0 + np.cumsum(np.random.randn(200) * 50)).tolist()
    print(f"Hurst: {HurstAnalyzer(ventana=120).calcular(precios):.4f}")