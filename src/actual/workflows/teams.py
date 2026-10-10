"""Small synthetic session/membership boundary over the existing controlled engine."""

import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated, Literal, Self
from uuid import uuid4

from pydantic import Field, SecretStr, model_validator
from sqlalchemy import (
    Column,
    Connection,
    DateTime,
    Engine,
    Integer,
    MetaData,
    String,
    Table,
    UniqueConstraint,
    select,
    text,
    update,
)
from sqlalchemy.dialects.postgresql import JSONB, insert
from sqlalchemy.exc import NoResultFound

from actual.core.primitives import ActorId, Contract, WorkspaceId, content_digest
from actual.worklab.shadow import Comparison

from .activation import Activation, ActivationStore, ControlledAuthorizer
from .approval import Approval, ApprovalService, BusinessIntent, Dispatcher, FakeWriter, Preview
from .connectors import Access, FakeReader, ReadConnector, ToolError
from .ir import Name, Workflow
from .runtime import Runtime
from .schema_guard import verify
from .state import Run, Value
from .storage import Conflict, Store

type Role = Literal["viewer", "operator", "reviewer", "admin"]
type Capability = Literal["fake_read", "fake_write"]


class Member(Contract):
    principal: ActorId
    role: Role
    active: bool = True


class ConnectorReference(Contract):
    id: Name
    capability: Capability
    account: Literal["synthetic_account"] = "synthetic_account"
    resource: Literal["synthetic_record", "synthetic_hostile", "synthetic_inbox"]

    @model_validator(mode="after")
    def scoped(self) -> Self:
        if (self.capability == "fake_write") != (self.resource == "synthetic_inbox"):
            raise ValueError("Connector scope mismatch")
        return self


class Organization(Contract):
    id: Name
    classification: Literal["synthetic"] = "synthetic"
    revision: Annotated[int, Field(ge=1)] = 1
    capabilities: Annotated[tuple[Capability, ...], Field(max_length=2)] = ()
    administrators: Annotated[tuple[ActorId, ...], Field(max_length=8)] = ()

    @model_validator(mode="after")
    def unique(self) -> Self:
        if len(set(self.capabilities)) != len(self.capabilities):
            raise ValueError("Duplicate organization permission")
        if len({actor.root for actor in self.administrators}) != len(self.administrators):
            raise ValueError("Duplicate organization administrator")
        return self


class Workspace(Contract):
    id: WorkspaceId
    organization: Name
    classification: Literal["synthetic"] = "synthetic"
    revision: Annotated[int, Field(ge=1)] = 1
    members: Annotated[tuple[Member, ...], Field(max_length=32)]
    connectors: Annotated[tuple[ConnectorReference, ...], Field(max_length=8)] = ()

    @model_validator(mode="after")
    def unique(self) -> Self:
        if len({m.principal.root for m in self.members}) != len(self.members):
            raise ValueError("Duplicate workspace principal")
        if len({c.id for c in self.connectors}) != len(self.connectors):
            raise ValueError("Duplicate connector reference")
        if not any(m.active and m.role == "admin" for m in self.members):
            raise ValueError("An active workspace administrator is required")
        return self


metadata = MetaData()
schema = Table("actual_team_schema", metadata, Column("version", Integer, primary_key=True))
organizations = Table(
    "actual_organizations",
    metadata,
    Column("id", String(48), primary_key=True),
    Column("revision", Integer, nullable=False),
    Column("payload", JSONB, nullable=False),
)
workspaces = Table(
    "actual_team_workspaces",
    metadata,
    Column("owner", String(64), primary_key=True),
    Column("organization", String(48), nullable=False),
    Column("revision", Integer, nullable=False),
    Column("payload", JSONB, nullable=False),
)
sessions = Table(
    "actual_synthetic_sessions",
    metadata,
    Column("digest", String(64), primary_key=True),
    Column("actor", String(64), nullable=False),
    Column("expires", DateTime(timezone=True), nullable=False),
    Column("active", Integer, nullable=False),
)
catalog = Table(
    "actual_shared_workflows",
    metadata,
    Column("owner", String(64), primary_key=True),
    Column("digest", String(64), primary_key=True),
    Column("name", String(48), nullable=False),
    Column("version", Integer, nullable=False),
    Column("payload", JSONB, nullable=False),
    UniqueConstraint("owner", "name", "version"),
)
audit = Table(
    "actual_team_audit",
    metadata,
    Column("owner", String(64), primary_key=True),
    Column("id", String(48), primary_key=True),
    Column("actor", String(64), nullable=False),
    Column("at", DateTime(timezone=True), nullable=False),
    Column("action", String(48), nullable=False),
    Column("digest", String(64), nullable=False),
    Column("revision", Integer, nullable=False),
)


