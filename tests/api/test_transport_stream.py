"""Adversarial ASGI streams cannot bypass byte bounds or leak request metadata."""

import asyncio
import json
import logging

import pytest

from actual.api.config import ApiSettings
from actual.api.transport import LocalBoundary
from actual.core.primitives import ActorId, WorkspaceId


def scope(headers: list[tuple[bytes, bytes]] | None = None) -> dict:
    return {
        "type": "http",
        "method": "POST",
        "path": "/api/v1/jobs/private-path",
        "query_string": b"secret=PRIVATE_STREAM_INPUT",
        "client": ("127.0.0.1", 50000),
        "headers": [
            (b"host", b"127.0.0.1:8765"),
            (b"content-type", b"application/json"),
            *(headers or []),
        ],
    }


async def invoke(messages: list[dict], request: dict, *, stall: bool = False) -> tuple[list, bool]:
    output = []
    reached = False

    async def downstream(scope: dict, receive: object, send: object) -> None:
        nonlocal reached
        reached = True
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"{}"})

    async def receive() -> dict:
        if stall:
            await asyncio.sleep(1)
        return messages.pop(0)

    async def send(message: dict) -> None:
        output.append(message)

    middleware = LocalBoundary(
        downstream,
        ApiSettings(
            workspace_id=WorkspaceId("workspace_" + "9" * 32),
            actor_id=ActorId("actor_" + "8" * 32),
        ),
    )
    await middleware(request, receive, send)
    return output, reached


def status(result: tuple[list, bool]) -> int:
    output, reached = result
    assert not reached
    response = json.loads(output[-1]["body"])
    assert response["schema_version"] == "actual-api-v1"
    assert response["request_id"]
    return output[0]["status"]


def test_chunked_actual_bytes_are_bounded_without_content_length() -> None:
    messages = [
        {"type": "http.request", "body": b" " * 200_000, "more_body": True},
        {"type": "http.request", "body": b" " * 62_145, "more_body": False},
    ]
    assert status(asyncio.run(invoke(messages, scope()))) == 413


def test_declared_length_mismatch_and_disconnect_fail_before_use_case() -> None:
    assert (
        status(
            asyncio.run(
                invoke(
                    [{"type": "http.request", "body": b"{}", "more_body": False}],
                    scope([(b"content-length", b"1")]),
                )
            )
        )
        == 400
    )
    assert status(asyncio.run(invoke([{"type": "http.disconnect"}], scope()))) == 400


def test_slow_body_wait_is_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("actual.api.transport.BODY_TIMEOUT_SECONDS", 0.001)
    assert status(asyncio.run(invoke([], scope(), stall=True))) == 408


@pytest.mark.parametrize("body", [b'{"x":1e999}', b'{"x":"\\ud800"}', b'{"x": {"x": 1, "x": 2}}'])
def test_hidden_nonfinite_surrogate_and_nested_duplicates_fail_closed(body: bytes) -> None:
    assert (
        status(
            asyncio.run(
                invoke([{"type": "http.request", "body": body, "more_body": False}], scope())
            )
        )
        == 422
    )


def test_structured_log_uses_route_template_and_server_request_id_only(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger="actual.api.requests")
    request = scope([(b"x-request-id", b"PRIVATE_STREAM_INPUT")])
    result = asyncio.run(
        invoke([{"type": "http.request", "body": b"{}", "more_body": False}], request)
    )
    assert result[1]
    records = [record for record in caplog.records if record.name == "actual.api.requests"]
    assert len(records) == 1
    record = json.loads(records[0].getMessage())
    assert set(record) == {"request_id", "method", "route", "status", "duration_ms", "error_code"}
    assert record["route"] == "unmatched"
    assert record["status"] == 200
    assert record["duration_ms"] >= 0
    assert record["request_id"] == request["state"]["request_id"]
    assert "PRIVATE_STREAM_INPUT" not in caplog.text
    assert "private-path" not in caplog.text
