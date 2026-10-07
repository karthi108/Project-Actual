"""Exact human approval, serialized intent reservation and conservative fake dispatch."""

import json
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import uuid4

from pydantic import Field, ValidationError
from sqlalchemy import (
    Column,
    Connection,
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
from sqlalchemy.exc import NoResultFound

from actual.core.primitives import ActorId, Contract, Digest, Instant, WorkspaceId, content_digest

from .connectors import Access, Authorizer, ToolError, WriteInput, WriteOutput, WritePort
from .ir import Name, Step, Workflow
from .runtime import inputs, route
from .schema_guard import verify
from .state import Run, Value
from .storage import Conflict, Store, runs
from .storage import audit as run_audit

metadata = MetaData()
schema = Table("actual_approval_schema", metadata, Column("version", Integer, primary_key=True))
approvals = Table(
    "actual_effect_approvals",
    metadata,
    Column("owner", String(64), primary_key=True),
    Column("id", String(48), primary_key=True),
    Column("run", String(48), nullable=False),
    Column("step", String(48), nullable=False),
    Column("payload", JSONB, nullable=False),
    Column("active", Integer, nullable=False),
    Column("intent", String(64)),
)
intents = Table(
    "actual_effect_intents",
    metadata,
    Column("owner", String(64), primary_key=True),
    Column("key", String(64), primary_key=True),
    Column("arguments_digest", String(64), nullable=False),
    Column("status", String(32), nullable=False),
    Column("receipt", String(48)),
)
audit = Table(
    "actual_effect_audit",
    metadata,
    Column("owner", String(64), primary_key=True),
    Column("id", String(48), primary_key=True),
    Column("at", DateTime(timezone=True), nullable=False),
    Column("actor", String(64), nullable=False),
    Column("run", String(48), nullable=False),
    Column("workflow", String(64), nullable=False),
    Column("step", String(48), nullable=False),
    Column("intent", String(64), nullable=False),
    Column("approval", String(48), nullable=False),
    Column("binding", String(64), nullable=False),
    Column("authority", String(64), nullable=False),
    Column("state", String(32), nullable=False),
)
provider = Table(
    "actual_synthetic_provider_receipts",
    metadata,
    Column("key", String(64), primary_key=True),
    Column("arguments_digest", String(64), nullable=False),
    Column("receipt", String(48), nullable=False),
)


def migrate(engine: Engine) -> None:
    if engine.dialect.name != "postgresql":
        raise ValueError("PostgreSQL required")
    with engine.begin() as connection:
        connection.execute(text("SELECT pg_advisory_xact_lock(734013001)"))
        metadata.create_all(connection)
        verify(connection, metadata)
        found = connection.execute(select(schema.c.version)).scalars().all()
        if found and found != [1]:
            raise Conflict("Unsupported approval migration version")
        if not found:
            connection.execute(schema.insert().values(version=1))


class BusinessIntent(Contract):
    account: Literal["synthetic_account"] = "synthetic_account"
    business_object: Name
    submission: Name

    def key(self, owner: WorkspaceId, destination: str) -> str:
        return content_digest(
            {
                "owner": owner.root,
                "account": self.account,
                "action": "fake_write",
                "destination": destination,
                "object": self.business_object,
                "submission": self.submission,
            }
        )


class ActionBinding(Contract):
    workspace_id: WorkspaceId
    principal_id: ActorId
    run: Name
    workflow_digest: Digest
    workflow_version: Annotated[int, Field(ge=1)]
    step: Name
    capability: Literal["fake_write"] = "fake_write"
    destination: Literal["synthetic_inbox"]
    arguments_digest: Digest
    artifact_digest: Digest
    business: BusinessIntent
    intent_digest: Digest
    policy_version: Annotated[int, Field(ge=1)]

    def access(self) -> Access:
        return Access(
            workspace_id=self.workspace_id,
            principal_id=self.principal_id,
            capability=self.capability,
            resource=self.destination,
            policy_version=self.policy_version,
            workflow_digest=self.workflow_digest,
            step=self.step,
            arguments_digest=self.arguments_digest,
            intent_digest=self.intent_digest,
        )

    @property
    def digest(self) -> str:
        return content_digest(self.model_dump(mode="json"))


class Preview(Contract):
    binding: ActionBinding
    payload: WriteInput
    revision: Annotated[int, Field(ge=1)]
    expires_at: Instant

    @property
    def digest(self) -> str:
        return content_digest(self.model_dump(mode="json"))


class Approval(Contract):
    id: Name
    binding: ActionBinding
    approver: ActorId
    expires_at: Instant
    reviewed_digest: Digest


def approval_seal(approval: Approval) -> str:
    return content_digest(
        {
            "access": approval.binding.access().model_dump(mode="json"),
            "approval": approval.model_dump(mode="json"),
        }
    )


def request(values: tuple[Value, ...]) -> WriteInput:
    if len(values) != 2 or len({value.name for value in values}) != 2:
        raise ToolError("denied")
    try:
        return WriteInput.model_validate({v.name: v.value for v in values})
    except ValidationError:
        raise ToolError("denied") from None


def bound(
    run: Run,
    workflow: Workflow,
    step: Step,
    payload: WriteInput,
    business: BusinessIntent,
    actor: ActorId,
    policy_version: int,
) -> ActionBinding:
    if step.kind != "tool" or step.capability != "fake_write" or step.effect != "EXTERNAL_WRITE":
        raise ToolError("denied")
    return ActionBinding(
        workspace_id=run.workspace_id,
        principal_id=actor,
        run=run.id,
        workflow_digest=workflow.digest,
        workflow_version=workflow.version,
        step=step.id,
        destination=payload.destination,
        arguments_digest=content_digest(payload.model_dump(mode="json")),
        artifact_digest=content_digest(payload.text),
        business=business,
        intent_digest=business.key(run.workspace_id, payload.destination),
        policy_version=policy_version,
    )


class ApprovalService:
    """Actor and authorizer are installed by the trusted local application boundary."""

    def __init__(
        self, store: Store, actor: ActorId, authorizer: Authorizer, policy_version: int = 1
    ):
        self.store, self.actor, self.authorizer = store, ActorId.model_validate(actor), authorizer
        self.policy_version = policy_version

    def _locked(self, connection: Connection, identifier: str, revision: int) -> Run:
        row = (
            connection.execute(select(runs).where(self.store._scope(identifier)).with_for_update())
            .mappings()
            .one()
        )
        run = self.store._run(row)
        if (
            run.workspace_id.root != self.store.owner
            or run.id != identifier
            or run.revision != row["revision"]
            or run.revision != revision
        ):
            raise Conflict("Run identity or revision conflict")
        return run

    def _action(self, run: Run) -> tuple[Workflow, Step, WriteInput]:
        workflow = self.store.definition(run.definition_digest)
        gate = next(s for s in workflow.steps if s.id == run.current)
        if gate.kind != "human_approval" or run.status != "human_wait":
            raise Conflict("Exact active human wait required")
        step = next(s for s in workflow.steps if s.id == gate.protects)
        try:
            return workflow, step, request(inputs(run, step))
        except (StopIteration, ToolError):
            raise Conflict("Consequential inputs unavailable") from None

    def allows(self, run: Run, workflow: Workflow, step: Step) -> bool:
        if step.protects is None:
            return False
        action = next(s for s in workflow.steps if s.id == step.protects)
        try:
            payload = request(inputs(run, action))
            return self.authorizer.allows(
                Access(
                    workspace_id=run.workspace_id,
                    principal_id=self.actor,
                    capability="fake_write",
                    resource=payload.destination,
                    policy_version=self.policy_version,
                    workflow_digest=workflow.digest,
                    step=action.id,
                    arguments_digest=content_digest(payload.model_dump(mode="json")),
                )
            )
        except (ToolError, StopIteration):
            return False

    def preview(self, identifier: str, business: BusinessIntent, now: datetime) -> Preview:
        run = self.store.load(identifier)
        workflow, step, payload = self._action(run)
        if run.due_at is None or run.due_at <= now:
            raise Conflict("Human wait expired")
        binding = bound(
            run,
            workflow,
            step,
            payload,
            BusinessIntent.model_validate(business),
            self.actor,
            self.policy_version,
        )
        if not self.authorizer.allows(binding.access()):
            raise ToolError("denied")
        return Preview(
            binding=binding, payload=payload, revision=run.revision, expires_at=run.due_at
        )

    def _event(self, connection: Connection, approval: Approval, state: str, now: datetime) -> None:
        b = approval.binding
        connection.execute(
            audit.insert().values(
                owner=self.store.owner,
                id="audit_" + uuid4().hex,
                at=now,
                actor=self.actor.root,
                run=b.run,
                workflow=b.workflow_digest,
                step=b.step,
                intent=b.intent_digest,
                approval=approval.id,
                binding=b.digest,
                authority=(
                    approval_seal(approval)
                    if state == "approved"
                    else content_digest(b.access().model_dump(mode="json"))
                ),
                state=state,
            )
        )

    def _save_gate(self, connection: Connection, run: Run, outcome: str, now: datetime) -> Run:
        changed = route(self.store.definition(run.definition_digest), run, outcome, now)
        connection.execute(
            update(runs)
            .where(self.store._scope(run.id))
            .values(
                payload=changed.model_dump(mode="json"),
                revision=changed.revision,
                lease_until=None,
                fence=runs.c.fence + 1,
            )
        )
        connection.execute(
            run_audit.insert().values(
                owner=self.store.owner,
                run=run.id,
                revision=changed.revision,
                at=now,
                step=run.current,
                status=changed.status,
                definition_digest=run.definition_digest,
            )
        )
        return changed

    def approve(self, preview: Preview, reviewed_digest: str, now: datetime) -> Approval:
        preview = Preview.model_validate(preview)
        with self.store.engine.begin() as connection:
            run = self._locked(connection, preview.binding.run, preview.revision)
            current = self.preview(run.id, preview.binding.business, now)
            if current != preview or reviewed_digest != current.digest:
                raise Conflict("Reviewed action changed")
            approval = Approval(
                id="approval_" + uuid4().hex,
                binding=current.binding,
                approver=self.actor,
                expires_at=current.expires_at,
                reviewed_digest=reviewed_digest,
            )
            connection.execute(
                approvals.insert().values(
                    owner=self.store.owner,
                    id=approval.id,
                    run=run.id,
                    step=approval.binding.step,
                    payload=approval.model_dump(mode="json"),
                    active=1,
                )
            )
            self._save_gate(connection, run, "approved", now)
            self._event(connection, approval, "approved", now)
            return approval

    def deny(self, identifier: str, revision: int, now: datetime) -> Run:
        with self.store.engine.begin() as connection:
            run = self._locked(connection, identifier, revision)
            self._action(run)
            return self._save_gate(connection, run, "denied", now)

    def revoke(self, identifier: str, now: datetime) -> None:
        with self.store.engine.begin() as connection:
            row = (
                connection.execute(
                    select(approvals)
                    .where(approvals.c.owner == self.store.owner, approvals.c.id == identifier)
                    .with_for_update()
                )
                .mappings()
                .one()
            )
            approval = Approval.model_validate_json(json.dumps(row["payload"]))
            if approval.approver != self.actor:
                raise ToolError("denied")
            connection.execute(
                update(approvals)
                .where(approvals.c.owner == self.store.owner, approvals.c.id == identifier)
                .values(active=0)
            )
            self._event(connection, approval, "revoked", now)


class FakeWriter:
    """Separate durable fake provider transaction models a lost acknowledgement."""

    def __init__(self, engine: Engine, lose_response: bool = False):
        self.engine, self.lose_response = engine, lose_response

    def write(self, payload: WriteInput, key: str) -> WriteOutput:
        payload = WriteInput.model_validate(payload)
        digest = content_digest(payload.model_dump(mode="json"))
        with self.engine.begin() as connection:
            connection.execute(
                insert(provider)
                .values(key=key, arguments_digest=digest, receipt="receipt_" + uuid4().hex)
                .on_conflict_do_nothing()
            )
            row = connection.execute(select(provider).where(provider.c.key == key)).mappings().one()
            if row["arguments_digest"] != digest:
                raise ToolError("denied")
        if self.lose_response:
            raise ToolError("unknown_outcome")
        return WriteOutput(receipt=row["receipt"])

    def reconcile(self, key: str) -> WriteOutput | None:
        with self.engine.connect() as connection:
            receipt = connection.execute(
                select(provider.c.receipt).where(provider.c.key == key)
            ).scalar_one_or_none()
        return None if receipt is None else WriteOutput(receipt=receipt)


class Dispatcher:
    def __init__(
        self,
        service: ApprovalService,
        provider_port: WritePort,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        before_dispatch: Callable[[], None] = lambda: None,
    ):
        self.service, self.provider, self.clock, self.before_dispatch = (
            service,
            provider_port,
            clock,
            before_dispatch,
        )

    def _approval(
        self,
        connection: Connection,
        run: Run,
        step: Step,
        values: tuple[Value, ...],
        fence: int,
        now: datetime,
    ) -> Approval:
        current = self.service._locked(connection, run.id, run.revision)
        row = (
            connection.execute(select(runs).where(self.service.store._scope(run.id)))
            .mappings()
            .one()
        )
        if (
            current != run
            or run.current != step.id
            or run.status != "ready"
            or row["fence"] != fence
            or row["lease_until"] is None
            or row["lease_until"] <= now
        ):
            raise ToolError("denied")
        record = (
            connection.execute(
                select(approvals)
                .where(
                    approvals.c.owner == self.service.store.owner,
                    approvals.c.run == run.id,
                    approvals.c.step == step.id,
                )
                .with_for_update()
            )
            .mappings()
            .one()
        )
        approval = Approval.model_validate_json(json.dumps(record["payload"]))
        binding = bound(
            run,
            self.service.store.definition(run.definition_digest),
            step,
            request(values),
            approval.binding.business,
            self.service.actor,
            self.service.policy_version,
        )
        if (
            record["active"] != 1
            or approval.id != record["id"]
            or approval.expires_at <= now
            or approval.binding != binding
            or not self.service.authorizer.allows(binding.access())
        ):
            raise ToolError("denied")
        seal = connection.execute(
            select(audit.c.authority).where(
                audit.c.owner == self.service.store.owner,
                audit.c.approval == approval.id,
                audit.c.state == "approved",
            )
        ).scalar_one_or_none()
        if seal != approval_seal(approval):
            raise ToolError("denied")
        if record["intent"] is not None and record["intent"] != binding.intent_digest:
            raise ToolError("denied")
        return approval

    def _settle(self, approval: Approval, result: WriteOutput | None, now: datetime) -> None:
        with self.service.store.engine.begin() as connection:
            existing = (
                connection.execute(
                    select(intents)
                    .where(
                        intents.c.owner == self.service.store.owner,
                        intents.c.key == approval.binding.intent_digest,
                    )
                    .with_for_update()
                )
                .mappings()
                .one()
            )
            if existing["status"] == "succeeded":
                if result is not None and result.receipt != existing["receipt"]:
                    raise Conflict("Provider receipt conflict")
                return
            connection.execute(
                update(intents)
                .where(
                    intents.c.owner == self.service.store.owner,
                    intents.c.key == approval.binding.intent_digest,
                )
                .values(
                    status="succeeded" if result else "outcome_unknown",
                    receipt=result.receipt if result else None,
                )
            )
            self.service._event(
                connection, approval, "succeeded" if result else "outcome_unknown", now
            )

    def execute(
        self, run: Run, step: Step, values: tuple[Value, ...], fence: int
    ) -> tuple[Value, ...]:
        now = self.clock()
        with self.service.store.engine.begin() as connection:
            try:
                approval = self._approval(connection, run, step, values, fence, now)
            except NoResultFound:
                raise ToolError("denied") from None
            b = approval.binding
            connection.execute(
                insert(intents)
                .values(
                    owner=self.service.store.owner,
                    key=b.intent_digest,
                    arguments_digest=b.arguments_digest,
                    status="reserved",
                )
                .on_conflict_do_nothing()
            )
            intent = (
                connection.execute(
                    select(intents)
                    .where(
                        intents.c.owner == self.service.store.owner,
                        intents.c.key == b.intent_digest,
                    )
                    .with_for_update()
                )
                .mappings()
                .one()
            )
            if intent["arguments_digest"] != b.arguments_digest:
                raise ToolError("denied")
            connection.execute(
                update(approvals)
                .where(approvals.c.owner == self.service.store.owner, approvals.c.id == approval.id)
                .values(intent=b.intent_digest)
            )
            self.service._event(connection, approval, "reserved", now)
        self.before_dispatch()
        with self.service.store.engine.begin() as connection:
            approval = self._approval(connection, run, step, values, fence, self.clock())
            intent = (
                connection.execute(
                    select(intents)
                    .where(
                        intents.c.owner == self.service.store.owner,
                        intents.c.key == b.intent_digest,
                    )
                    .with_for_update()
                )
                .mappings()
                .one()
            )
            if intent["status"] == "succeeded":
                return (
                    Value(name="receipt", value=WriteOutput(receipt=intent["receipt"]).receipt),
                )
            dispatch = intent["status"] == "reserved"
            if dispatch:
                connection.execute(
                    update(intents)
                    .where(
                        intents.c.owner == self.service.store.owner,
                        intents.c.key == b.intent_digest,
                    )
                    .values(status="dispatching")
                )
                self.service._event(connection, approval, "dispatching", self.clock())
        # The committed dispatch marker is the revocation boundary. A cancellation after
        # this point can only stop local progress and request reconciliation/compensation.
        try:
            result = (
                self.provider.write(request(values), b.intent_digest)
                if dispatch
                else self.provider.reconcile(b.intent_digest)
            )
            result = None if result is None else WriteOutput.model_validate(result)
        except Exception:
            result = None
        self._settle(approval, result, self.clock())
        if result is None:
            raise ToolError("unknown_outcome")
        return (Value(name="receipt", value=result.receipt),)

    def reconcile(self, approval_id: str) -> WriteOutput | None:
        with self.service.store.engine.connect() as connection:
            payload = connection.execute(
                select(approvals.c.payload).where(
                    approvals.c.owner == self.service.store.owner, approvals.c.id == approval_id
                )
            ).scalar_one()
        approval = Approval.model_validate_json(json.dumps(payload))
        with self.service.store.engine.connect() as connection:
            status = connection.execute(
                select(intents.c.status).where(
                    intents.c.owner == self.service.store.owner,
                    intents.c.key == approval.binding.intent_digest,
                )
            ).scalar_one()
        if status not in ("dispatching", "outcome_unknown", "succeeded"):
            raise Conflict("Intent has not crossed the dispatch boundary")
        # Read-only recovery never grants permission to resend, even after revocation.
        result = self.provider.reconcile(approval.binding.intent_digest)
        result = None if result is None else WriteOutput.model_validate(result)
        self._settle(approval, result, self.clock())
        return result