def migrate(engine: Engine) -> None:
    if engine.dialect.name != "postgresql":
        raise ValueError("PostgreSQL required")
    with engine.begin() as connection:
        connection.execute(text("SELECT pg_advisory_xact_lock(734026001)"))
        metadata.create_all(connection)
        verify(connection, metadata)
        found = connection.execute(select(schema.c.version)).scalars().all()
        if found and found != [1]:
            raise Conflict("Unsupported teams migration version")
        if not found:
            connection.execute(schema.insert().values(version=1))


def token_digest(token: SecretStr) -> str:
    value = token.get_secret_value()
    if re.fullmatch(r"synthetic_session_[0-9a-f]{64}", value) is None:
        raise ToolError("denied")
    return content_digest(value)


@dataclass(frozen=True)
class Context:
    actor: ActorId
    workspace: Workspace
    organization: Organization
    member: Member


def member(workspace: Workspace, actor: ActorId) -> Member:
    found = next((m for m in workspace.members if m.principal == actor and m.active), None)
    if found is None:
        raise ToolError("denied")
    return found


class Directory:
    """Operator provisioning is trusted local configuration, not a request or model port."""

    def __init__(self, engine: Engine):
        self.engine = engine

    def provision(self, organization: Organization, workspace: Workspace) -> None:
        organization = Organization.model_validate(organization)
        workspace = Workspace.model_validate(workspace)
        if workspace.organization != organization.id:
            raise Conflict("Organization scope mismatch")
        with self.engine.begin() as connection:
            for table, values in (
                (
                    organizations,
                    dict(
                        id=organization.id,
                        revision=organization.revision,
                        payload=organization.model_dump(mode="json"),
                    ),
                ),
                (
                    workspaces,
                    dict(
                        owner=workspace.id.root,
                        organization=organization.id,
                        revision=workspace.revision,
                        payload=workspace.model_dump(mode="json"),
                    ),
                ),
            ):
                connection.execute(insert(table).values(**values).on_conflict_do_nothing())
            recorded_org = connection.execute(
                select(organizations.c.payload).where(organizations.c.id == organization.id)
            ).scalar_one()
            recorded_workspace = connection.execute(
                select(workspaces.c.payload).where(workspaces.c.owner == workspace.id.root)
            ).scalar_one()
            if recorded_org != organization.model_dump(
                mode="json"
            ) or recorded_workspace != workspace.model_dump(mode="json"):
                raise Conflict("Provisioning cannot overwrite existing authority")

    def issue(self, token: SecretStr, actor: ActorId, expires: datetime) -> None:
        digest = token_digest(token)
        actor = ActorId.model_validate(actor)
        if expires.tzinfo is None:
            raise ValueError("UTC-aware session expiry required")
        with self.engine.begin() as connection:
            connection.execute(
                sessions.insert().values(
                    digest=digest,
                    actor=actor.root,
                    expires=expires,
                    active=1,
                )
            )

    def revoke(self, token: SecretStr) -> None:
        with self.engine.begin() as connection:
            connection.execute(
                update(sessions).where(sessions.c.digest == token_digest(token)).values(active=0)
            )

    def workspace(self, owner: WorkspaceId) -> tuple[Workspace, Organization]:
        with self.engine.connect() as connection:
            row = (
                connection.execute(select(workspaces).where(workspaces.c.owner == owner.root))
                .mappings()
                .one()
            )
            workspace = Workspace.model_validate_json(json.dumps(row["payload"]))
            org_row = (
                connection.execute(
                    select(organizations).where(organizations.c.id == row["organization"])
                )
                .mappings()
                .one()
            )
        organization = Organization.model_validate_json(json.dumps(org_row["payload"]))
        if (
            workspace.id != owner
            or workspace.organization != row["organization"]
            or workspace.revision != row["revision"]
            or organization.id != row["organization"]
            or organization.revision != org_row["revision"]
        ):
            raise ToolError("denied")
        return workspace, organization

    def resolve(self, token: SecretStr, owner: WorkspaceId, now: datetime) -> Context:
        owner = WorkspaceId.model_validate(owner)
        try:
            with self.engine.connect() as connection:
                session = (
                    connection.execute(
                        select(sessions).where(
                            sessions.c.digest == token_digest(token),
                            sessions.c.active == 1,
                            sessions.c.expires > now,
                        )
                    )
                    .mappings()
                    .one()
                )
            workspace, organization = self.workspace(owner)
            actor = ActorId(session["actor"])
            return Context(actor, workspace, organization, member(workspace, actor))
        except NoResultFound:
            raise ToolError("denied") from None

    def reviewer(self, owner: WorkspaceId, actor: ActorId, policy_version: int) -> bool:
        try:
            workspace, organization = self.workspace(owner)
            return organization.revision == policy_version and member(workspace, actor).role in (
                "reviewer",
                "admin",
            )
        except (NoResultFound, ToolError):
            return False


