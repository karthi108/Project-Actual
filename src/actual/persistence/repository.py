"""One scoped Career aggregate and its transactional observation history.

There is no mutable ORM domain model. Complete replacements are validated before
storage, then reloaded and checked inside the same transaction before commit.
"""

import hashlib
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta

from pydantic import TypeAdapter
from sqlalchemy import Connection, Engine, delete, func, select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from actual.career.applications import Application
from actual.career.events import (
    ApplicationStatusRecorded,
    DraftReviewed,
    JobAdded,
    RequirementsReviewed,
    WorkEvent,
    delivery_relation,
)
from actual.career.jobs import Job, Requirement
from actual.career.snapshot import CareerSnapshot
from actual.core.primitives import EventId, Instant, WorkspaceId, canonical_bytes
from actual.profile.contracts import Claim, EvidenceRecord

from . import schema
from .database import verify_schema
from .errors import (
    ConflictError,
    DeletedWorkspaceError,
    NotFoundError,
    PersistenceError,
)
from .event_mapping import event_rows, load_event, validate_event
from .mapping import Row, checksum, collections, load_snapshot, state_rows

_INSTANT: TypeAdapter[datetime] = TypeAdapter(Instant)


@dataclass(frozen=True)
class StoredCareer:
    snapshot: CareerSnapshot
    generation: int


@dataclass(frozen=True)
class DeletionRecord:
    workspace_id: WorkspaceId
    deleted_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "workspace_id", WorkspaceId.model_validate(self.workspace_id, strict=True)
        )
        object.__setattr__(self, "deleted_at", _INSTANT.validate_python(self.deleted_at))


