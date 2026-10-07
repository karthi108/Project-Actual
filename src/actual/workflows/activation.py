"""Operator-reviewed, pinned synthetic step activation and controlled composition."""

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated, Literal

from pydantic import Field
from sqlalchemy import (
    Column,
    DateTime,
    Engine,
    Integer,
    MetaData,
    String,
    Table,
    select,
    text,
    update,
)
from sqlalchemy.dialects.postgresql import JSONB, insert

from actual.core.primitives import ActorId, Contract, Digest, WorkspaceId, content_digest
from actual.worklab.shadow import Comparison

from .approval import ApprovalService, Dispatcher, FakeWriter
from .connectors import Access, Authorizer, FakeReader, LocalPolicy, ReadConnector, ToolError
from .ir import Name, Workflow
from .runtime import Runtime
from .storage import Conflict, Store


class Activation(Contract):
    workflow_digest: Digest
    step: Name
    capability: Literal["fake_read", "fake_write"]
    state: Literal["disabled", "shadow", "enabled"]
    principal: ActorId
    evidence_digest: Digest
    revision: Annotated[int, Field(ge=1)]


metadata = MetaData()
schema = Table("actual_activation_schema", metadata, Column("version", Integer, primary_key=True))
records = Table(
    "actual_step_activation",
    metadata,
    Column("owner", String(64), primary_key=True),
    Column("workflow", String(64), primary_key=True),
    Column("step", String(48), primary_key=True),
    Column("payload", JSONB, nullable=False),
    Column("revision", Integer, nullable=False),
)
audit = Table(
    "actual_activation_audit",
    metadata,
    Column("owner", String(64), primary_key=True),
    Column("workflow", String(64), primary_key=True),
    Column("step", String(48), primary_key=True),
    Column("revision", Integer, primary_key=True),
    Column("actor", String(64), nullable=False),
    Column("state", String(16), nullable=False),
    Column("evidence", String(64), nullable=False),
    Column("at", DateTime(timezone=True), nullable=False),
)


def migrate(engine: Engine) -> None:
    if engine.dialect.name != "postgresql":
        raise ValueError("PostgreSQL required")
    with engine.begin() as connection:
        connection.execute(text("SELECT pg_advisory_xact_lock(734016001)"))
        metadata.create_all(connection)
        found = connection.execute(select(schema.c.version)).scalars().all()
        if found and found != [1]:
            raise Conflict("Unsupported activation migration version")
        if not found:
            connection.execute(schema.insert().values(version=1))


class ActivationStore:
    def __init__(self, engine: Engine, owner: WorkspaceId, actor: ActorId, permission: Authorizer):
        self.engine, self.owner = engine, WorkspaceId.model_validate(owner)
        self.actor, self.permission = ActorId.model_validate(actor), permission

    def set(
        self,
        workflow: Workflow,
        step_id: str,
        state: Literal["disabled", "shadow", "enabled"],
        evidence: Comparison,
        reviewed_digest: str,
        expected_revision: int,
        now: datetime,
    ) -> Activation:
        workflow, evidence = Workflow.model_validate(workflow), Comparison.model_validate(evidence)
        step = next(s for s in workflow.steps if s.id == step_id)
        if (
            step.capability not in ("fake_read", "fake_write")
            or evidence.workflow_digest != workflow.digest
            or evidence.produced.definition_digest != workflow.digest
        ):
            raise ToolError("denied")
        digest = content_digest(evidence.model_dump(mode="json"))
        if digest != reviewed_digest:
            raise Conflict("Activation evidence changed")
        name: Literal["fake_read", "fake_write"] = (
            "fake_read" if step.capability == "fake_read" else "fake_write"
        )
        access = Access(
            workspace_id=self.owner,
            principal_id=self.actor,
            capability=name,
            resource="synthetic_inbox" if step.capability == "fake_write" else "synthetic_record",
            workflow_digest=workflow.digest,
            step=step.id,
        )
        if not self.permission.allows(access):
            raise ToolError("denied")
        record = Activation(
            workflow_digest=workflow.digest,
            step=step.id,
            capability=name,
            state=state,
            principal=self.actor,
            evidence_digest=digest,
            revision=expected_revision + 1,
        )
        scope = (
            (records.c.owner == self.owner.root)
            & (records.c.workflow == workflow.digest)
            & (records.c.step == step.id)
        )
        with self.engine.begin() as connection:
            connection.execute(
                insert(records)
                .values(
                    owner=self.owner.root,
                    workflow=workflow.digest,
                    step=step.id,
                    payload=record.model_dump(mode="json"),
                    revision=0,
                )
                .on_conflict_do_nothing()
            )
            previous = connection.execute(
                select(records.c.revision).where(scope).with_for_update()
            ).scalar_one()
            if previous != expected_revision:
                raise Conflict("Stale activation revision")
            connection.execute(
                update(records)
                .where(scope)
                .values(payload=record.model_dump(mode="json"), revision=record.revision)
            )
            connection.execute(
                audit.insert().values(
                    owner=self.owner.root,
                    workflow=workflow.digest,
                    step=step.id,
                    revision=record.revision,
                    actor=self.actor.root,
                    state=state,
                    evidence=digest,
                    at=now,
                )
            )
        return record

    def allows(self, access: Access) -> bool:
        if (
            access.workspace_id != self.owner
            or access.principal_id != self.actor
            or access.workflow_digest is None
            or access.step is None
        ):
            return False
        with self.engine.connect() as connection:
            payload = connection.execute(
                select(records.c.payload).where(
                    records.c.owner == self.owner.root,
                    records.c.workflow == access.workflow_digest,
                    records.c.step == access.step,
                )
            ).scalar_one_or_none()
        if payload is None:
            return False
        record = Activation.model_validate_json(json.dumps(payload))
        return (
            record.state == "enabled"
            and record.principal == access.principal_id
            and record.capability == access.capability
        )


class ControlledAuthorizer:
    def __init__(self, permission: Authorizer, activations: ActivationStore):
        self.permission, self.activations = permission, activations

    def allows(self, access: Access) -> bool:
        return self.permission.allows(access) and self.activations.allows(access)


@dataclass(frozen=True)
class Controlled:
    runtime: Runtime
    approvals: ApprovalService
    activations: ActivationStore
    permission: LocalPolicy


def controlled(
    engine: Engine,
    owner: WorkspaceId,
    actor: ActorId,
    permissions: frozenset[str] = frozenset(),
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> Controlled:
    """Synthetic-only application composition. No migrations or implicit activation."""
    store = Store(engine, owner)
    permission = LocalPolicy(owner, actor, permissions)
    activations = ActivationStore(engine, owner, actor, permission)
    authority = ControlledAuthorizer(permission, activations)
    approvals = ApprovalService(store, actor, authority)
    runtime = Runtime(
        store,
        approvals,
        clock=clock,
        connector=ReadConnector(FakeReader(), actor, authority),
        effects=Dispatcher(approvals, FakeWriter(engine), clock=clock),
    )
    return Controlled(runtime, approvals, activations, permission)
