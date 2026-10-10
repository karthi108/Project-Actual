"""Opt-in OTLP/HTTP JSON transition spans without payloads or authority."""

import asyncio
import json
from collections.abc import Callable
from secrets import token_hex
from time import time_ns
from typing import Protocol

import httpx2 as httpx

from actual.core.primitives import content_digest
from actual.workflows.runtime import Runtime
from actual.workflows.state import Run


class TraceSink(Protocol):
    def emit(self, payload: bytes) -> bool: ...


class LocalOtlp:
    """Fixed local collector, one bounded attempt, no headers/proxy configuration."""

    def __init__(self, transport: httpx.AsyncBaseTransport | None = None):
        self.transport = transport

    def emit(self, payload: bytes) -> bool:
        if len(payload) > 16384:
            return False
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self._bounded(payload))
        return False  # The synchronous driver must never block an existing event loop.

    async def _bounded(self, payload: bytes) -> bool:
        try:
            return await asyncio.wait_for(self._send(payload), timeout=0.25)
        except (TimeoutError, httpx.HTTPError, ValueError):
            return False

    async def _send(self, payload: bytes) -> bool:
        async with httpx.AsyncClient(
            timeout=0.25, trust_env=False, follow_redirects=False, transport=self.transport
        ) as client:
            async with client.stream(
                "POST",
                "http://127.0.0.1:4318/v1/traces",
                content=payload,
                headers={"content-type": "application/json", "accept-encoding": "identity"},
            ) as response:
                if response.status_code != 200 or response.headers.get("content-encoding"):
                    return False
                body = bytearray()
                async for chunk in response.aiter_bytes():
                    if len(body) + len(chunk) > 1024:
                        return False
                    body.extend(chunk)
                return not body or json.loads(body) == {}


def span(run: Run, mode: str, start: int, end: int, failed: bool) -> bytes:
    identity = content_digest({"owner": run.workspace_id.root, "run": run.id})
    attributes = {
        "actual.run.digest": identity,
        "actual.workflow.digest": run.definition_digest,
        "actual.mode": mode,
        "actual.status": run.status,
    }
    return json.dumps(
        {
            "resourceSpans": [
                {
                    "resource": {
                        "attributes": [{"key": "service.name", "value": {"stringValue": "actual"}}]
                    },
                    "scopeSpans": [
                        {
                            "scope": {"name": "actual.workflow", "version": "1"},
                            "spans": [
                                {
                                    "traceId": identity[:32],
                                    "spanId": token_hex(8),
                                    "name": "workflow.tick",
                                    "kind": 1,
                                    "startTimeUnixNano": str(start),
                                    "endTimeUnixNano": str(max(start, end)),
                                    "status": {"code": 2 if failed else 1},
                                    "attributes": [
                                        {"key": key, "value": {"stringValue": value}}
                                        for key, value in attributes.items()
                                    ],
                                }
                            ],
                        }
                    ],
                }
            ],
        },
        separators=(",", ":"),
    ).encode("utf-8")


class ObservedRuntime:
    def __init__(
        self,
        runtime: Runtime,
        sink: TraceSink | None = None,
        clock: Callable[[], int] = time_ns,
    ):
        if runtime.mode != "synthetic" and sink is not None:
            raise ValueError("Replay/shadow telemetry cannot export")
        self.runtime, self.sink, self.clock = runtime, sink, clock
        self.exported, self.dropped = 0, 0

    def tick(self, identifier: str) -> Run:
        start = self.clock()
        before = self.runtime.store.load(identifier)
        result, failed = before, True
        try:
            result = self.runtime.tick(identifier)
            failed = result.status == "failed"
            return result
        finally:
            if self.sink is not None and self.runtime.mode == "synthetic":
                # Best-effort diagnostics never change a committed result or hide an exception.
                try:
                    emitted = self.sink.emit(
                        span(result, self.runtime.mode, start, self.clock(), failed)
                    )
                except Exception:
                    emitted = False
                if emitted:
                    self.exported += 1
                else:
                    self.dropped += 1
