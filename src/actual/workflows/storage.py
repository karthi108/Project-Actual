"""Explicit additive workflow migration and owner-scoped serialized progress."""

import json
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy import (
    Column,
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
from sqlalchemy.engine import RowMapping
from sqlalchemy.sql.elements import ColumnElement

from actual.core.primitives import WorkspaceId, content_digest

from .ir import Workflow, value_type
from .schema_guard import verify
from .state import Run, Value

metadata = MetaData()
version = Table("actual_workflow_schema", metadata, Column("version", Integer, primary_key=True))
definitions = Table(
    "actual_workflow_definitions",
    metadata,
    Column("owner", String(64), primary_key=True),
    Column("digest", String(64), primary_key=True),
    Column("name", String(48), nullable=False),
    Column("version", Integer, nullable=False),
    Column("payload", JSONB, nullable=False),
    UniqueConstraint("owner", "name", "version"),
)
runs = Table(
    "actual_workflow_runs",
    metadata,
    Column("owner", String(64), primary_key=True),
    Column("id", String(48), primary_key=True),
    Column("workflow", String(48), nullable=False),
    Column("trigger_id", String(48), nullable=False),
    Column("trigger_digest", String(64), nullable=False),
    Column("revision", Integer, nullable=False),
    Column("payload", JSONB, nullable=False),
    Column("fence", Integer, nullable=False),
    Column("lease_until", DateTime(timezone=True)),
    UniqueConstraint("owner", "workflow", "trigger_id"),
)
audit = Table(
    "actual_workflow_audit",
    metadata,
    Column("owner", String(64), primary_key=True),
    Column("run", String(48), primary_key=True),
    Column("revision", Integer, primary_key=True),
    Column("at", DateTime(timezone=True), nullable=False),
    Column("step", String(48), nullable=False),
    Column("status", String(48), nullable=False),
    Column("definition_digest", String(64), nullable=False),
)
dead_letters = Table(
    "actual_workflow_dead_letters",
    metadata,
    Column("owner", String(64), primary_key=True),
    Column("run", String(48), primary_key=True),
    Column("definition_digest", String(64), nullable=False),
    Column("revision", Integer, nullable=False),
    Column("step", String(48), nullable=False),
    Column("code", String(48), nullable=False),
    Column("at", DateTime(timezone=True), nullable=False),
)


class Conflict(Exception):
    """Safe state conflict, without payload or database diagnostics."""


def migrate(engine: Engine) -> None:
    """Operator-invoked only; never startup DDL or accepted Career migration edits."""
    if engine.dialect.name != "postgresql":
        raise ValueError("PostgreSQL required")
    with engine.begin() as connection:
        connection.execute(text("SELECT pg_advisory_xact_lock(734011001)"))
        metadata.create_all(connection)
        verify(connection, metadata)
        found = connection.execute(select(version.c.version)).scalars().all()
        if found and found not in ([1], [2]):
            raise Conflict("Unsupported workflow migration version")
        if not found:
            connection.execute(version.insert().values(version=2))
        elif found == [1]:
            connection.execute(update(version).values(version=2))


def decode(payload: object) -> Run:
    return Run.model_validate_json(json.dumps(payload))


class Store:
    def __init__(self, engine: Engine, owner: WorkspaceId):
        self.engine = engine
        self.owner = WorkspaceId.model_validate(owner).root

    def _scope(self, identifier: str) -> ColumnElement[bool]:
        return (runs.c.owner == self.owner) & (runs.c.id == identifier)

    def _run(self, row: RowMapping) -> Run:
        run = decode(row["payload"])
        if (
            run.workspace_id.root != self.owner
            or run.workspace_id.root != row["owner"]
            or run.id != row["id"]
            or run.revision != row["revision"]
            or run.trigger_id != row["trigger_id"]
            or content_digest(tuple(v.model_dump(mode="json") for v in run.trigger))
            != row["trigger_digest"]
        ):
            raise Conflict("Stored run identity conflict")
        return run

    def _definition(self, row: RowMapping, digest: str) -> Workflow:
        workflow = Workflow.model_validate_json(json.dumps(row["payload"]))
        if (
            workflow.digest != digest
            or row["owner"] != self.owner
            or workflow.id != row["name"]
            or workflow.version != row["version"]
        ):
            raise Conflict("Definition identity mismatch")
        return workflow

    def definition(self, digest: str) -> Workflow:
        with self.engine.connect() as connection:
            row = (
                connection.execute(
                    select(definitions).where(
                        definitions.c.owner == self.owner, definitions.c.digest == digest
                    )
                )
                .mappings()
                .one()
            )
        return self._definition(row, digest)

    def start(
        self, workflow: Workflow, trigger_id: str, values: tuple[Value, ...], now: datetime
    ) -> Run:
        workflow = Workflow.model_validate(workflow)
        expected = {item.name: item.type for item in workflow.trigger_schema}
        if (
            len(values) != len(expected)
            or {v.name: value_type(v.value) for v in values} != expected
        ):
            raise ValueError("Trigger schema mismatch")
        values = tuple(sorted(values, key=lambda value: value.name))
        run = Run(
            id="run_" + uuid4().hex,
            workspace_id=WorkspaceId(self.owner),
            definition_digest=workflow.digest,
            trigger_id=trigger_id,
            trigger=values,
            current=next(step.id for step in workflow.steps if step.kind == "trigger"),
            started_at=now,
        )
        digest = content_digest(tuple(v.model_dump(mode="json") for v in values))
        with self.engine.begin() as connection:
            connection.execute(
                insert(definitions)
                .values(
                    owner=self.owner,
                    digest=workflow.digest,
                    name=workflow.id,
                    version=workflow.version,
                    payload=workflow.model_dump(mode="json"),
                )
                .on_conflict_do_nothing()
            )
            recorded = connection.execute(
                select(definitions.c.digest).where(
                    definitions.c.owner == self.owner,
                    definitions.c.name == workflow.id,
                    definitions.c.version == workflow.version,
                )
            ).scalar_one()
            if recorded != workflow.digest:
                raise Conflict("Immutable definition version conflict")
            connection.execute(
                insert(runs)
                .values(
                    owner=self.owner,
                    id=run.id,
                    workflow=workflow.id,
                    trigger_id=trigger_id,
                    trigger_digest=digest,
                    revision=1,
                    payload=run.model_dump(mode="json"),
                    fence=0,
                )
                .on_conflict_do_nothing()
            )
            row = (
                connection.execute(
                    select(runs)
                    .where(
                        runs.c.owner == self.owner,
                        runs.c.workflow == workflow.id,
                        runs.c.trigger_id == trigger_id,
                    )
                    .with_for_update()
                )
                .mappings()
                .one()
            )
            if row["trigger_digest"] != digest:
                raise Conflict("Trigger identity reused with different input")
            return self._run(row)

    def load(self, identifier: str) -> Run:
        with self.engine.connect() as connection:
            row = connection.execute(select(runs).where(self._scope(identifier))).mappings().one()
        return self._run(row)

    def claim(self, identifier: str, now: datetime) -> tuple[Run, int] | None:
        with self.engine.begin() as connection:
            row = (
                connection.execute(select(runs).where(self._scope(identifier)).with_for_update())
                .mappings()
                .one()
            )
            run = self._run(row)
            if run.status in ("succeeded", "failed", "cancelled"):
                return None
            if row["lease_until"] is not None and row["lease_until"] > now:
                return None
            workflow = self._definition(
                connection.execute(
                    select(definitions).where(
                        definitions.c.owner == self.owner,
                        definitions.c.digest == run.definition_digest,
                    )
                )
                .mappings()
                .one(),
                run.definition_digest,
            )
            if workflow.id != row["workflow"]:
                raise Conflict("Stored workflow identity conflict")
            if (
                run.due_at is not None
                and run.due_at > now
                and now < run.started_at + timedelta(seconds=workflow.max_duration_seconds)
            ):
                return None
            step = next(item for item in workflow.steps if item.id == run.current)
            fence = row["fence"] + 1
            connection.execute(
                update(runs)
                .where(self._scope(identifier))
                .values(
                    fence=fence,
                    lease_until=now + timedelta(seconds=step.timeout_seconds),
                )
            )
            return run, fence

    def finish(self, old: Run, fence: int, changed: Run, now: datetime) -> Run:
        changed = Run.model_validate(changed)
        if (
            changed.id,
            changed.workspace_id,
            changed.definition_digest,
            changed.trigger,
            changed.trigger_id,
            changed.started_at,
            changed.revision,
        ) != (
            old.id,
            old.workspace_id,
            old.definition_digest,
            old.trigger,
            old.trigger_id,
            old.started_at,
            old.revision + 1,
        ):
            raise Conflict("Immutable run identity or revision mismatch")
        if old.workspace_id.root != self.owner:
            raise Conflict("Run owner mismatch")
        with self.engine.begin() as connection:
            updated = connection.execute(
                update(runs)
                .where(
                    self._scope(old.id),
                    runs.c.revision == old.revision,
                    runs.c.fence == fence,
                    runs.c.lease_until > now,
                )
                .values(
                    payload=changed.model_dump(mode="json"),
                    revision=changed.revision,
                    lease_until=None,
                )
            )
            if updated.rowcount != 1:
                raise Conflict("Stale worker, expired lease or changed run")
            connection.execute(
                audit.insert().values(
                    owner=self.owner,
                    run=old.id,
                    revision=changed.revision,
                    at=now,
                    step=old.current,
                    status=changed.status,
                    definition_digest=old.definition_digest,
                )
            )
            if changed.status == "failed":
                connection.execute(
                    insert(dead_letters)
                    .values(
                        owner=self.owner,
                        run=old.id,
                        definition_digest=old.definition_digest,
                        revision=changed.revision,
                        step=old.current,
                        code=changed.failure_code or "workflow_failed",
                        at=now,
                    )
                    .on_conflict_do_nothing()
                )
        return changed

    def cancel(self, identifier: str, revision: int, now: datetime) -> Run:
        with self.engine.begin() as connection:
            row = (
                connection.execute(select(runs).where(self._scope(identifier)).with_for_update())
                .mappings()
                .one()
            )
            old = self._run(row)
            if old.revision != revision or old.status in ("succeeded", "failed", "cancelled"):
                raise Conflict("Stale or terminal run")
            changed = old.model_copy(update={"status": "cancelled", "revision": revision + 1})
            connection.execute(
                update(runs)
                .where(self._scope(identifier))
                .values(
                    payload=changed.model_dump(mode="json"),
                    revision=changed.revision,
                    fence=row["fence"] + 1,
                    lease_until=None,
                )
            )
            connection.execute(
                audit.insert().values(
                    owner=self.owner,
                    run=identifier,
                    revision=changed.revision,
                    at=now,
                    step=old.current,
                    status="cancelled",
                    definition_digest=old.definition_digest,
                )
            )
            return changed
