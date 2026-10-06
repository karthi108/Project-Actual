"""Fake-only checks for bounded owned-process TCP observation."""

import asyncio
import importlib.util
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "phase6_monitor_tests", ROOT / "scripts/phase6_monitor.py"
)
assert SPEC is not None and SPEC.loader is not None
monitor = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(monitor)

PROCESS_ID = 100
PROCESSES = json.dumps(
    [
        {"ProcessId": 100, "ParentProcessId": 20},
        {"ProcessId": 200, "ParentProcessId": 100},
        {"ProcessId": 300, "ParentProcessId": 200},
        {"ProcessId": 900, "ParentProcessId": 50},
    ]
)
HEADINGS = "Active Connections\n  Proto  Local Address  Foreign Address  State  PID\n"


def run_stopped() -> int:
    async def run() -> int:
        stopped = asyncio.Event()
        stopped.set()
        return await monitor.observe_network(PROCESS_ID, stopped)

    return asyncio.run(run())


def fake_commands(
    monkeypatch: pytest.MonkeyPatch,
    *,
    processes: str = PROCESSES,
    tcp: str = HEADINGS + " TCP 127.0.0.1:40000 127.0.0.1:11434 ESTABLISHED 100\n",
    tcpv6: str = HEADINGS + " TCP [::1]:40001 [::1]:11434 ESTABLISHED 300\n",
) -> list[tuple[list[str], dict[str, Any]]]:
    calls: list[tuple[list[str], dict[str, Any]]] = []

    def execute(arguments: list[str], **options: Any) -> subprocess.CompletedProcess[str]:
        calls.append((arguments, options))
        if arguments[0] == "powershell":
            text = processes
        else:
            assert arguments[:4] == ["netstat.exe", "-ano", "-p", arguments[3]]
            text = tcp if arguments[-1] == "tcp" else tcpv6
        return subprocess.CompletedProcess(arguments, returncode=0, stdout=text, stderr="")

    monkeypatch.setattr(monitor.subprocess, "run", execute)
    return calls


