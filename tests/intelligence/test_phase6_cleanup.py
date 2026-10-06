"""Cleanup failure cannot bypass the exact owned-handle fallback or claim success."""

import importlib
import subprocess
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest


@pytest.fixture
def cleanup(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / "scripts"))
    return importlib.import_module("phase6_cleanup")


class OwnedHandle:
    pid = 12345

    def __init__(self, *, exited: bool = False, kill_error: bool = False) -> None:
        self.exited = exited
        self.kill_error = kill_error
        self.killed = False
        self.waited = False

    def poll(self) -> int | None:
        return 0 if self.exited else None

    def kill(self) -> None:
        self.killed = True
        if self.kill_error:
            raise OSError("sensitive operating-system details")
        self.exited = True

    def wait(self, *, timeout: int) -> int:
        self.waited = True
        assert timeout == 5
        if not self.exited:
            raise subprocess.TimeoutExpired("sensitive command", timeout)
        return 0


def test_cleanup_targets_only_live_owned_pid_tree_and_reaps_handle(
    cleanup: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    handle = OwnedHandle()
    calls = []

    def stop(command: list[str], **kwargs: object) -> SimpleNamespace:
        calls.append((command, kwargs))
        handle.exited = True
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(cleanup.subprocess, "run", stop)
    cleanup.cleanup_owned_server(handle)
    assert calls[0][0] == ["taskkill", "/PID", "12345", "/T", "/F"]
    assert calls[0][1]["timeout"] == 10
    assert calls[0][1]["creationflags"] == subprocess.CREATE_NO_WINDOW
    assert handle.waited and not handle.killed


@pytest.mark.parametrize("failure", ["timeout", "os_error", "nonzero"])
def test_failed_tree_stop_always_kills_owned_handle_and_reports_uncertain_children(
    failure: str, cleanup: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    handle = OwnedHandle()

    def stop(*args: object, **kwargs: object) -> SimpleNamespace:
        if failure == "timeout":
            raise subprocess.TimeoutExpired("sensitive command canary", 10)
        if failure == "os_error":
            raise OSError("sensitive error canary")
        return SimpleNamespace(returncode=1)

    monkeypatch.setattr(cleanup.subprocess, "run", stop)
    with pytest.raises(RuntimeError) as captured:
        cleanup.cleanup_owned_server(handle)
    assert str(captured.value) == "owned_server_cleanup_failed"
    assert handle.killed and handle.waited
    assert "canary" not in str(captured.value)


def test_already_exited_handle_never_retargets_its_potentially_reused_pid(
    cleanup: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    handle = OwnedHandle(exited=True)

    def forbidden(*args: object, **kwargs: object) -> None:
        pytest.fail("A stale PID must never be targeted")

    monkeypatch.setattr(cleanup.subprocess, "run", forbidden)
    with pytest.raises(RuntimeError, match="^owned_server_cleanup_failed$"):
        cleanup.cleanup_owned_server(handle)
    assert handle.waited and not handle.killed


def test_unconfirmed_handle_stop_exposes_only_safe_failure(
    cleanup: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    handle = OwnedHandle(kill_error=True)
    monkeypatch.setattr(
        cleanup.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(returncode=1)
    )
    with pytest.raises(RuntimeError, match="^owned_server_cleanup_failed$"):
        cleanup.cleanup_owned_server(handle)
