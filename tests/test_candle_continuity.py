"""Regression tests for contiguous one-minute market candles."""

import pytest

from PERCEIVE.stream_altar import build_observation_from_klines


def make_rows(count=31, missing_index=None):
    base = 1_900_000_000_000
    rows = []

    for index in range(count):
        if index == missing_index:
            continue

        open_time = base + index * 60_000
        price = 100.0 + index
        close_time = open_time + 59_999

        rows.append([
            open_time,
            str(price),
            str(price + 1),
            str(price - 1),
            str(price + 0.5),
            "10",
            close_time,
        ])

    return rows, rows[-1][6]


def test_accepts_contiguous_closed_one_minute_candles():
    rows, now_ms = make_rows()

    observation = build_observation_from_klines(rows, now_ms=now_ms)

    assert len(observation["historial_precios"]) == 31
    assert observation["observed_at"].endswith("+00:00")


def test_rejects_missing_minute_even_with_enough_fresh_candles():
    rows, now_ms = make_rows(count=31, missing_index=10)

    # Thirty candles remain and the latest candle is fresh; the missing minute
    # must still make the input invalid.
    assert len(rows) == 30

    with pytest.raises(ValueError, match="contiguous 1-minute intervals"):
        build_observation_from_klines(rows, now_ms=now_ms)
