"""Bounded metadata-only Windows TCP sampling for an owned Ollama process tree.

This is observation, not a firewall: snapshots may miss brief connections and
do not inspect UDP/DNS. No addresses or command output are returned or logged.
"""

import asyncio
import ipaddress
import json
import re
import subprocess
import time
from collections import defaultdict

INSPECTION_TIMEOUT_SECONDS = 20.0
SAMPLE_INTERVAL_SECONDS = 1.0
_MAX_INSPECTION_CHARS = 1_000_000
_FAILURE = "phase6_network_inspection_failed"
_STATES = frozenset(
    {
        "LISTENING",
        "SYN_SENT",
        "SYN_RECEIVED",
        "ESTABLISHED",
        "FIN_WAIT_1",
        "FIN_WAIT_2",
        "CLOSE_WAIT",
        "CLOSING",
        "LAST_ACK",
        "TIME_WAIT",
        "DELETE_TCB",
        "CLOSED",
    }
)
_PROCESS_COMMAND = (
    "$ErrorActionPreference='Stop'; "
    "@(Get-CimInstance Win32_Process -ErrorAction Stop | "
    "Select-Object ProcessId,ParentProcessId) | ConvertTo-Json -Compress"
)


def _run(arguments: list[str], deadline: float) -> str:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise RuntimeError(_FAILURE)
    result = subprocess.run(
        arguments,
        capture_output=True,
        text=True,
        timeout=remaining,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    if (
        result.returncode != 0
        or type(result.stdout) is not str
        or not result.stdout.strip()
        or len(result.stdout) > _MAX_INSPECTION_CHARS
    ):
        raise RuntimeError(_FAILURE)
    return result.stdout


def _process_ids(payload: str, process_id: int) -> set[int]:
    def unique(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise RuntimeError(_FAILURE)
            result[key] = value
        return result

    records: object = json.loads(payload, object_pairs_hook=unique)
    if type(records) is dict:
        records = [records]
    if type(records) is not list:
        raise RuntimeError(_FAILURE)
    parents: dict[int, int] = {}
    children: dict[int, set[int]] = defaultdict(set)
    for record in records:
        if type(record) is not dict or set(record) != {"ProcessId", "ParentProcessId"}:
            raise RuntimeError(_FAILURE)
        pid, parent = record["ProcessId"], record["ParentProcessId"]
        if (
            type(pid) is not int
            or type(parent) is not int
            or not 0 <= pid <= 2**32 - 1
            or not 0 <= parent <= 2**32 - 1
            or pid in parents
        ):
            raise RuntimeError(_FAILURE)
        parents[pid] = parent
        children[parent].add(pid)
    if process_id not in parents:
        raise RuntimeError(_FAILURE)
    owned = {process_id}
    pending = [process_id]
    while pending:
        parent = pending.pop()
        for child in children[parent] - owned:
            owned.add(child)
            pending.append(child)
    return owned


def _endpoint(value: str) -> tuple[ipaddress.IPv4Address | ipaddress.IPv6Address, int]:
    if value.startswith("["):
        matched = re.fullmatch(r"\[([^\]]+)\]:([0-9]{1,5})", value)
        if matched is None:
            raise RuntimeError(_FAILURE)
        address_text, port_text = matched.groups()
    else:
        matched = re.fullmatch(r"([^:]+):([0-9]{1,5})", value)
        if matched is None:
            raise RuntimeError(_FAILURE)
        address_text, port_text = matched.groups()
    address = ipaddress.ip_address(address_text)
    port = int(port_text)
    if not 0 <= port <= 65535:
        raise RuntimeError(_FAILURE)
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped is not None:
        address = address.ipv4_mapped
    return address, port


def _check_tcp(payload: str, owned: set[int]) -> None:
    header_seen = False
    for line in payload.splitlines():
        fields = line.split()
        if not fields:
            continue
        if fields == ["Proto", "Local", "Address", "Foreign", "Address", "State", "PID"]:
            header_seen = True
            continue
        if fields[0].upper() in {"TCP", "TCPV6"} and (len(fields) != 5 or not fields[-1].isdigit()):
            raise RuntimeError(_FAILURE)
        if not fields[-1].isdigit():
            continue  # Headings have no numeric owner identifier.
        pid = int(fields[-1])
        if pid not in owned:
            continue
        if len(fields) != 5 or fields[0].upper() not in {"TCP", "TCPV6"}:
            raise RuntimeError(_FAILURE)
        state = fields[3].upper()
        if state not in _STATES:
            raise RuntimeError(_FAILURE)
        _, local_port = _endpoint(fields[1])
        remote, remote_port = _endpoint(fields[2])
        if state == "ESTABLISHED" and (
            not remote.is_loopback or local_port == 0 or remote_port == 0
        ):
            raise RuntimeError(_FAILURE)
    if not header_seen:
        raise RuntimeError(_FAILURE)


def _sample(process_id: int) -> None:
    deadline = time.monotonic() + INSPECTION_TIMEOUT_SECONDS
    processes = _run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", _PROCESS_COMMAND],
        deadline,
    )
    owned = _process_ids(processes, process_id)
    # NETSTAT's supported protocol selectors distinguish TCP and TCPv6.
    # Query both; -n avoids DNS and -o supplies PID ownership without -b.
    for protocol in ("tcp", "tcpv6"):
        connections = _run(["netstat.exe", "-ano", "-p", protocol], deadline)
        _check_tcp(connections, owned)
    if time.monotonic() > deadline:
        raise RuntimeError(_FAILURE)


async def observe_network(process_id: int, stopped: asyncio.Event) -> int:
    """Return successful sample count; any failed inspection aborts without retry."""
    try:
        if type(process_id) is not int or not 1 <= process_id <= 2**32 - 1:
            raise RuntimeError(_FAILURE)
        samples = 0
        while True:
            async with asyncio.timeout(INSPECTION_TIMEOUT_SECONDS):
                await asyncio.to_thread(_sample, process_id)
            samples += 1
            if stopped.is_set():
                return samples
            try:
                await asyncio.wait_for(stopped.wait(), timeout=SAMPLE_INTERVAL_SECONDS)
            except TimeoutError:
                pass
    except asyncio.CancelledError:
        raise
    except Exception:
        # Never expose peer addresses, raw command output or TimeoutExpired contents.
        raise RuntimeError(_FAILURE) from None
