"""Regression tests for CatedralX shared execution and state paths."""

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest


def _iso(epoch):
    return datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat()


def _snapshot(observed_at):
    prices = [100.0 + index for index in range(30)]
    return {
        "PERCEIVE": {
            "historial_precios": prices,
            "precio": prices[-1],
            "gap": 0.0,
            "inercia": 0.0,
            "source": "test",
            "observed_at": observed_at,
        }
    }


def _fake_state():
    return SimpleNamespace(
        decision="hold",
        percepcion_espacial={"hurst": 0.5},
    )


def test_canonical_state_path_is_configurable_and_rejects_repo_paths(
    tmp_path, monkeypatch
):
    from REASON.state_paths import canonical_state_path

    external = tmp_path / "state" / "hormonas.json"
    monkeypatch.setenv("CATEDRALX_STATE_PATH", str(external))
    assert canonical_state_path() == external.resolve()

    repo_root = Path(__file__).resolve().parents[1]
    inside_repo = repo_root / "03-OUTPUT" / "hormonas.json"
    monkeypatch.setenv("CATEDRALX_STATE_PATH", str(inside_repo))

    with pytest.raises(ValueError, match="fuera del repositorio"):
        canonical_state_path()


def test_orchestrator_loop_uses_shared_cycle_and_keeps_snapshot_read_only(
    tmp_path, monkeypatch
):
    from REASON import orchestrator

    path = tmp_path / "input.json"
    path.write_text(json.dumps(_snapshot(_iso(time.time()))), encoding="utf-8")
    original_bytes = path.read_bytes()
    monkeypatch.setattr(orchestrator, "SNAPSHOT_PATH", path)

    calls = []
    state = _fake_state()
    monkeypatch.setattr(
        orchestrator,
        "execute_cycle",
        lambda sensory: calls.append(sensory) or state,
    )

    instance = object.__new__(orchestrator.Orchestrator)
    instance.ultimo_fe = 0.0

    class StopLoop(BaseException):
        pass

    monkeypatch.setattr(
        orchestrator.time,
        "sleep",
        lambda _seconds: (_ for _ in ()).throw(StopLoop()),
    )

    with pytest.raises(StopLoop):
        instance.bucle_infinito()

    assert len(calls) == 1
    assert path.read_bytes() == original_bytes


def test_orchestrator_loop_rejects_stale_snapshot(tmp_path, monkeypatch):
    from REASON import orchestrator

    path = tmp_path / "stale_input.json"
    path.write_text(
        json.dumps(_snapshot(_iso(time.time() - 300))),
        encoding="utf-8",
    )
    original_bytes = path.read_bytes()
    monkeypatch.setattr(orchestrator, "SNAPSHOT_PATH", path)

    monkeypatch.setattr(
        orchestrator,
        "execute_cycle",
        lambda _sensory: pytest.fail(
            "El bucle no debe ejecutar un ciclo con datos caducados"
        ),
    )

    instance = object.__new__(orchestrator.Orchestrator)
    instance.ultimo_fe = 0.0

    class StopLoop(BaseException):
        pass

    monkeypatch.setattr(
        orchestrator.time,
        "sleep",
        lambda _seconds: (_ for _ in ()).throw(StopLoop()),
    )

    with pytest.raises(StopLoop):
        instance.bucle_infinito()

    assert path.read_bytes() == original_bytes


def test_orchestrator_uses_the_configured_canonical_state_path(
    tmp_path, monkeypatch
):
    from REASON.orchestrator import Orchestrator
    from REASON.state_paths import canonical_state_path

    configured = tmp_path / "canonical" / "hormonas.json"
    monkeypatch.setenv("CATEDRALX_STATE_PATH", str(configured))

    instance = Orchestrator()

    assert canonical_state_path() == configured.resolve()
    assert instance.transductor.output_path == configured.resolve()


def test_transductor_default_path_resolves_environment_when_constructed(
    tmp_path, monkeypatch
):
    from REASON.procesador import ProcesadorEndocrino

    configured = tmp_path / "dynamic-state" / "hormonas.json"
    monkeypatch.setenv("CATEDRALX_STATE_PATH", str(configured))

    instance = ProcesadorEndocrino()

    assert instance.output_path == configured.resolve()


def test_legacy_integrated_function_delegates_to_shared_transductor(
    monkeypatch
):
    import importlib
    from types import SimpleNamespace
    from REASON import orchestrator

    processor_module = importlib.import_module("REASON.procesador")
    payload = {"contexto": {"decision_financiera": "hold"}}
    calls = []
    expected_state = {"contexto": {"decision_financiera": "hold"}}

    class FakeTransductor:
        def volcar_estado_quimico(self, supplied):
            calls.append(supplied)

        def leer_estado_actual(self):
            return expected_state

    monkeypatch.setattr(
        orchestrator,
        "_think_orchestrator",
        SimpleNamespace(transductor=FakeTransductor()),
    )

    result = processor_module.procesar_estado_integrado(payload)

    assert calls == [payload]
    assert result is expected_state


def test_transductor_guardar_writes_json_and_cleans_temp(tmp_path):
    import json
    from REASON.procesador import ProcesadorEndocrino

    target = tmp_path / "nested" / "hormonas.json"
    transductor = ProcesadorEndocrino(output_path=target)

    saved = transductor.guardar()

    assert target.exists()
    assert json.loads(target.read_text(encoding="utf-8")) == saved
    assert list(target.parent.glob(f".{target.name}.*.tmp")) == []
