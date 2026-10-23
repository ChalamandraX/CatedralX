#!/usr/bin/env python3
"""Fetch one public market-data snapshot into RSX; never submits orders."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ELITE_DIR = Path(__file__).resolve().parents[1]
if str(ELITE_DIR) not in sys.path:
    sys.path.insert(0, str(ELITE_DIR))

from PERCEIVE.data_feeder import snapshot_path, write_observation
from PERCEIVE.stream_altar import fetch_binance_spot_observation


def main() -> int:
    try:
        observation = fetch_binance_spot_observation()
        target = write_observation(observation)
        result = {
            "status": "FEED_UPDATED",
            "snapshot_path": str(target),
            "symbol": observation["source"].split(":")[1],
            "interval": "1m",
            "observed_candles": len(observation["historial_precios"]),
            "price": observation["precio"],
            "source": observation["source"],
            "observed_at": observation["observed_at"],
            "trading_enabled": False,
            "orders_created": False,
            "orders_executed": False,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        return 0
    except Exception as exc:
        print(json.dumps({
            "status": "FEED_ERROR",
            "error_type": type(exc).__name__,
            "reason": str(exc),
            "snapshot_path": str(snapshot_path()),
            "trading_enabled": False,
            "orders_created": False,
            "orders_executed": False,
        }, ensure_ascii=False, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
