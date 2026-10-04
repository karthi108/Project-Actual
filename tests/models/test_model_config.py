"""Local model configuration cannot silently enable remote or real-data inference."""

from dataclasses import FrozenInstanceError

import pytest

from actual.models.config import LOCAL_QWEN_MODELS, OllamaSettings
from actual.models.contracts import GenerationSettings
from actual.models.errors import FailureCode, ModelFailure


def synthetic_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ACTUAL_MODEL_MODE", "synthetic-development")
    for name in (
        "ACTUAL_OLLAMA_BASE_URL",
        "ACTUAL_OLLAMA_MODEL",
        "ACTUAL_MODEL_TIMEOUT_SECONDS",
        "ACTUAL_MODEL_CONTEXT_TOKENS",
        "ACTUAL_MODEL_MAX_OUTPUT_TOKENS",
    ):
        monkeypatch.delenv(name, raising=False)


def test_defaults_and_installed_qwen_choices_are_explicit_and_immutable() -> None:
    settings = OllamaSettings()
    assert settings.base_url == "http://127.0.0.1:11434"
    assert settings.model == "qwen3:4b-instruct"
    assert settings.mode == "synthetic-development"
    assert settings.generation.timeout_seconds == 120.0
    assert settings.generation.context_tokens == 4096
    assert settings.generation.max_output_tokens == 128
    assert settings.generation.temperature == 0
    assert settings.generation.seed == 42
    for model in LOCAL_QWEN_MODELS:
        assert OllamaSettings(model=model).model == model
    with pytest.raises(FrozenInstanceError):
        settings.model = "qwen3:8b"


@pytest.mark.parametrize(
    ("endpoint", "canonical"),
    [
        ("http://localhost:11434/", "http://127.0.0.1:11434"),
        ("http://127.0.0.1:12434", "http://127.0.0.1:12434"),
        ("http://[::1]:11434", "http://[::1]:11434"),
    ],
)
def test_local_endpoints_are_canonicalized_without_dns(endpoint: str, canonical: str) -> None:
    assert OllamaSettings(base_url=endpoint).base_url == canonical


@pytest.mark.parametrize(
    "endpoint",
    [
        "https://127.0.0.1:11434",
        "http://private.example:11434",
        "http://192.168.1.10:11434",
        "http://0.0.0.0:11434",
        "http://localhost.private.example:11434",
        "http://localhost:11434@private.example:11434",
        "http://PRIVATE_USER:PRIVATE_PASSWORD@localhost:11434",
        "http://localhost:11434/api/chat",
        "http://localhost:11434?token=PRIVATE_ENDPOINT_TOKEN",
        "http://localhost:11434#PRIVATE_ENDPOINT_TOKEN",
        "http://localhost:11434?",
        "http://localhost:11434#",
        "http://localhost",
        "http://localhost:0",
        "http://localhost:65536",
        " http://localhost:11434",
        "http://localhost:11434\n",
    ],
)
def test_invalid_destinations_fail_without_echoing_configuration(endpoint: str) -> None:
    with pytest.raises(ModelFailure) as captured:
        OllamaSettings(base_url=endpoint)
    assert captured.value.code == FailureCode.CONFIGURATION
    assert endpoint not in str(captured.value)
    assert "PRIVATE_" not in str(captured.value)


@pytest.mark.parametrize("model", ["qwen3:4b-instruct:cloud", "qwen3:remote", "llama3:8b", ""])
def test_unapproved_or_cloud_model_tags_fail_closed(model: str) -> None:
    with pytest.raises(ModelFailure) as captured:
        OllamaSettings(model=model)
    assert captured.value.code == FailureCode.CONFIGURATION


def test_environment_requires_explicit_synthetic_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    synthetic_environment(monkeypatch)
    monkeypatch.delenv("ACTUAL_MODEL_MODE", raising=False)
    with pytest.raises(ModelFailure) as captured:
        OllamaSettings.from_environment()
    assert captured.value.code == FailureCode.CONFIGURATION
    monkeypatch.setenv("ACTUAL_MODEL_MODE", "personal")
    with pytest.raises(ModelFailure):
        OllamaSettings.from_environment()
    monkeypatch.setenv("ACTUAL_MODEL_MODE", "synthetic-development")
    assert OllamaSettings.from_environment() == OllamaSettings()


def test_environment_selects_only_supported_local_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    synthetic_environment(monkeypatch)
    monkeypatch.setenv("ACTUAL_OLLAMA_BASE_URL", "http://localhost:12434")
    monkeypatch.setenv("ACTUAL_OLLAMA_MODEL", "qwen3:8b")
    monkeypatch.setenv("ACTUAL_MODEL_TIMEOUT_SECONDS", "31")
    monkeypatch.setenv("ACTUAL_MODEL_CONTEXT_TOKENS", "2048")
    monkeypatch.setenv("ACTUAL_MODEL_MAX_OUTPUT_TOKENS", "64")
    monkeypatch.setenv("ACTUAL_MODEL_PROVIDER", "paid-service")
    settings = OllamaSettings.from_environment()
    assert settings.base_url == "http://127.0.0.1:12434"
    assert settings.model == "qwen3:8b"
    assert settings.generation.timeout_seconds == 31.0
    assert settings.generation.context_tokens == 2048
    assert settings.generation.max_output_tokens == 64


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("ACTUAL_MODEL_TIMEOUT_SECONDS", "PRIVATE_TIMEOUT"),
        ("ACTUAL_MODEL_TIMEOUT_SECONDS", "NaN"),
        ("ACTUAL_MODEL_TIMEOUT_SECONDS", " 120"),
        ("ACTUAL_MODEL_CONTEXT_TOKENS", "-1"),
        ("ACTUAL_MODEL_MAX_OUTPUT_TOKENS", "128.0"),
    ],
)
def test_invalid_numeric_environment_fails_without_echo(
    monkeypatch: pytest.MonkeyPatch, field: str, value: str
) -> None:
    synthetic_environment(monkeypatch)
    monkeypatch.setenv(field, value)
    with pytest.raises(ModelFailure) as captured:
        OllamaSettings.from_environment()
    assert captured.value.code == FailureCode.CONFIGURATION
    assert value not in str(captured.value)


def test_configuration_rejects_real_mode_and_untyped_generation() -> None:
    with pytest.raises(ModelFailure):
        OllamaSettings(mode="personal")
    with pytest.raises(ModelFailure):
        OllamaSettings(generation={"timeout_seconds": 120})


@pytest.mark.parametrize(
    ("field", "value"),
    [("timeout_seconds", float("inf")), ("timeout_seconds", 0), ("context_tokens", 8193)],
)
def test_forged_generation_settings_are_revalidated(field: str, value: object) -> None:
    generation = GenerationSettings()
    object.__setattr__(generation, field, value)
    with pytest.raises(ModelFailure) as captured:
        OllamaSettings(generation=generation)
    assert captured.value.code == FailureCode.CONFIGURATION
