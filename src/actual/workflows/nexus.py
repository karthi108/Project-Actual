"""ACTUAL-side proposed protocol; real NEXUS interoperability is pending."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal
from uuid import uuid4

import httpx2 as httpx
from pydantic import Field

from actual.core.primitives import ActorId, Contract, Digest, Instant, WorkspaceId, content_digest

from .connectors import Access, LocalPolicy
from .ir import Name

LocalPolicyAuthorizer = LocalPolicy


class AuthorizationRequest(Contract):
    protocol: Literal["actual-nexus-v1"] = "actual-nexus-v1"
    request_id: Name
    access: Access

    @property
    def digest(self) -> str:
        return content_digest(self.model_dump(mode="json"))


class AuthorizationDecision(Contract):
    protocol: Literal["actual-nexus-v1"] = "actual-nexus-v1"
    request_id: Name
    request_digest: Digest
    decision_id: Name
    decision: Literal["allow", "deny"]
    policy_version: Annotated[int, Field(ge=1)]
    expires_at: Instant


class NexusSettings(Contract):
    mode: Literal["synthetic_harness"] = "synthetic_harness"
    port: Annotated[int, Field(ge=1024, le=65535)]
    timeout_seconds: Annotated[float, Field(gt=0, le=2, allow_inf_nan=False)] = 1.0


class NexusAuthorizer:
    def __init__(
        self,
        settings: NexusSettings,
        owner: WorkspaceId,
        actor: ActorId,
        transport: httpx.BaseTransport | None = None,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ):
        self.settings = NexusSettings.model_validate(settings)
        self.owner, self.actor = WorkspaceId.model_validate(owner), ActorId.model_validate(actor)
        self.transport, self.clock = transport, clock
        self.last_decision: AuthorizationDecision | None = None

    def allows(self, access: Access) -> bool:
        self.last_decision = None
        access = Access.model_validate(access)
        if (
            access.workspace_id != self.owner
            or access.principal_id != self.actor
            or access.workflow_digest is None
            or access.step is None
            or access.arguments_digest is None
        ):
            return False
        request = AuthorizationRequest(request_id="request_" + uuid4().hex, access=access)
        try:
            with httpx.Client(
                transport=self.transport,
                trust_env=False,
                follow_redirects=False,
                timeout=self.settings.timeout_seconds,
            ) as client:
                with client.stream(
                    "POST",
                    f"http://127.0.0.1:{self.settings.port}/v1/authorize",
                    content=request.model_dump_json().encode("utf-8"),
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                        "Accept-Encoding": "identity",
                    },
                ) as response:
                    if (
                        response.status_code != 200
                        or response.headers.get("content-type", "").split(";", 1)[0].lower()
                        != "application/json"
                        or response.headers.get("content-encoding", "identity") != "identity"
                    ):
                        return False
                    body = bytearray()
                    for chunk in response.iter_bytes():
                        body.extend(chunk)
                        if len(body) > 4096:
                            return False
            decision = AuthorizationDecision.model_validate_json(bytes(body))
            now = self.clock()
            if (
                decision.request_id != request.request_id
                or decision.request_digest != request.digest
                or decision.policy_version != access.policy_version
                or not now < decision.expires_at <= now + timedelta(seconds=30)
            ):
                return False
            self.last_decision = decision
            return decision.decision == "allow"
        except (httpx.HTTPError, ValueError, TypeError):
            return False
