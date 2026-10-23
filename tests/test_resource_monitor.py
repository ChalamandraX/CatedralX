"""Regression tests for CatedralX resource monitoring and defense."""

from types import SimpleNamespace

import pytest

from DSX.DEFENSE import defense, guardian_ram


def test_resource_readings_and_available_memory(monkeypatch):
    monkeypatch.setattr(
        guardian_ram.psutil,
        "virtual_memory",
        lambda: SimpleNamespace(percent=42.5, available=256 * 1024**2),
    )

    cpu_intervals = []

    def fake_cpu_percent(interval):
        cpu_intervals.append(interval)
        return 12.5

    monkeypatch.setattr(guardian_ram.psutil, "cpu_percent", fake_cpu_percent)

    assert guardian_ram.uso_ram_porcentaje() == 42.5
    assert guardian_ram.uso_cpu_porcentaje() == 12.5
    assert cpu_intervals == [0.1]
    assert guardian_ram.memoria_disponible_mb() == 256.0


def test_resource_gate_allows_usage_below_thresholds(monkeypatch):
    monkeypatch.setattr(guardian_ram, "uso_ram_porcentaje", lambda: 84.9)
    monkeypatch.setattr(guardian_ram, "uso_cpu_porcentaje", lambda: 89.9)

    assert guardian_ram.hay_suficiente_recurso() is True


@pytest.mark.parametrize(
    ("ram", "cpu", "expected"),
    [
        (85.0, 20.0, False),
        (20.0, 90.0, False),
        (85.1, 90.1, False),
        (84.9, 89.9, True),
    ],
)
def test_resource_gate_respects_thresholds(monkeypatch, ram, cpu, expected):
    monkeypatch.setattr(guardian_ram, "uso_ram_porcentaje", lambda: ram)
    monkeypatch.setattr(guardian_ram, "uso_cpu_porcentaje", lambda: cpu)

    assert guardian_ram.hay_suficiente_recurso() is expected


@pytest.mark.parametrize(
    ("usage", "expected"),
    [
        (0.0, 0.0),
        (45.0, 0.5),
        (90.0, 1.0),
        (100.0, 1.0),
        (120.0, 1.0),
        (-5.0, 0.0),
    ],
)
def test_ram_risk_is_normalized_and_clamped(monkeypatch, usage, expected):
    monkeypatch.setattr(
        defense.psutil,
        "virtual_memory",
        lambda: SimpleNamespace(percent=usage),
    )

    assert defense.riesgo_ram_monitor() == pytest.approx(expected)


def test_compound_risk_uses_configured_weights():
    assert defense.riesgo_compuesto(0.2, 0.8) == pytest.approx(0.47)


def test_bunker_uses_the_required_resource_monitor():
    from PERCEIVE import bunker

    assert bunker.hay_suficiente_recurso is guardian_ram.hay_suficiente_recurso
