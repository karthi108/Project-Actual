"""Configuration cannot accidentally widen the unauthenticated listener's scope."""

import logging

import pytest

from actual.api import __main__ as launcher
from actual.api.config import ApiSettings, ConfigurationError
from actual.api.transport import REQUEST_LOG
from actual.core.primitives import ActorId, WorkspaceId
from actual.persistence.errors import PersistenceError

WORKSPACE = WorkspaceId("workspace_" + "9" * 32)
ACTOR = ActorId("actor_" + "8" * 32)


def explicit_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ACTUAL_API_MODE", "synthetic-development")
    monkeypatch.setenv("ACTUAL_API_WORKSPACE_ID", WORKSPACE.root)
    monkeypatch.setenv("ACTUAL_API_ACTOR_ID", ACTOR.root)
    monkeypatch.delenv("ACTUAL_API_PORT", raising=False)


def test_environment_requires_explicit_synthetic_mode_and_owner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for field in ("ACTUAL_API_MODE", "ACTUAL_API_WORKSPACE_ID", "ACTUAL_API_ACTOR_ID"):
        explicit_environment(monkeypatch)
        monkeypatch.delenv(field)
        with pytest.raises(ConfigurationError) as captured:
            ApiSettings.from_environment()
        assert "workspace_" not in str(captured.value)
        assert "actor_" not in str(captured.value)
    explicit_environment(monkeypatch)
    settings = ApiSettings.from_environment()
    assert settings.workspace_id == WORKSPACE
    assert settings.actor_id == ACTOR
    assert settings.port == 8765
    assert settings.authorities == {"127.0.0.1:8765", "localhost:8765", "[::1]:8765"}


@pytest.mark.parametrize("port", ["0", "-1", "65536", "08765", " 8765", "invalid-private-value"])
def test_invalid_environment_port_is_rejected_without_echo(
    monkeypatch: pytest.MonkeyPatch, port: str
) -> None:
    explicit_environment(monkeypatch)
    monkeypatch.setenv("ACTUAL_API_PORT", port)
    with pytest.raises(ConfigurationError) as captured:
        ApiSettings.from_environment()
    assert port not in str(captured.value)


def test_real_mode_and_wrong_identifier_kind_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    explicit_environment(monkeypatch)
    monkeypatch.setenv("ACTUAL_API_MODE", "production")
    with pytest.raises(ConfigurationError):
        ApiSettings.from_environment()
    explicit_environment(monkeypatch)
    monkeypatch.setenv("ACTUAL_API_WORKSPACE_ID", ACTOR.root)
    with pytest.raises(ConfigurationError):
        ApiSettings.from_environment()
    for port in (True, 0, 65536):
        with pytest.raises(ConfigurationError):
            ApiSettings(workspace_id=WORKSPACE, actor_id=ACTOR, port=port)


def test_launcher_binds_loopback_and_ignores_untrusted_proxy_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    explicit_environment(monkeypatch)
    monkeypatch.setenv("ACTUAL_API_HOST", "0.0.0.0")
    calls = []
    app = object()
    monkeypatch.setattr(launcher, "create_app", lambda settings: app)
    monkeypatch.setattr(
        launcher.uvicorn, "run", lambda target, **options: calls.append((target, options))
    )
    handlers, level, propagate = REQUEST_LOG.handlers[:], REQUEST_LOG.level, REQUEST_LOG.propagate
    try:
        launcher.main()
        target, options = calls[0]
        assert target is app
        assert options["host"] == "127.0.0.1"
        assert options["port"] == 8765
        assert options["proxy_headers"] is False
        assert options["access_log"] is False
        assert options["server_header"] is False
        assert options["log_config"] is None
        assert REQUEST_LOG.level == logging.INFO
        assert REQUEST_LOG.propagate is False
    finally:
        REQUEST_LOG.handlers = handlers
        REQUEST_LOG.setLevel(level)
        REQUEST_LOG.propagate = propagate


def test_launcher_configuration_failure_never_prints_a_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    explicit_environment(monkeypatch)

    def failure(settings: ApiSettings) -> None:
        raise PersistenceError("postgresql://private-user:PRIVATE_PASSWORD@private-host")

    monkeypatch.setattr(launcher, "create_app", failure)
    with pytest.raises(SystemExit) as captured:
        launcher.main()
    assert "PRIVATE_PASSWORD" not in str(captured.value)
    assert "postgresql" not in str(captured.value)
