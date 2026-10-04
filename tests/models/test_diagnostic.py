"""The supported diagnostic admits no user prose or credential-bearing child environment."""

import asyncio
import runpy
from pathlib import Path

import pytest

from actual.models import __main__ as diagnostic
from actual.models.errors import FailureCode, ModelFailure
from actual.models.gateway import MODEL_LOG


def test_launcher_refuses_content_arguments(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["actual-model-probe", "PRIVATE_PROFILE"])
    with pytest.raises(SystemExit) as caught:
        diagnostic.main()
    assert "PRIVATE_PROFILE" not in str(caught.value)


def test_launcher_configuration_failure_has_only_safe_code(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("sys.argv", ["actual-model-probe"])
    monkeypatch.delenv("ACTUAL_MODEL_MODE", raising=False)
    monkeypatch.setattr(MODEL_LOG, "handlers", [])
    monkeypatch.setattr(MODEL_LOG, "propagate", True)
    monkeypatch.setattr(MODEL_LOG, "level", MODEL_LOG.level)
    with pytest.raises(SystemExit) as caught:
        diagnostic.main()
    assert caught.value.code == 1
    assert capsys.readouterr().out == '{"error_code":"configuration","status":"failure"}\n'
    # Do not leave a handler pointing at pytest's closed capture stream.
    MODEL_LOG.handlers.clear()


def test_diagnostic_uses_fixed_synthetic_input(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed = []

    class Unavailable:
        def __init__(self, provider: object, *, capabilities: tuple) -> None:
            observed.append(capabilities)

        async def run(self, capability: object, value: object) -> None:
            observed.append(value)
            raise ModelFailure(FailureCode.PROVIDER_UNAVAILABLE)

    monkeypatch.setattr(diagnostic, "ModelGateway", Unavailable)
    from actual.models.config import OllamaSettings

    with pytest.raises(ModelFailure):
        asyncio.run(diagnostic.probe(OllamaSettings()))
    assert observed[1].model_dump(mode="json") == {
        "schema_version": "actual-probe-input-v1",
        "synthetic": True,
        "tokens": ["red", "blue", "green"],
    }


def test_owned_server_environment_excludes_secrets_and_disables_retention(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("OLLAMA_MODELS", str(tmp_path))
    monkeypatch.setenv("ACTUAL_DATABASE_URL", "PRIVATE_DATABASE_CREDENTIAL")
    monkeypatch.setenv("OPENAI_API_KEY", "PRIVATE_PAID_KEY")
    monkeypatch.setenv("OLLAMA_API_KEY", "PRIVATE_OLLAMA_KEY")
    monkeypatch.setenv("OLLAMA_DEBUG_LOG_REQUESTS", "1")
    module = runpy.run_path("scripts/verify_phase5_live.py", run_name="phase5_test")
    environment = module["server_environment"](11435)
    assert not any("PRIVATE_" in value for value in environment.values())
    assert environment["OLLAMA_NO_CLOUD"] == "1"
    assert environment["OLLAMA_NOPRUNE"] == "1"
    assert environment["OLLAMA_DEBUG"] == "0"
    assert environment["OLLAMA_DEBUG_LOG_REQUESTS"] == "0"
    assert environment["OLLAMA_HOST"] == "127.0.0.1:11435"
    assert environment["OLLAMA_MODELS"] == str(tmp_path)