class CareerStore:
    def __init__(self, engine: Engine, workspace_id: WorkspaceId) -> None:
        if engine.dialect.name != "postgresql":
            raise PersistenceError("Career storage requires PostgreSQL")
        self._engine = engine
        self.workspace_id = WorkspaceId.model_validate(workspace_id, strict=True)

    @contextmanager
    def _transaction(self, *, permit_deleted: bool = False) -> Iterator[Connection]:
        try:
            with self._engine.begin() as connection:
                verify_schema(connection)
                # Creation/deletion also need a lock before a workspace row exists.
                key = int.from_bytes(
                    hashlib.sha256(self.workspace_id.root.encode()).digest()[:8], signed=True
                )
                connection.execute(select(func.pg_advisory_xact_lock(key)))
                if not permit_deleted and self._deletion(connection) is not None:
                    raise DeletedWorkspaceError("Workspace has a deletion tombstone")
                yield connection
        except IntegrityError:
            raise ConflictError("A database constraint rejected the transaction") from None
        except SQLAlchemyError:
            raise PersistenceError("The database transaction failed") from None
        except (ValueError, TypeError, UnicodeError):
            raise PersistenceError("The transaction failed contract validation") from None

    def _workspace(self, connection: Connection) -> Row | None:
        row = (
            connection.execute(
                select(schema.career_workspaces)
                .where(schema.career_workspaces.c.workspace_id == self.workspace_id.root)
                .with_for_update()
            )
            .mappings()
            .one_or_none()
        )
        return dict(row) if row is not None else None

    def _current(self, connection: Connection) -> StoredCareer:
        row = self._workspace(connection)
        if row is None:
            raise NotFoundError("Career workspace does not exist")
        return StoredCareer(load_snapshot(connection, row), row["generation"])

    def load(self) -> StoredCareer:
        with self._transaction() as connection:
            return self._current(connection)

    def export(self) -> bytes:
        return canonical_bytes(self.load().snapshot)

    def save(
        self,
        snapshot: CareerSnapshot,
        *,
        expected_generation: int,
        events: tuple[WorkEvent, ...] = (),
    ) -> StoredCareer:
        checked = CareerSnapshot.model_validate(snapshot)
        canonical_bytes(checked)
        if checked.workspace_id != self.workspace_id:
            raise PersistenceError("Replacement belongs to another workspace")
        if (
            type(expected_generation) is not int
            or not 0 <= expected_generation < 9223372036854775807
        ):
            raise ValueError("Expected generation must be a bounded integer")
        observations = self._events(events)
        with self._transaction() as connection:
            row = self._workspace(connection)
            if row is None:
                if expected_generation != 0:
                    raise ConflictError("Workspace creation requires generation zero")
                old = None
                generation = 1
            else:
                if row["generation"] != expected_generation:
                    raise ConflictError("Workspace generation changed")
                old = load_snapshot(connection, row)
                self._replacement(old, checked, observations)
                generation = row["generation"] + (canonical_bytes(old) != canonical_bytes(checked))
            self._write_state(connection, checked, generation, old)
            self._append(connection, observations, checked)
            # Reads check canonical payloads, every projection and domain relationships.
            result = self._current(connection)
            if result.snapshot != checked or result.generation != generation:
                raise PersistenceError("Written state did not round trip exactly")
            return result

    @staticmethod
    def _events(events: tuple[WorkEvent, ...]) -> tuple[WorkEvent, ...]:
        if type(events) is not tuple or len(events) > 128:
            raise ValueError("A bounded tuple of events is required")
        checked = tuple(WorkEvent.model_validate(event) for event in events)
        if len({event.event_id for event in checked}) != len(checked):
            raise ValueError("A transaction cannot repeat an event ID")
        return checked

    @staticmethod
    def _replacement(
        old: CareerSnapshot, new: CareerSnapshot, events: tuple[WorkEvent, ...]
    ) -> None:
        if new.as_of < old.as_of:
            raise ConflictError("Snapshot time cannot move backwards")
        old_collections, new_collections = collections(old), collections(new)
        old_jobs = {record.id for record in old.jobs}
        for job in new.jobs:
            if job.id not in old_jobs:
                matches = tuple(
                    event
                    for event in events
                    if isinstance(event.payload, JobAdded) and event.payload.job.object_id == job.id
                )
                if not matches:
                    raise ConflictError("New job requires its atomic observation event")
                for event in matches:
                    validate_event(event, new)
        old_applications = {record.id for record in old.applications}
        for app in new.applications:
            if app.id not in old_applications:
                if len(app.history) != 1:
                    raise ConflictError(
                        "Historical application import requires aggregate bootstrap"
                    )
                matches = tuple(
                    event
                    for event in events
                    if isinstance(event.payload, ApplicationStatusRecorded)
                    and event.payload.application.object_id == app.id
                )
                if not matches:
                    raise ConflictError("New application requires its atomic initial observation")
                for event in matches:
                    validate_event(event, new)
        for kind, before in old_collections.items():
            after = {record.id: record for record in new_collections[kind]}
            if any(record.id not in after for record in before):
                raise ConflictError("Ordinary replacement cannot delete provenance records")
            for prior in before:
                current = after[prior.id]
                changed = canonical_bytes(prior) != canonical_bytes(current)
                if current.revision != prior.revision + changed:
                    raise ConflictError("Changed records require exactly the next revision")
                if isinstance(prior, EvidenceRecord) and isinstance(current, EvidenceRecord):
                    provenance: tuple[str, ...] = (
                        "source_kind",
                        "source_reference",
                        "source_actor_id",
                        "collected_at",
                    )
                    if any(
                        getattr(prior, field) != getattr(current, field) for field in provenance
                    ):
                        raise ConflictError(
                            "Source provenance requires a distinct evidence identity"
                        )
                if isinstance(prior, Claim) and isinstance(current, Claim):
                    provenance = ("origin", "asserted_by", "asserted_at")
                    if any(
                        getattr(prior, field) != getattr(current, field) for field in provenance
                    ):
                        raise ConflictError("Claim origin cannot be rewritten")
                if isinstance(prior, Application) and isinstance(current, Application):
                    if current.job_id != prior.job_id:
                        raise ConflictError("Application identity cannot change its job")
                    if current.history[: len(prior.history)] != prior.history:
                        raise ConflictError("Application history cannot be rewritten")
                    if len(current.history) not in (len(prior.history), len(prior.history) + 1):
                        raise ConflictError("An application update appends one observation")
                    if len(current.history) > len(prior.history):
                        matches = tuple(
                            event
                            for event in events
                            if isinstance(event.payload, ApplicationStatusRecorded)
                            and event.payload.application.object_id == current.id
                        )
                        if not matches:
                            raise ConflictError(
                                "Application transition requires its atomic observation event"
                            )
                        for event in matches:
                            validate_event(event, new)
                if isinstance(prior, Job) and isinstance(current, Job):
                    identity = ("company_id", "opportunity_id", "posted_at", "source_reference")
                    if any(getattr(prior, field) != getattr(current, field) for field in identity):
                        raise ConflictError("Job source identity cannot be rewritten")
                if isinstance(prior, Requirement) and isinstance(current, Requirement):
                    if current.job_id != prior.job_id or current.origin != prior.origin:
                        raise ConflictError("Requirement source identity cannot be rewritten")
        old_drafts = {record.id: record for record in old.drafts}
        for draft in new.drafts:
            previous = old_drafts.get(draft.id)
            if draft.review is not None and (previous is None or previous.review != draft.review):
                matches = tuple(
                    event
                    for event in events
                    if isinstance(event.payload, DraftReviewed)
                    and event.payload.draft.object_id == draft.id
                )
                if not matches:
                    raise ConflictError("New draft review requires its atomic observation event")
                for event in matches:
                    validate_event(event, new)
        old_requirements = {record.id: record for record in old.requirements}
        for requirement in new.requirements:
            previous_requirement = old_requirements.get(requirement.id)
            if (
                requirement.review is not None
                and requirement.review.decision == "accepted"
                and (
                    previous_requirement is None
                    or previous_requirement.review != requirement.review
                )
            ):
                matches = tuple(
                    event
                    for event in events
                    if isinstance(event.payload, RequirementsReviewed)
                    and any(
                        reference.object_id == requirement.id
                        for reference in event.payload.requirements
                    )
                )
                if not matches:
                    raise ConflictError(
                        "New requirement review requires its atomic observation event"
                    )
                for event in matches:
                    validate_event(event, new)

    def _write_state(
        self,
        connection: Connection,
        snapshot: CareerSnapshot,
        generation: int,
        old: CareerSnapshot | None,
    ) -> None:
        workspace = self.workspace_id.root
        header = {
            "workspace_id": workspace,
            "classification": snapshot.classification,
            "as_of": snapshot.as_of,
            "generation": generation,
            "snapshot_digest": checksum(snapshot),
        }
        if old is None:
            connection.execute(schema.career_workspaces.insert().values(**header))
        else:
            connection.execute(
                update(schema.career_workspaces)
                .where(schema.career_workspaces.c.workspace_id == workspace)
                .values(**header)
            )
        rows = state_rows(snapshot)
        # Exact refs are reconciled explicitly and constraints checked at commit.
        links = (schema.claim_evidence_links, schema.cv_claim_links, schema.draft_claim_links)
        for table in links:
            connection.execute(delete(table).where(table.c.workspace_id == workspace))
        old_rows = state_rows(old) if old is not None else {}
        for table in (schema.object_identities, *schema.CURRENT_TABLES.values()):
            key = "object_id" if table is schema.object_identities else "id"
            before = {row[key]: row for row in old_rows.get(table.name, [])}
            for row in rows[table.name]:
                previous = before.get(row[key])
                if previous is None:
                    connection.execute(table.insert().values(**row))
                elif row != previous:
                    connection.execute(
                        update(table)
                        .where(table.c.workspace_id == workspace, table.c[key] == row[key])
                        .values(**row)
                    )
        for table in links:
            if rows[table.name]:
                connection.execute(table.insert(), rows[table.name])

    def _append(
        self,
        connection: Connection,
        events: tuple[WorkEvent, ...],
        snapshot: CareerSnapshot,
    ) -> tuple[EventId, ...]:
        inserted: list[EventId] = []
        for event in events:
            if event.workspace_id != self.workspace_id:
                raise ValueError("Observation belongs to another workspace")
            query = select(schema.work_events).where(
                schema.work_events.c.workspace_id == self.workspace_id.root
            )
            prior = (
                connection.execute(
                    query.where(schema.work_events.c.event_id == event.event_id.root)
                )
                .mappings()
                .one_or_none()
            )
            if prior is not None:
                previous = load_event(connection, dict(prior))
                if (
                    canonical_bytes(previous) == canonical_bytes(event)
                    or delivery_relation(previous, event) == "duplicate"
                ):
                    continue
                raise ConflictError("Event identity has different content")
            if event.source_event_id is not None:
                prior = (
                    connection.execute(
                        query.where(
                            schema.work_events.c.source == event.source,
                            schema.work_events.c.source_event_id == event.source_event_id.root,
                        )
                    )
                    .mappings()
                    .one_or_none()
                )
                if prior is not None:
                    if delivery_relation(load_event(connection, dict(prior)), event) == "duplicate":
                        continue
                    raise ConflictError("Source event identity has different content")
            validate_event(event, snapshot)
            for name, rows in event_rows(event).items():
                if rows:
                    connection.execute(schema.metadata.tables[name].insert(), rows)
            inserted.append(event.event_id)
        return tuple(inserted)

    def append_events(self, events: tuple[WorkEvent, ...]) -> tuple[EventId, ...]:
        checked = self._events(events)
        with self._transaction() as connection:
            return self._append(connection, checked, self._current(connection).snapshot)

    def load_events(self) -> tuple[WorkEvent, ...]:
        with self._transaction() as connection:
            self._current(connection)
            rows = connection.execute(
                select(schema.work_events)
                .where(schema.work_events.c.workspace_id == self.workspace_id.root)
                .order_by(schema.work_events.c.occurred_at, schema.work_events.c.event_id)
            ).mappings()
            return tuple(load_event(connection, dict(row)) for row in rows)

    def _deletion(self, connection: Connection) -> DeletionRecord | None:
        row = (
            connection.execute(
                select(schema.deletion_ledger).where(
                    schema.deletion_ledger.c.workspace_id == self.workspace_id.root
                )
            )
            .mappings()
            .one_or_none()
        )
        return DeletionRecord(self.workspace_id, row["deleted_at"]) if row is not None else None

    def deletion_record(self) -> DeletionRecord | None:
        with self._transaction(permit_deleted=True) as connection:
            return self._deletion(connection)

    def delete(self, deleted_at: datetime) -> None:
        instant = _INSTANT.validate_python(deleted_at)
        with self._transaction(permit_deleted=True) as connection:
            prior = self._deletion(connection)
            if prior is None:
                connection.execute(
                    schema.deletion_ledger.insert().values(
                        workspace_id=self.workspace_id.root, deleted_at=instant
                    )
                )
            # Every delete is explicit; no evidence/provenance cascade is configured.
            for table in reversed(schema.metadata.sorted_tables):
                if table is not schema.deletion_ledger:
                    connection.execute(
                        delete(table).where(table.c.workspace_id == self.workspace_id.root)
                    )

    def apply_deletion_record(self, record: DeletionRecord) -> None:
        if type(record) is not DeletionRecord or record.workspace_id != self.workspace_id:
            raise ValueError("Deletion record belongs to another workspace")
        self.delete(record.deleted_at)

    def prune_events(self, now: datetime) -> int:
        try:
            cutoff = _INSTANT.validate_python(now) - timedelta(days=90)
        except OverflowError:
            raise ValueError("Retention instant is outside the supported range") from None
        with self._transaction() as connection:
            self._current(connection)
            event_ids = tuple(
                connection.execute(
                    select(schema.work_events.c.event_id).where(
                        schema.work_events.c.workspace_id == self.workspace_id.root,
                        schema.work_events.c.recorded_at < cutoff,
                    )
                ).scalars()
            )
            if event_ids:
                for table in (
                    schema.event_object_refs,
                    schema.event_evidence_refs,
                    schema.work_events,
                ):
                    connection.execute(
                        delete(table).where(
                            table.c.workspace_id == self.workspace_id.root,
                            table.c.event_id.in_(event_ids),
                        )
                    )
            return len(event_ids)
