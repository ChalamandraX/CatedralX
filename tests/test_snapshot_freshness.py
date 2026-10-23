"""Tests for market-observation freshness; file mtime is not market time."""

import json
import os
import time
import pytest
from datetime import datetime, timezone

from PERCEIVE.api_pulse import check_snapshot, validate_snapshot_payload


def make_snapshot(observed_at, count=30):
    prices = [100.0 + index for index in range(count)]
    return {
        "PERCEIVE": {
            "historial_precios": prices,
            "precio": prices[-1],
            "source": "test",
            "observed_at": observed_at,
        }
    }


def iso_time(epoch):
    return datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat()


def test_rejects_old_observations_even_when_file_is_recent(tmp_path):
    now = 2_000_000_000.0
    path = tmp_path / "snapshot.json"
    path.write_text(
        json.dumps(make_snapshot(iso_time(now - 300))),
        encoding="utf-8",
    )
    os.utime(path, (now, now))

    result = check_snapshot(path, max_age_seconds=120, now=now)

    assert result["healthy"] is False
    assert result["reason"] == "stale_observation"


def test_uses_market_timestamp_even_when_file_mtime_is_old(tmp_path):
    now = 2_000_000_000.0
    path = tmp_path / "snapshot.json"
    path.write_text(
        json.dumps(make_snapshot(iso_time(now - 30))),
        encoding="utf-8",
    )
    os.utime(path, (now - 600, now - 600))

    result = check_snapshot(path, max_age_seconds=120, now=now)

    assert result["healthy"] is True
    assert result["age_seconds"] == 30


def test_rejects_missing_observation_timestamp():
    result = validate_snapshot_payload(
        make_snapshot(None),
        max_age_seconds=120,
        now=2_000_000_000,
    )

    assert result["healthy"] is False
    assert result["reason"] == "missing_observed_at"


def test_rejects_history_with_fewer_than_30_prices():
    result = validate_snapshot_payload(
        make_snapshot(iso_time(2_000_000_000 - 10), count=29),
        max_age_seconds=120,
        now=2_000_000_000,
    )

    assert result["healthy"] is False
    assert result["reason"] == "insufficient_price_history"


def test_rejects_timezone_free_observation_timestamp():
    result = validate_snapshot_payload(
        make_snapshot("2033-05-18T03:33:10"),
        max_age_seconds=120,
        now=2_000_000_000,
    )

    assert result["healthy"] is False
    assert result["reason"] == "observed_at_requires_timezone"


def test_rejects_observation_timestamp_too_far_in_future():
    now = 2_000_000_000.0
    result = validate_snapshot_payload(
        make_snapshot(iso_time(now + 60)),
        max_age_seconds=120,
        now=now,
    )

    assert result["healthy"] is False
    assert result["reason"] == "observation_from_future"


def test_reason_entry_point_refuses_stale_snapshot(tmp_path, monkeypatch, capsys):
    from REASON import razon

    snapshot_path = tmp_path / "stale_reason.json"
    snapshot_path.write_text(
        json.dumps(make_snapshot(iso_time(time.time() - 300))),
        encoding="utf-8",
    )
    monkeypatch.setenv("CATEDRALX_SNAPSHOT_PATH", str(snapshot_path))

    def forbidden_cycle(_sensory):
        pytest.fail("El motor no debe ejecutar un ciclo con datos caducados")

    monkeypatch.setattr(razon, "execute_cycle", forbidden_cycle)

    return_code = razon.main()
    output = json.loads(capsys.readouterr().out)

    assert return_code == 2
    assert output["status"] == "NO_CYCLE"
    assert "stale_observation" in output["reason"]
    assert output["trading_enabled"] is False
    assert output["orders_executed"] is False


def test_bunker_cycle_refuses_stale_snapshot(tmp_path, monkeypatch):
    from PERCEIVE import bunker

    snapshot_path = tmp_path / "stale_bunker.json"
    snapshot_path.write_text(
        json.dumps(make_snapshot(iso_time(time.time() - 300))),
        encoding="utf-8",
    )
    monkeypatch.setattr(bunker, "SNAPSHOT_PATH", snapshot_path)
    monkeypatch.setattr(
        bunker,
        "execute_cycle",
        lambda _sensory: pytest.fail(
            "El daemon no debe ejecutar un ciclo con datos caducados"
        ),
    )

    daemon = object.__new__(bunker.BunkerDaemon)

    with pytest.raises(ValueError, match="stale_observation"):
        daemon._ciclo()


def test_bunker_uses_shared_cycle_without_overwriting_snapshot(
    tmp_path, monkeypatch
):
    from types import SimpleNamespace
    from PERCEIVE import bunker

    snapshot_path = tmp_path / "fresh_bunker.json"
    snapshot_path.write_text(
        json.dumps(make_snapshot(iso_time(time.time()))),
        encoding="utf-8",
    )
    original_bytes = snapshot_path.read_bytes()
    monkeypatch.setattr(bunker, "SNAPSHOT_PATH", snapshot_path)

    sensory = SimpleNamespace(precio_actual=129.0)
    state = SimpleNamespace(
        decision="hold",
        confianza=0.42,
        regimen="SIDEWAYS",
        free_energy=0.1,
        hamiltoniano=0.2,
        energia_cognitiva=0.3,
        giroscopio={},
        razon_anarmonica={},
        percepcion_espacial={
            "hurst": 0.5,
            "analisis_financiero": {"signal": "hold"},
        },
    )
    setattr(state, "señal_combinada", "lateral")

    calls = []
    monkeypatch.setattr(
        bunker,
        "execute_cycle",
        lambda item: calls.append(item) or state,
    )

    daemon = object.__new__(bunker.BunkerDaemon)
    monkeypatch.setattr(
        daemon, "_construir_entrada", lambda _snapshot: sensory
    )

    result = daemon._ciclo()

    assert calls == [sensory]
    assert result["REASON"]["decision"] == "hold"
    assert snapshot_path.read_bytes() == original_bytes
