"""One genuine local probe using an isolated cloud-disabled Ollama subprocess.

Run with uv run --locked python scripts/verify_phase5_live.py and explicit
ACTUAL_MODEL_MODE=synthetic-development. No models are downloaded and the
shared Ollama process/configuration is left untouched. Only metadata is printed.
"""

import asyncio
import json
import os
import shutil
import socket
import subprocess
from dataclasses import replace
from pathlib import Path

import httpx2 as httpx

from actual.models.__main__ import probe
from actual.models.codec import encode_object
from actual.models.config import OllamaSettings
from actual.models.errors import ModelFailure


async def observe_network(process_id: int, stopped: asyncio.Event) -> int:
    """Sample TCP peers for the owned server and its descendants, without printing peers."""
    command = (
        "$ErrorActionPreference='Stop'; "
        f"$ownedIds = [System.Collections.Generic.HashSet[int]]::new(); "
        f"[void]$ownedIds.Add({process_id}); "
        "$processes = @(Get-CimInstance Win32_Process | "
        "Select-Object ProcessId,ParentProcessId); "
        "do { $added=$false; foreach ($item in $processes) { "
        "if ($ownedIds.Contains([int]$item.ParentProcessId)) { "
        "if ($ownedIds.Add([int]$item.ProcessId)) { $added=$true } } } } while ($added); "
        "$outside = @(Get-NetTCPConnection -State Established -ErrorAction SilentlyContinue | "
        "Where-Object { $ownedIds.Contains([int]$_.OwningProcess) } | Where-Object { "
        "$address=[System.Net.IPAddress]::Parse($_.RemoteAddress); "
        "if ($address.IsIPv4MappedToIPv6) { $address=$address.MapToIPv4() }; "
        "-not [System.Net.IPAddress]::IsLoopback($address) }); "
        "@{outside_count=$outside.Count} | ConvertTo-Json -Compress"
    )
    samples = 0
    while True:
        result = await asyncio.to_thread(
            subprocess.run,
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", command],
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if result.returncode != 0 or json.loads(result.stdout) != {"outside_count": 0}:
            raise RuntimeError("Owned server TCP isolation could not be confirmed")
        samples += 1
        if stopped.is_set():
            return samples
        try:
            await asyncio.wait_for(stopped.wait(), timeout=0.25)
        except TimeoutError:
            pass


def server_environment(port: int) -> dict[str, str]:
    # Do not pass development/application/database credentials to the model process.
    child_environment = {
        key: value
        for key, value in os.environ.items()
        if key.upper()
        in {
            "PATH",
            "SYSTEMROOT",
            "WINDIR",
            "SYSTEMDRIVE",
            "COMSPEC",
            "PATHEXT",
            "TEMP",
            "TMP",
            "USERPROFILE",
            "LOCALAPPDATA",
            "APPDATA",
        }
    }
    model_path = os.environ.get("OLLAMA_MODELS")
    if model_path is None:
        profile = os.environ.get("USERPROFILE")
        if profile is None:
            raise RuntimeError("Existing Windows model directory is required")
        model_path = str(Path(profile) / ".ollama" / "models")
    if not Path(model_path).is_dir():
        raise RuntimeError("Existing installed model directory is required")
    child_environment.update(
        {
            "OLLAMA_HOST": f"127.0.0.1:{port}",
            "OLLAMA_MODELS": model_path,
            "OLLAMA_NO_CLOUD": "1",
            "OLLAMA_DEBUG": "0",
            "OLLAMA_DEBUG_LOG_REQUESTS": "0",
            "OLLAMA_NOPRUNE": "1",
            "OLLAMA_KEEP_ALIVE": "0",
            "OLLAMA_MAX_LOADED_MODELS": "1",
            "OLLAMA_NUM_PARALLEL": "1",
        }
    )
    return child_environment


async def verify() -> None:
    settings = OllamaSettings.from_environment()
    executable = shutil.which("ollama")
    if executable is None:
        raise RuntimeError("Installed Ollama executable is required")
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    child_environment = server_environment(port)
    local = replace(settings, base_url=f"http://127.0.0.1:{port}")
    process = subprocess.Popen(
        [executable, "serve"],
        env=child_environment,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    try:
        async with asyncio.timeout(15):
            async with httpx.AsyncClient(
                trust_env=False, follow_redirects=False, timeout=1
            ) as client:
                while True:
                    if process.poll() is not None:
                        raise RuntimeError("Owned Ollama process exited before readiness")
                    try:
                        response = await client.get(local.base_url + "/api/status")
                        if response.status_code == 200:
                            if response.json().get("cloud", {}).get("disabled") is not True:
                                raise RuntimeError("Owned server did not disable cloud")
                            break
                    except (httpx.ConnectError, httpx.TimeoutException):
                        pass
                    await asyncio.sleep(0.2)
        # Prove this precise child process listens only on loopback.
        inspected = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                f"Get-NetTCPConnection -State Listen -LocalPort {port} | "
                "Select-Object LocalAddress,OwningProcess | ConvertTo-Json -Compress",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        listening = json.loads(inspected.stdout)
        if inspected.returncode != 0 or listening != {
            "LocalAddress": "127.0.0.1",
            "OwningProcess": process.pid,
        }:
            raise RuntimeError("Owned server loopback/process identity could not be verified")
        stopped = asyncio.Event()
        observation = asyncio.create_task(observe_network(process.pid, stopped))
        try:
            metadata = await probe(local)
        finally:
            stopped.set()
            samples = await observation
        print(metadata)
        print(
            encode_object(
                {
                    "live_smoke": "passed",
                    "cloud_disabled": True,
                    "owned_loopback_process_verified": True,
                    "model_downloads": 0,
                    "application_state_writes": 0,
                    "tcp_observation_samples": samples,
                    "non_loopback_tcp_connections_observed": 0,
                }
            ).decode()
        )
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


if __name__ == "__main__":
    try:
        asyncio.run(verify())
    except ModelFailure as failure:
        print(encode_object({"live_smoke": "failed", "error_code": failure.code.value}).decode())
        raise SystemExit(1) from None
    except (RuntimeError, TimeoutError, OSError, ValueError, httpx.HTTPError):
        print('{"live_smoke":"failed","error_code":"verification_environment"}')
        raise SystemExit(1) from None
