"""The only external Job Intelligence entry point is a closed development run."""

import asyncio
import importlib
import json
import os
import subprocess
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest


def run_script(script: str, *arguments: str) -> subprocess.CompletedProcess[str]:
    environment = dict(os.environ)
    environment.pop("ACTUAL_MODEL_MODE", None)
    root = Path(__file__).resolve().parents[2]
    return subprocess.run(
        [sys.executable, str(root / "scripts" / script), *arguments],
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
        timeout=15,
    )


def test_runner_rejects_arbitrary_prompt_or_file_before_provider_configuration() -> None:
    result = run_script("evaluate_phase6_live.py", "private-career-material.json")
    assert result.returncode == 2
    assert result.stdout.strip() == ('{"evaluation":"failed","error_code":"unsupported_arguments"}')
    assert result.stderr == ""


def test_old_rejected_runner_never_silently_runs_a_new_capability() -> None:
    result = run_script("evaluate_phase6_live.py")
    assert result.returncode == 1
    assert json.loads(result.stdout) == {
        "error_code": "rejected_phase6_runner",
        "evaluation": "failed",
    }
    assert result.stderr == ""


def test_hardening_runner_requires_explicit_synthetic_mode_without_stack_trace() -> None:
    result = run_script("evaluate_phase6a_live.py")
    assert result.returncode == 1
    assert json.loads(result.stdout) == {"error_code": "configuration", "evaluation": "failed"}
    assert result.stderr == ""


def test_hardening_runner_rejects_arbitrary_intake_before_configuration() -> None:
    result = run_script("evaluate_phase6a_live.py", "private-career-material.json")
    assert result.returncode == 2
    assert json.loads(result.stdout) == {
        "error_code": "unsupported_arguments",
        "evaluation": "failed",
    }
    assert result.stderr == ""


@pytest.fixture
def hardening_helper(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / "scripts"))
    return importlib.import_module("evaluate_phase6a_live")


@pytest.mark.parametrize("failure", ["cleanup", "cancellation"])
def test_partial_runner_finalizes_no_go_after_cleanup_or_cancellation_without_inference(
    failure: str,
    hardening_helper: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    helper = hardening_helper
    # Only existing observable fixtures are loaded. No model transport or process
    # runs; temporary reports cannot be confused with genuine acceptance evidence.
    selected = helper.cases()
    safety_inputs = helper.fixed_inputs("safety-inputs-v1.json")
    monkeypatch.setattr(helper, "ROOT", tmp_path)
    monkeypatch.setattr(helper, "cases", lambda: selected)
    monkeypatch.setattr(helper, "fixed_inputs", lambda name: safety_inputs)
    monkeypatch.setattr(helper, "frozen_sources", lambda: {"synthetic-source.py": "a" * 64})
    monkeypatch.setattr(helper.shutil, "which", lambda executable: "owned-fake-ollama.exe")
    monkeypatch.setattr(helper, "server_environment", lambda port: {})
    monkeypatch.setattr(
        helper.OllamaSettings, "from_environment", staticmethod(lambda: helper.OllamaSettings())
    )
    handle = SimpleNamespace(pid=23456, poll=lambda: None)
    monkeypatch.setattr(helper.subprocess, "Popen", lambda *args, **kwargs: handle)
    monkeypatch.setattr(
        helper.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0,
            stdout=json.dumps({"LocalAddress": "127.0.0.1", "OwningProcess": handle.pid}),
        ),
    )

    class FakeClient:
        def __init__(self, **kwargs: object) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args: object) -> None:
            pass

        async def get(self, url: str) -> SimpleNamespace:
            return SimpleNamespace(status_code=200, json=lambda: {"cloud": {"disabled": True}})

    monkeypatch.setattr(helper.httpx, "AsyncClient", FakeClient)

    async def no_inference(*args: object) -> None:
        if failure == "cancellation":
            raise asyncio.CancelledError

    async def observation(process_id: int, stopped: asyncio.Event) -> int:
        await stopped.wait()
        return 1

    cleaned = []

    def cleanup(owned: object) -> None:
        assert owned is handle
        cleaned.append(owned)
        if failure == "cleanup":
            raise RuntimeError("owned_server_cleanup_failed")

    monkeypatch.setattr(helper, "run_trials", no_inference)
    monkeypatch.setattr(helper, "observe_network", observation)
    monkeypatch.setattr(helper, "cleanup_owned_server", cleanup)
    assert asyncio.run(helper.verify()) is False
    assert cleaned == [handle]
    report_path = next((tmp_path / "evaluation-runs").glob("*.report.json"))
    report = json.loads(report_path.read_bytes())
    assert report["verdict"] == "NO_GO"
    assert report["attempted_calls"] == 0
    expected = "owned_server_cleanup_failed" if failure == "cleanup" else "cancelled_by_supervision"
    assert report["evaluation_abort_code"] == expected
    checkpoint = json.loads(
        next((tmp_path / "evaluation-runs").glob("*.checkpoint.json")).read_bytes()
    )
    assert checkpoint["status"] == "aborted"
    assert checkpoint["abort_code"] == expected


@pytest.mark.parametrize("abort_code", ["owned_server_cleanup_failed", "cancelled_by_supervision"])
def test_runner_abort_prevents_go_even_when_every_other_quality_gate_passes(
    abort_code: str,
    hardening_helper: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    helper = hardening_helper
    monkeypatch.setattr(helper, "frozen_sources", lambda: {"source.py": "b" * 64})
    finalized = []
    journal = SimpleNamespace(
        frozen_sources=helper.frozen_sources(),
        finalize=lambda reason: finalized.append(reason),
        attempts=[{"gateway_schema_valid": True}] * 87,
        configuration={"provider": "fake", "model": "synthetic-test-double"},
        records=[],
    )
    monkeypatch.setattr(helper, "gold_cases", lambda selected: ())
    monkeypatch.setattr(helper, "safety_check", lambda base: {})
    monkeypatch.setattr(helper, "component_check", lambda *args: {})
    monkeypatch.setattr(helper, "evaluate_results", lambda *args: {})
    monkeypatch.setattr(helper, "quality_gates", lambda *args: {"otherwise_passing": True})
    report = helper.build_report(
        journal, (SimpleNamespace(case_id="synthetic-test-case"),), [], abort_code
    )
    assert all(trial["verdict"] == "GO" for trial in report["trials"])
    assert report["verdict"] == "NO_GO"
    assert report["evaluation_abort_code"] == abort_code
    assert finalized == [abort_code]