def test_success_checks_ipv4_ipv6_descendants_and_only_returns_sample_count(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = fake_commands(monkeypatch)
    assert run_stopped() == 1
    assert len(calls) == 3
    assert [arguments[-1] for arguments, _ in calls[1:]] == ["tcp", "tcpv6"]
    for _, options in calls:
        assert 0 < options["timeout"] <= 20
        assert options["capture_output"] is True
        assert options["creationflags"] == subprocess.CREATE_NO_WINDOW
    assert "Get-NetTCPConnection" not in calls[0][0][-1]
    assert "CommandLine" not in calls[0][0][-1]


@pytest.mark.parametrize(
    "remote",
    ["127.0.0.1:11434", "127.23.45.67:11434", "[::1]:11434", "[::ffff:127.0.0.1]:11434"],
)
def test_local_and_ipv4_mapped_loopback_peers_are_accepted(
    monkeypatch: pytest.MonkeyPatch, remote: str
) -> None:
    fake_commands(monkeypatch, tcp=HEADINGS + f" TCP 127.0.0.1:40000 {remote} ESTABLISHED 200\n")
    assert run_stopped() == 1


@pytest.mark.parametrize(
    "row",
    [
        " TCP 127.0.0.1:40000 203.0.113.7:443 ESTABLISHED 100",
        " TCP 127.0.0.1:40000 203.0.113.7:443 ESTABLISHED 200",
        " TCP [::1]:40000 [2001:db8::7]:443 ESTABLISHED 300",
        " TCP [::1]:40000 [::ffff:203.0.113.7]:443 ESTABLISHED 300",
    ],
)
def test_owned_server_and_any_descendant_external_peer_fails_closed(
    monkeypatch: pytest.MonkeyPatch, row: str
) -> None:
    calls = fake_commands(monkeypatch, tcp=HEADINGS + row + "\n")
    with pytest.raises(RuntimeError, match="^phase6_network_inspection_failed$") as captured:
        run_stopped()
    assert "203.0.113.7" not in str(captured.value)
    assert len(calls) == 2  # Inspection stops immediately; no automatic retry.


def test_unrelated_connections_are_not_mistaken_for_owned_egress(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_commands(
        monkeypatch,
        tcp=HEADINGS + " TCP 192.0.2.8:40000 203.0.113.7:443 ESTABLISHED 900\n",
    )
    assert run_stopped() == 1


@pytest.mark.parametrize(
    "row",
    [
        " TCP 127.0.0.1:1 invalid:2 ESTABLISHED 100",
        " TCP 127.0.0.1:1 127.0.0.1:65536 ESTABLISHED 100",
        " TCP 127.0.0.1:1 127.0.0.1:2 UNKNOWN_STATE 100",
        " TCP 127.0.0.1:1 127.0.0.1:2 ESTABLISHED surplus 100",
        " TCP 127.0.0.1:1 127.0.0.1:2 ESTABLISHED not-a-pid",
        " BAD 127.0.0.1:1 127.0.0.1:2 ESTABLISHED 100",
        " TCP 127.0.0.1:0 127.0.0.1:2 ESTABLISHED 100",
    ],
)
def test_unparseable_or_ambiguous_owned_rows_never_count_as_a_safe_sample(
    monkeypatch: pytest.MonkeyPatch, row: str
) -> None:
    fake_commands(monkeypatch, tcp=HEADINGS + row + "\n")
    with pytest.raises(RuntimeError, match="^phase6_network_inspection_failed$"):
        run_stopped()


def test_non_established_rows_do_not_claim_external_connections(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_commands(
        monkeypatch,
        tcp=HEADINGS + " TCP 127.0.0.1:11434 0.0.0.0:0 LISTENING 100\n",
        tcpv6=HEADINGS + " TCP [::1]:11434 [::]:0 LISTENING 200\n",
    )
    assert run_stopped() == 1


@pytest.mark.parametrize(
    "processes",
    [
        "not JSON",
        "[]",
        '[{"ProcessId":100,"ProcessId":200,"ParentProcessId":20}]',
        '[{"ProcessId":100,"ParentProcessId":20,"CommandLine":"private"}]',
        '[{"ProcessId":true,"ParentProcessId":20}]',
        '[{"ProcessId":100,"ParentProcessId":"20"}]',
        '[{"ProcessId":100,"ParentProcessId":20},{"ProcessId":100,"ParentProcessId":20}]',
    ],
)
def test_invalid_or_missing_owner_inventory_aborts_without_netstat(
    monkeypatch: pytest.MonkeyPatch, processes: str
) -> None:
    calls = fake_commands(monkeypatch, processes=processes)
    with pytest.raises(RuntimeError, match="^phase6_network_inspection_failed$"):
        run_stopped()
    assert len(calls) == 1


@pytest.mark.parametrize(
    "exception", [subprocess.TimeoutExpired("private peer", 20), OSError("private")]
)
def test_inspection_timeout_and_os_errors_are_content_free_and_not_retried(
    monkeypatch: pytest.MonkeyPatch, exception: Exception
) -> None:
    calls = 0

    def execute(*arguments: object, **options: object) -> subprocess.CompletedProcess[str]:
        nonlocal calls
        calls += 1
        raise exception

    monkeypatch.setattr(monitor.subprocess, "run", execute)
    with pytest.raises(RuntimeError, match="^phase6_network_inspection_failed$") as captured:
        run_stopped()
    assert "private" not in str(captured.value)
    assert captured.value.__suppress_context__ is True
    assert calls == 1


def test_subprocess_nonzero_empty_and_oversized_outputs_are_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for result in (
        subprocess.CompletedProcess([], 1, stdout=PROCESSES, stderr="private"),
        subprocess.CompletedProcess([], 0, stdout="", stderr=""),
        subprocess.CompletedProcess([], 0, stdout="x" * 1_000_001, stderr=""),
    ):
        monkeypatch.setattr(
            monitor.subprocess, "run", lambda *args, _result=result, **kwargs: _result
        )
        with pytest.raises(RuntimeError, match="^phase6_network_inspection_failed$"):
            run_stopped()


def test_all_subprocesses_share_one_inspection_deadline(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = fake_commands(monkeypatch)
    ticks = iter([0.0, 1.0, 4.0, 8.0, 9.0])
    monkeypatch.setattr(monitor, "time", SimpleNamespace(monotonic=lambda: next(ticks)))
    monitor._sample(PROCESS_ID)
    assert [options["timeout"] for _, options in calls] == [19.0, 16.0, 12.0]


def test_missing_netstat_header_does_not_silently_mean_no_connections(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_commands(monkeypatch, tcp="unparseable command output")
    with pytest.raises(RuntimeError, match="^phase6_network_inspection_failed$"):
        run_stopped()


def test_ipv6_query_is_independently_checked(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = fake_commands(
        monkeypatch,
        tcpv6=HEADINGS + " TCP [::1]:40000 [2001:db8::7]:443 ESTABLISHED 200\n",
    )
    with pytest.raises(RuntimeError, match="^phase6_network_inspection_failed$"):
        run_stopped()
    assert len(calls) == 3


def test_stopping_after_two_successful_samples_returns_exact_count(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(monitor, "SAMPLE_INTERVAL_SECONDS", 0.001)

    async def run() -> tuple[int, int]:
        stopped = asyncio.Event()
        loop = asyncio.get_running_loop()
        calls = 0

        def execute(arguments: list[str], **options: object) -> subprocess.CompletedProcess[str]:
            nonlocal calls
            calls += 1
            text = PROCESSES if arguments[0] == "powershell" else HEADINGS
            if calls == 6:
                loop.call_soon_threadsafe(stopped.set)
            return subprocess.CompletedProcess(arguments, 0, stdout=text, stderr="")

        monkeypatch.setattr(monitor.subprocess, "run", execute)
        samples = await monitor.observe_network(PROCESS_ID, stopped)
        return samples, calls

    assert asyncio.run(run()) == (2, 6)


def test_async_worker_stall_is_bounded_and_mapped_safely(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(monitor, "INSPECTION_TIMEOUT_SECONDS", 0.01)

    async def stall(*args: object) -> None:
        await asyncio.Event().wait()

    monkeypatch.setattr(monitor.asyncio, "to_thread", stall)
    with pytest.raises(RuntimeError, match="^phase6_network_inspection_failed$"):
        run_stopped()


@pytest.mark.parametrize("process_id", [0, -1, True, "100", 2**32])
def test_invalid_owned_pid_cannot_begin_inspection(process_id: object) -> None:
    async def run() -> None:
        await monitor.observe_network(process_id, asyncio.Event())

    with pytest.raises(RuntimeError, match="^phase6_network_inspection_failed$"):
        asyncio.run(run())
