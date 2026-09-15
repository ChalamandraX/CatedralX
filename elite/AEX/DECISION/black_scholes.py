"""Black-Scholes option pricing and implied-volatility utilities."""

import math


def _normal_cdf(value: float) -> float:
    return 0.5 * (1.0 + math.erf(value / math.sqrt(2.0)))


def _normal_pdf(value: float) -> float:
    return math.exp(-0.5 * value**2) / math.sqrt(2.0 * math.pi)


def black_scholes_price(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    option_type: str = "call",
) -> float:
    """Return the Black-Scholes price for a European call or put."""
    if S <= 0.0 or K <= 0.0:
        raise ValueError("S and K must be positive")
    if option_type not in {"call", "put"}:
        raise ValueError("option_type must be 'call' or 'put'")
    if T < 0.0 or sigma < 0.0:
        raise ValueError("T and sigma must be non-negative")

    discount = math.exp(-r * T)
    if T <= 1e-5 or sigma <= 1e-5:
        if option_type == "call":
            return max(0.0, S - K * discount)
        return max(0.0, K * discount - S)

    d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    if option_type == "call":
        return float(S * _normal_cdf(d1) - K * discount * _normal_cdf(d2))
    return float(K * discount * _normal_cdf(-d2) - S * _normal_cdf(-d1))


def black_scholes_greeks(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    option_type: str = "call",
) -> dict[str, float]:
    """Return delta, gamma, theta and per-percent vega for a European option."""
    if S <= 0.0 or K <= 0.0:
        raise ValueError("S and K must be positive")
    if T < 0.0 or sigma < 0.0:
        raise ValueError("T and sigma must be non-negative")
    if option_type not in {"call", "put"}:
        raise ValueError("option_type must be 'call' or 'put'")
    if T <= 1e-5 or sigma <= 1e-5:
        forward = S - K * math.exp(-r * T)
        delta = 1.0 if forward > 0.0 else -1.0 if forward < 0.0 else 0.0
        if option_type == "put":
            delta -= 1.0
        return {"delta": delta, "gamma": 0.0, "theta": 0.0, "vega": 0.0}

    sqrt_time = math.sqrt(T)
    d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * sqrt_time)
    d2 = d1 - sigma * sqrt_time
    pdf_d1 = _normal_pdf(d1)
    gamma = pdf_d1 / (S * sigma * sqrt_time)
    vega = S * pdf_d1 * sqrt_time / 100.0
    if option_type == "call":
        delta = _normal_cdf(d1)
        theta = -(S * pdf_d1 * sigma) / (2.0 * sqrt_time) - r * K * math.exp(-r * T) * _normal_cdf(d2)
    else:
        delta = _normal_cdf(d1) - 1.0
        theta = -(S * pdf_d1 * sigma) / (2.0 * sqrt_time) + r * K * math.exp(-r * T) * _normal_cdf(-d2)
    return {"delta": delta, "gamma": gamma, "theta": theta, "vega": vega}


def implied_volatility(
    market_price: float,
    S: float,
    K: float,
    T: float,
    r: float,
    option_type: str = "call",
) -> float:
    """Solve for volatility using a bounded bisection search in ``[1e-5, 5]``."""
    if market_price < 0.0:
        raise ValueError("market_price must be non-negative")

    intrinsic_value = black_scholes_price(S, K, T, r, 0.0, option_type)
    upper_bound = S if option_type == "call" else K * math.exp(-r * T)
    if market_price <= intrinsic_value or market_price > upper_bound:
        return 0.0

    lower_sigma, upper_sigma = 1e-5, 5.0
    lower_error = black_scholes_price(S, K, T, r, lower_sigma, option_type) - market_price
    upper_error = black_scholes_price(S, K, T, r, upper_sigma, option_type) - market_price
    if lower_error * upper_error > 0.0:
        return 0.0

    for _ in range(100):
        middle_sigma = (lower_sigma + upper_sigma) / 2.0
        middle_error = black_scholes_price(S, K, T, r, middle_sigma, option_type) - market_price
        if abs(middle_error) < 1e-6 or upper_sigma - lower_sigma < 1e-6:
            return float(middle_sigma)
        if lower_error * middle_error <= 0.0:
            upper_sigma, upper_error = middle_sigma, middle_error
        else:
            lower_sigma, lower_error = middle_sigma, middle_error
    return float((lower_sigma + upper_sigma) / 2.0)