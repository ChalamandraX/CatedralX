"""Deterministic, analysis-only financial layer for CatedralX.

This module computes descriptive price/return statistics and a conservative
momentum classification. The classification is a heuristic, not a calibrated
probability or a trading instruction. It never places or simulates orders.
"""
from __future__ import annotations

import math
import statistics
from collections.abc import Sequence
from typing import Any

MIN_OBSERVATIONS = 30
SHORT_WINDOW = 5
MEDIUM_WINDOW = 20
VOLATILITY_WINDOW = 10


def analyze_financial_market(prices: Sequence[float]) -> dict[str, Any]:
    """Return validated market diagnostics and a deterministic momentum label.

    Prices must be positive finite observations in chronological order. Their
    sampling interval is intentionally unspecified; no annualization is done.
    The result is suitable for analysis and review only, never for execution.
    """
    if isinstance(prices, (str, bytes)):
        raise ValueError("prices debe ser una secuencia numérica, no texto.")
    try:
        values = list(prices)
    except TypeError as exc:
        raise ValueError("prices debe ser una secuencia de precios.") from exc
    if len(values) < MIN_OBSERVATIONS:
        raise ValueError(
            f"Se requieren al menos {MIN_OBSERVATIONS} observaciones; se recibieron {len(values)}."
        )

    checked: list[float] = []
    for index, value in enumerate(values):
        if isinstance(value, bool):
            raise ValueError(f"prices[{index}] debe ser positivo y finito.")
        try:
            price = float(value)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError(f"prices[{index}] debe ser positivo y finito.") from exc
        if not math.isfinite(price) or price <= 0:
            raise ValueError(f"prices[{index}] debe ser positivo y finito.")
        checked.append(price)

    log_returns = [math.log(current / prior) for prior, current in zip(checked, checked[1:])]
    if not all(math.isfinite(value) for value in log_returns):
        raise ValueError("La serie produjo rendimientos no finitos.")

    sigma = statistics.pstdev(log_returns) if log_returns else 0.0
    recent_returns = log_returns[-VOLATILITY_WINDOW:]
    baseline_returns = log_returns[:-VOLATILITY_WINDOW]
    recent_volatility = statistics.pstdev(recent_returns) if recent_returns else 0.0
    baseline_volatility = statistics.pstdev(baseline_returns) if baseline_returns else 0.0
    volatility_expansion = (
        recent_volatility > 1e-12
        and (
            baseline_volatility <= 1e-12
            or recent_volatility >= 2.0 * baseline_volatility
        )
    )

    short_return = sum(log_returns[-SHORT_WINDOW:])
    medium_return = sum(log_returns[-MEDIUM_WINDOW:])
    short_scale = max(sigma * math.sqrt(SHORT_WINDOW), 1e-12)
    medium_scale = max(sigma * math.sqrt(MEDIUM_WINDOW), 1e-12)
    # Saturating scores stay interpretable and bounded when observed volatility
    # is numerically close to zero (e.g. synthetic perfect-trend test series).
    short_score = math.tanh(short_return / short_scale)
    medium_score = math.tanh(medium_return / medium_scale)
    combined_score = 0.4 * short_score + 0.6 * medium_score

    proposed_signal = "hold"
    reason = "El impulso corto y medio no confirma una misma dirección."
    if short_score >= 0.5 and medium_score >= 0.5:
        proposed_signal = "buy"
        reason = "Impulso corto y medio alineado al alza; señal heurística para revisión."
    elif short_score <= -0.5 and medium_score <= -0.5:
        proposed_signal = "sell"
        reason = "Impulso corto y medio alineado a la baja; señal heurística para revisión."

    risk_flags: list[str] = []
    signal = proposed_signal
    if volatility_expansion:
        risk_flags.append("volatility_expansion")
        if proposed_signal in {"buy", "sell"}:
            signal = "hold"
            reason = (
                "Se bloqueó la etiqueta direccional: la volatilidad reciente es al menos "
                "el doble de la volatilidad de referencia."
            )

    if signal == "buy":
        regime = "TREND_ALCISTA"
        combined_signal = "compra"
    elif signal == "sell":
        regime = "TREND_BAJISTA"
        combined_signal = "venta"
    elif volatility_expansion:
        regime = "VOLATILIDAD_EN_EXPANSION"
        combined_signal = "lateral"
    else:
        regime = "INDEFINIDO"
        combined_signal = "lateral"

    peak = checked[0]
    max_drawdown = 0.0
    for price in checked:
        peak = max(peak, price)
        if peak > 0:
            max_drawdown = min(max_drawdown, price / peak - 1.0)

    short_sma = statistics.fmean(checked[-SHORT_WINDOW:])
    medium_sma = statistics.fmean(checked[-MEDIUM_WINDOW:])
    long_sma = statistics.fmean(checked[-min(60, len(checked)):])
    strength = abs(combined_score) if signal in {"buy", "sell"} else 0.0

    return {
        "signal": signal,
        "proposed_signal_before_risk_gate": proposed_signal,
        "combined_signal": combined_signal,
        "regime": regime,
        "signal_strength": round(strength, 6),
        "signal_strength_is_probability": False,
        "decision_reason": reason,
        "risk_flags": risk_flags,
        "observations": len(checked),
        "latest_price": checked[-1],
        "cumulative_return_pct": round((checked[-1] / checked[0] - 1.0) * 100.0, 6),
        "latest_return_pct": round((math.exp(log_returns[-1]) - 1.0) * 100.0, 6),
        "realized_volatility_per_observation": round(sigma, 10),
        "recent_volatility_per_observation": round(recent_volatility, 10),
        "baseline_volatility_per_observation": round(baseline_volatility, 10),
        "volatility_expansion": volatility_expansion,
        "max_drawdown_pct": round(max_drawdown * 100.0, 6),
        "moving_averages": {
            "short_5": round(short_sma, 10),
            "medium_20": round(medium_sma, 10),
            "long_up_to_60": round(long_sma, 10),
        },
        "momentum_scores": {
            "short_5": round(short_score, 6),
            "medium_20": round(medium_score, 6),
            "combined": round(combined_score, 6),
        },
        "analysis_only": True,
        "trading_enabled": False,
        "orders_created": False,
        "orders_executed": False,
    }