class TeamPermission:
    def __init__(
        self,
        directory: Directory,
        token: SecretStr,
        owner: WorkspaceId,
        principal: ActorId,
        clock: Callable[[], datetime],
    ):
        self.directory, self.token, self.owner = directory, token, owner
        self.principal, self.clock = principal, clock

    def allows(self, access: Access) -> bool:
        try:
            context = self.directory.resolve(self.token, self.owner, self.clock())
            subject = member(context.workspace, self.principal)
            actor_may_review = context.member.role == "admin" or (
                context.member.role == "reviewer" and access.capability == "fake_write"
            )
            return (
                access.workspace_id == self.owner
                and access.principal_id == self.principal
                and (context.actor == self.principal or actor_may_review)
                and subject.role in ("operator", "admin")
                and access.policy_version == context.organization.revision
                and access.capability in context.organization.capabilities
                and any(
                    c.capability == access.capability and c.resource == access.resource
                    for c in context.workspace.connectors
                )
            )
        except (ToolError, NoResultFound):
            return False


class Teams:
    """Synthetic application boundary: session is verified for every operation/dispatch."""

    def __init__(
        self, directory: Directory, clock: Callable[[], datetime] = lambda: datetime.now(UTC)
    ):
        self.directory, self.engine, self.clock = directory, directory.engine, clock

    def context(self, token: SecretStr, owner: WorkspaceId, roles: tuple[Role, ...]) -> Context:
        context = self.directory.resolve(token, owner, self.clock())
        if context.member.role not in roles:
            raise ToolError("denied")
        return context

    def _workflow(self, owner: WorkspaceId, digest: str) -> Workflow:
        with self.engine.connect() as connection:
            row = (
                connection.execute(
                    select(catalog).where(catalog.c.owner == owner.root, catalog.c.digest == digest)
                )
                .mappings()
                .one()
            )
        workflow = Workflow.model_validate_json(json.dumps(row["payload"]))
        if (
            workflow.digest != digest
            or workflow.id != row["name"]
            or workflow.version != row["version"]
        ):
            raise Conflict("Shared workflow identity mismatch")
        return workflow

    def publish(self, token: SecretStr, owner: WorkspaceId, workflow: Workflow) -> None:
        context = self.context(token, owner, ("operator", "admin"))
        workflow = Workflow.model_validate(workflow)
        with self.engine.begin() as connection:
            connection.execute(
                insert(catalog)
                .values(
                    owner=owner.root,
                    digest=workflow.digest,
                    name=workflow.id,
                    version=workflow.version,
                    payload=workflow.model_dump(mode="json"),
                )
                .on_conflict_do_nothing()
            )
            digest = connection.execute(
                select(catalog.c.digest).where(
                    catalog.c.owner == owner.root,
                    catalog.c.name == workflow.id,
                    catalog.c.version == workflow.version,
                )
            ).scalar_one()
            if digest != workflow.digest:
                raise Conflict("Immutable shared workflow version")
            self._audit(connection, context, "publish", workflow.digest, workflow.version)

    def _audit(
        self, connection: Connection, context: Context, action: str, digest: str, revision: int
    ) -> None:
        connection.execute(
            audit.insert().values(
                owner=context.workspace.id.root,
                id="audit_" + uuid4().hex,
                actor=context.actor.root,
                at=self.clock(),
                action=action,
                digest=digest,
                revision=revision,
            )
        )

    def update_workspace(
        self, token: SecretStr, workspace: Workspace, expected_revision: int
    ) -> None:
        workspace = Workspace.model_validate(workspace)
        context = self.context(token, workspace.id, ("admin",))
        if (
            workspace.organization != context.organization.id
            or workspace.revision != expected_revision + 1
        ):
            raise Conflict("Workspace authority revision mismatch")
        with self.engine.begin() as connection:
            changed = connection.execute(
                update(workspaces)
                .where(
                    workspaces.c.owner == workspace.id.root,
                    workspaces.c.revision == expected_revision,
                )
                .values(payload=workspace.model_dump(mode="json"), revision=workspace.revision)
            )
            if changed.rowcount != 1:
                raise Conflict("Stale workspace authority")
            self._audit(
                connection,
                context,
                "workspace_policy",
                content_digest(workspace.model_dump(mode="json")),
                workspace.revision,
            )

    def start(
        self,
        token: SecretStr,
        owner: WorkspaceId,
        digest: str,
        trigger: str,
        values: tuple[Value, ...],
    ) -> Run:
        context = self.context(token, owner, ("operator", "admin"))
        return Store(self.engine, owner).start(
            self._workflow(owner, digest), trigger, values, self.clock(), principal=context.actor
        )

    def update_policy(
        self,
        token: SecretStr,
        owner: WorkspaceId,
        organization: Organization,
        expected_revision: int,
    ) -> None:
        organization = Organization.model_validate(organization)
        context = self.context(token, owner, ("admin",))
        if context.actor not in context.organization.administrators:
            raise ToolError("denied")
        if (
            organization.id != context.organization.id
            or organization.revision != expected_revision + 1
        ):
            raise Conflict("Organization authority revision mismatch")
        with self.engine.begin() as connection:
            changed = connection.execute(
                update(organizations)
                .where(
                    organizations.c.id == organization.id,
                    organizations.c.revision == expected_revision,
                )
                .values(
                    payload=organization.model_dump(mode="json"), revision=organization.revision
                )
            )
            if changed.rowcount != 1:
                raise Conflict("Stale organization authority")
            self._audit(
                connection,
                context,
                "organization_policy",
                content_digest(organization.model_dump(mode="json")),
                organization.revision,
            )

    def load(self, token: SecretStr, owner: WorkspaceId, identifier: str) -> Run:
        self.context(token, owner, ("viewer", "operator", "reviewer", "admin"))
        try:
            run = Store(self.engine, owner).load(identifier)
            self._workflow(owner, run.definition_digest)
            if run.initiator is None:
                raise ToolError("denied")
            return run
        except NoResultFound:
            raise ToolError("denied") from None

    def _composition(
        self, token: SecretStr, context: Context, principal: ActorId
    ) -> tuple[Runtime, ApprovalService]:
        owner = context.workspace.id
        permission = TeamPermission(self.directory, token, owner, principal, self.clock)
        activation = ActivationStore(
            self.engine,
            owner,
            context.actor,
            permission,
            principal=principal,
            policy_version=context.organization.revision,
        )
        authority = ControlledAuthorizer(permission, activation)
        service = ApprovalService(
            Store(self.engine, owner),
            context.actor,
            authority,
            context.organization.revision,
            principal=principal,
            approval_authority=lambda approval: self.directory.reviewer(
                owner, approval.approver, approval.binding.policy_version
            ),
        )
        runtime = Runtime(
            service.store,
            service,
            clock=self.clock,
            connector=ReadConnector(
                FakeReader(), principal, authority, context.organization.revision
            ),
            effects=Dispatcher(service, FakeWriter(self.engine), clock=self.clock),
        )
        return runtime, service

    def tick(self, token: SecretStr, owner: WorkspaceId, identifier: str) -> Run:
        context = self.context(token, owner, ("operator", "admin"))
        run = self.load(token, owner, identifier)
        if run.initiator != context.actor:
            raise ToolError("denied")
        runtime, _ = self._composition(token, context, context.actor)
        return runtime.tick(identifier)

    def preview(
        self, token: SecretStr, owner: WorkspaceId, identifier: str, business: BusinessIntent
    ) -> Preview:
        context = self.context(token, owner, ("reviewer", "admin"))
        run = self.load(token, owner, identifier)
        assert run.initiator is not None
        _, service = self._composition(token, context, run.initiator)
        return service.preview(identifier, business, self.clock())

    def approve(
        self, token: SecretStr, owner: WorkspaceId, preview: Preview, reviewed_digest: str
    ) -> Approval:
        context = self.context(token, owner, ("reviewer", "admin"))
        preview = Preview.model_validate(preview)
        if preview.binding.workspace_id != owner:
            raise ToolError("denied")
        run = self.load(token, owner, preview.binding.run)
        assert run.initiator is not None
        _, service = self._composition(token, context, run.initiator)
        return service.approve(preview, reviewed_digest, self.clock())

    def deny(self, token: SecretStr, owner: WorkspaceId, identifier: str, revision: int) -> Run:
        context = self.context(token, owner, ("reviewer", "admin"))
        run = self.load(token, owner, identifier)
        assert run.initiator is not None
        _, service = self._composition(token, context, run.initiator)
        return service.deny(identifier, revision, self.clock())

    def revoke_approval(self, token: SecretStr, owner: WorkspaceId, identifier: str) -> None:
        context = self.context(token, owner, ("reviewer", "admin"))
        _, service = self._composition(token, context, context.actor)
        service.revoke(identifier, self.clock())

    def activate(
        self,
        token: SecretStr,
        owner: WorkspaceId,
        digest: str,
        step: str,
        principal: ActorId,
        evidence: Comparison,
        reviewed_digest: str,
        expected_revision: int,
        state: Literal["disabled", "shadow", "enabled"] = "enabled",
    ) -> Activation:
        context = self.context(token, owner, ("admin",))
        permission = TeamPermission(self.directory, token, owner, principal, self.clock)
        activation = ActivationStore(
            self.engine,
            owner,
            context.actor,
            permission,
            principal=principal,
            policy_version=context.organization.revision,
        )
        return activation.set(
            self._workflow(owner, digest),
            step,
            state,
            evidence,
            reviewed_digest,
            expected_revision,
            self.clock(),
        )
