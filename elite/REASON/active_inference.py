"""Active-inference engine for market return surprise and free energy."""

from typing import List, Tuple

import numpy as np


class ActiveInferenceEngine:
    """Measure divergence between the market posterior and an adaptive prior."""

    def __init__(self) -> None:
        self.mu_p = 0.0
        self.sigma_p = 0.01

    def inferir(
        self,
        retornos_recientes: List[float],
        precio_actual: float,
        precio_previo: float,
    ) -> Tuple[float, float]:
        """Return KL divergence and variational free energy for recent returns."""
        if len(retornos_recientes) < 2 or precio_actual <= 0.0 or precio_previo <= 0.0:
            return 0.0, 0.0

        returns = np.asarray(retornos_recientes, dtype=float)
        if returns.ndim != 1 or not np.all(np.isfinite(returns)):
            return 0.0, 0.0

        mu_q = float(np.mean(returns))
        sigma_q = float(np.std(returns)) + 1e-8
        var_q = sigma_q**2
        var_p = self.sigma_p**2
        d_kl = 0.5 * (np.log(var_p / var_q) + (var_q + (mu_q - self.mu_p) ** 2) / var_p - 1.0)

        ultimo_retorno = float(np.log(precio_actual / (precio_previo + 1e-8)))
        z_score = (ultimo_retorno - self.mu_p) / self.sigma_p
        sorpresa = 0.5 * (z_score**2 + np.log(2.0 * np.pi * var_p))
        fe_var = max(0.0, float(d_kl + sorpresa))

        self.mu_p = 0.95 * self.mu_p + 0.05 * mu_q
        self.sigma_p = 0.95 * self.sigma_p + 0.05 * sigma_q
        return float(d_kl), float(fe_var)


engine = ActiveInferenceEngine()