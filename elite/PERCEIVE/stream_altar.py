"""Transport-neutral RSX adapter plus an explicit public market-data fetcher.

Only public spot candles are read; this module has no order/trading API.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import math
import os
import re
import time
from typing import Any, Callable
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .data_feeder import write_observation

BINANCE_KLINES_URL = "https://data-api.binance.vision/api/v3/klines"
DEFAULT_SYMBOL = "BTCUSDT"
DEFAULT_LIMIT = 60
MIN_CLOSED_CANDLES = 30


def accept_observation(payload: dict[str, Any], *, writer: Callable = write_observation):
    """Validate and persist one caller-supplied observation."""
    return writer(payload)


def run_once(fetcher: Callable[[], dict[str, Any]], *, writer: Callable = write_observation):
    """Fetch exactly one observation from an explicitly configured provider."""
    payload = fetcher()
    if not isinstance(payload, dict):
        raise ValueError("provider must return a dictionary")
    return writer(payload)


def build_observation_from_klines(
    rows: Any,
    *,
    now_ms: int | None = None,
    symbol: str = DEFAULT_SYMBOL,
) -> dict[str, Any]:
    """Build a validated observation from Binance-shaped kline rows.

    Only candles whose close time has passed are included. Synthetic values are
    never added. The gap and inertia fields are simple return-derived features.
    """
    if not isinstance(rows, list):
        raise ValueError("provider response must be a list of klines")
    current_ms = int(time.time() * 1000) if now_ms is None else int(now_ms)
    closed: list[tuple[int, float, float, int]] = []
    for index, row in enumerate(rows):
        if not isinstance(row, (list, tuple)) or len(row) < 7:
            raise ValueError(f"kline[{index}] has an invalid shape")
        try:
            open_time = int(row[0])
            open_price = float(row[1])
            close_price = float(row[4])
            close_time = int(row[6])
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError(f"kline[{index}] contains invalid values") from exc
        if (
            not math.isfinite(open_price) or open_price <= 0
            or not math.isfinite(close_price) or close_price <= 0
        ):
            raise ValueError(f"kline[{index}] prices must be positive and finite")
        if close_time <= current_ms:
            closed.append((open_time, open_price, close_price, close_time))

    if len(closed) < MIN_CLOSED_CANDLES:
        raise ValueError(
            f"need at least {MIN_CLOSED_CANDLES} closed observed candles; got {len(closed)}"
        )
    open_times = [item[0] for item in closed]
    if open_times != sorted(set(open_times)):
        raise ValueError("provider candles must have unique, ascending open times")

    last_close_time = closed[-1][3]
    age_ms = current_ms - last_close_time
    # With 1-minute candles, a closed candle older than two minutes is stale.
    if age_ms < 0 or age_ms > 120_000:
        raise ValueError(f"latest closed candle is stale ({age_ms} ms old)")

    prices = [item[2] for item in closed]
    previous_close = prices[-2]
    latest_open = closed[-1][1]
    latest_close = prices[-1]
    observed_at = datetime.fromtimestamp(
        last_close_time / 1000, tz=timezone.utc
    ).isoformat()

    return {
        "historial_precios": prices,
        "precio": latest_close,
        "gap": (latest_open / previous_close) - 1.0,
        "inercia": (latest_close / previous_close) - 1.0,
        "source": f"binance_spot_public:{symbol}:1m",
        "observed_at": observed_at,
    }


def fetch_binance_spot_observation(
    symbol: str | None = None,
    *,
    limit: int = DEFAULT_LIMIT,
    timeout: float = 5.0,
    now_ms: int | None = None,
) -> dict[str, Any]:
    """Fetch public BTC/USDT (or configured spot symbol) closed 1-minute candles."""
    chosen_symbol = (symbol or os.getenv("CATEDRALX_MARKET_SYMBOL") or DEFAULT_SYMBOL).upper()
    if not re.fullmatch(r"[A-Z0-9]{5,20}", chosen_symbol):
        raise ValueError("market symbol must contain only 5-20 uppercase letters/digits")
    if isinstance(limit, bool) or not isinstance(limit, int) or not 30 <= limit <= 1000:
        raise ValueError("limit must be an integer from 30 to 1000")
    if not math.isfinite(float(timeout)) or timeout <= 0 or timeout > 20:
        raise ValueError("timeout must be greater than 0 and at most 20 seconds")

    query = urlencode({"symbol": chosen_symbol, "interval": "1m", "limit": limit})
    request = Request(
        f"{BINANCE_KLINES_URL}?{query}",
        headers={"Accept": "application/json", "User-Agent": "CatedralX-RSX/1.0"},
        method="GET",
    )
    with urlopen(request, timeout=float(timeout)) as response:
        if getattr(response, "status", 200) != 200:
            raise RuntimeError(f"market provider returned HTTP {response.status}")
        raw = response.read(2_000_000)
    try:
        rows = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("market provider returned invalid JSON") from exc
    observation = build_observation_from_klines(
        rows, now_ms=now_ms, symbol=chosen_symbol
    )
    return observation
