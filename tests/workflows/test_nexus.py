from datetime import UTC, datetime, timedelta

import httpx2 as httpx
import pytest

from actual.core.primitives import ActorId, WorkspaceId
from actual.workflows.connectors import Access
from actual.workflows.nexus import (
    AuthorizationDecision,
    AuthorizationRequest,
    NexusAuthorizer,
    NexusSettings,
)

OWNER = WorkspaceId("workspace_" + "1" * 32)
ACTOR = ActorId("actor_" + "1" * 32)
NOW = datetime(2026, 10, 7, tzinfo=UTC)


def access():
    return Access(
        workspace_id=OWNER,
        principal_id=ACTOR,
        capability="fake_write",
        resource="synthetic_inbox",
        workflow_digest="a" * 64,
        step="send",
        arguments_digest="b" * 64,
        intent_digest="c" * 64,
    )


def authorizer(handler):
    return NexusAuthorizer(
        NexusSettings(port=19022), OWNER, ACTOR, httpx.MockTransport(handler), clock=lambda: NOW
    )


def reply(request, **changes):
    incoming = AuthorizationRequest.model_validate_json(request.content)
    assert request.url.path == "/v1/authorize"
    decision = AuthorizationDecision(
        request_id=incoming.request_id,
        request_digest=incoming.digest,
        decision_id="decision_fake",
        decision="allow",
        policy_version=1,
        expires_at=NOW + timedelta(seconds=10),
    )
    return httpx.Response(
        200,
        content=decision.model_copy(update=changes).model_dump_json(),
        headers={"Content-Type": "application/json"},
    )


def test_proposed_protocol_exact_context_binding_and_decision_metadata():
    client = authorizer(reply)
    assert client.allows(access()) and client.last_decision.decision_id == "decision_fake"
    assert not client.allows(
        access().model_copy(update={"workspace_id": WorkspaceId("workspace_" + "2" * 32)})
    )
    assert not client.allows(access().model_copy(update={"arguments_digest": None}))


@pytest.mark.parametrize(
    "changes",
    [
        {"request_digest": "d" * 64},
        {"request_id": "other"},
        {"policy_version": 2},
        {"expires_at": NOW},
        {"expires_at": NOW + timedelta(seconds=31)},
        {"decision": "deny"},
    ],
)
def test_stale_mismatched_denied_decisions_fail_closed(changes):
    assert not authorizer(lambda req: reply(req, **changes)).allows(access())


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(429),
        httpx.Response(500),
        httpx.Response(302, headers={"Location": "http://example.com"}),
        httpx.Response(200, json={"allow": True, "secret": "fabricated"}),
        httpx.Response(200, content=b"x" * 4097, headers={"Content-Type": "application/json"}),
    ],
)
def test_transport_and_untrusted_response_fail_closed(response):
    assert not authorizer(lambda req: response).allows(access())


def test_timeout_never_falls_back_to_permission():
    def timeout(request):
        raise httpx.ReadTimeout("fabricated private diagnostic")

    assert not authorizer(timeout).allows(access())
