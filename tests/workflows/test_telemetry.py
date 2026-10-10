import asyncio
import json
import re
from time import monotonic

import httpx2 as httpx
import pytest

from actual.deployment.telemetry import LocalOtlp, ObservedRuntime
from actual.workflows.examples import text_workflow
from actual.workflows.runtime import Runtime
from actual.workflows.state import Value
from actual.worklab.replay import Case, Memory


def memory():
    return Memory(
        Case(
            id="synthetic_telemetry",
            workflow=text_workflow(),
            trigger=(Value(name="text", value="Fabricated private text, never telemetry"),),
        )
    )


def test_transition_spans_exclude_contents_and_keep_stable_run_correlation():
    stored = memory()
    bodies = []

    class Sink:
        def emit(self, payload):
            bodies.append(payload)
            return True

    observed = ObservedRuntime(Runtime(stored, clock=lambda: stored.run.started_at), Sink())
    observed.tick(stored.run.id)
    observed.tick(stored.run.id)
    observed.tick(stored.run.id)
    assert stored.run.status == "succeeded" and observed.exported == 3
    spans = [json.loads(body)["resourceSpans"][0]["scopeSpans"][0]["spans"][0] for body in bodies]
    assert len({span["traceId"] for span in spans}) == 1
    assert len({span["spanId"] for span in spans}) == 3
    for span in spans:
        assert re.fullmatch("[0-9a-f]{32}", span["traceId"])
        assert re.fullmatch("[0-9a-f]{16}", span["spanId"])
        assert span["kind"] == 1 and isinstance(span["startTimeUnixNano"], str)
    joined = b"".join(bodies)
    assert b"Fabricated private" not in joined
    assert (
        stored.run.id.encode() not in joined and stored.run.workspace_id.root.encode() not in joined
    )


def test_export_failure_does_not_change_execution_or_hide_the_original_failure():
    class Broken:
        def emit(self, payload):
            raise RuntimeError("Fabricated diagnostic, never logged")

    stored = memory()
    observed = ObservedRuntime(Runtime(stored, clock=lambda: stored.run.started_at), Broken())
    assert observed.tick(stored.run.id).current == "copy" and observed.dropped == 1

    def fail(*args):
        raise ValueError("Original execution exception")

    stored.claim = fail
    with pytest.raises(ValueError, match="Original execution"):
        observed.tick(stored.run.id)
    assert observed.dropped == 2


@pytest.mark.parametrize("mode", ["replay", "shadow"])
def test_replay_shadow_cannot_obtain_telemetry_export(mode):
    with pytest.raises(ValueError, match="cannot export"):
        ObservedRuntime(Runtime(memory(), mode=mode), LocalOtlp())


@pytest.mark.parametrize("status,body", [(200, b"{}"), (302, b""), (500, b""), (200, b"x" * 1025)])
def test_fixed_otlp_destination_and_bounded_response(status, body):
    def handler(request):
        assert str(request.url) == "http://127.0.0.1:4318/v1/traces"
        assert request.headers["content-type"] == "application/json"
        return httpx.Response(status, content=body, headers={"location": "https://example.com"})

    exporter = LocalOtlp(httpx.MockTransport(handler))
    assert exporter.emit(b"{}") == (status == 200 and body == b"{}")
    assert not exporter.emit(b"x" * 16385)


def test_otlp_slow_peer_has_a_whole_export_deadline():
    async def slow(request):
        await asyncio.sleep(2)
        return httpx.Response(200, json={})

    started = monotonic()
    assert not LocalOtlp(httpx.MockTransport(slow)).emit(b"{}")
    assert monotonic() - started < 1
