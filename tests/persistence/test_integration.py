"""Exercise actual PostgreSQL state, event, isolation and deletion transactions."""

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier

import pytest
from sqlalchemy import Engine, MetaData, delete, func, insert, select, update
from sqlalchemy.exc import DBAPIError, IntegrityError

from actual.career.applications import StatusObservation
from actual.career.events import (
    ApplicationStatusRecorded,
    AssessmentCounts,
    DraftReviewed,
    FitAssessmentRecorded,
    JobAdded,
    WorkEvent,
)
from actual.career.snapshot import CareerSnapshot
from actual.careerlab.generator import generate_inputs
from actual.careerlab_bridge import ImportContext, map_observable
from actual.core.primitives import (
    ActorId,
    AssessmentId,
    EventId,
    JobId,
    OpportunityId,
    SourceEventId,
    WorkspaceId,
    canonical_bytes,
    canonical_data,
    content_digest,
    load_contract,
)
from actual.core.references import BusinessObjectRef
from actual.core.workflow import ContentReview
from actual.persistence import schema
from actual.persistence.errors import (
    ConflictError,
    CorruptStorageError,
    DeletedWorkspaceError,
    NotFoundError,
    PersistenceError,
    UnsupportedEventError,
)
from actual.persistence.mapping import entity_row
from actual.persistence.repository import CareerStore, DeletionRecord
from actual.profile.contracts import evidence_ref

ACTOR = ActorId("actor_" + "2" * 32)


def world(case: int = 0, owner: int = 1) -> CareerSnapshot:
    return map_observable(
        generate_inputs()[case],
        ImportContext(workspace_id=WorkspaceId(f"workspace_{owner:032x}"), actor_id=ACTOR),
    )


def reference(record: object) -> BusinessObjectRef:
    return BusinessObjectRef(
        workspace_id=record.workspace_id,
        classification=record.classification,
        kind=record.id.prefix,
        object_id=record.id,
        revision=record.revision,
        content_digest=content_digest(record.model_dump(mode="json")),
    )


def job_event(snapshot: CareerSnapshot, number: int = 1, **changes: object) -> WorkEvent:
    ref = reference(snapshot.jobs[0])
    return WorkEvent.model_validate(
        {
            "event_id": EventId(f"event_{number:032x}"),
            "workspace_id": snapshot.workspace_id,
            "actor_id": ACTOR,
            "occurred_at": snapshot.as_of,
            "recorded_at": snapshot.as_of,
            "source": "manual",
            "source_event_id": SourceEventId(f"source_event_{number:032x}"),
            "business_objects": (ref,),
            "privacy_classification": snapshot.classification,
            "activity": "job_added",
            "payload": JobAdded(job=ref),
            **changes,
        }
    )


def changed_company(snapshot: CareerSnapshot, suffix: str = "A") -> CareerSnapshot:
    company = snapshot.companies[0]
    changed = company.model_copy(
        update={"revision": company.revision + 1, "context": f"Synthetic changed context {suffix}."}
    )
    return snapshot.model_copy(update={"companies": (changed, *snapshot.companies[1:])})


def advanced_application(snapshot: CareerSnapshot) -> tuple[CareerSnapshot, WorkEvent]:
    old = snapshot.applications[0]
    occurred = old.history[-1].occurred_at + timedelta(days=1)
    entry = StatusObservation(
        actor_id=ACTOR,
        occurred_at=occurred,
        recorded_at=occurred + timedelta(hours=1),
        state="ready_for_review",
        basis="user_reported",
    )
    app = old.model_copy(
        update={
            "revision": old.revision + 1,
            "state": entry.state,
            "history": (*old.history, entry),
        }
    )
    result = snapshot.model_copy(update={"applications": (app, *snapshot.applications[1:])})
    ref = reference(app)
    event = WorkEvent(
        event_id=EventId("event_" + "3" * 32),
        workspace_id=snapshot.workspace_id,
        actor_id=entry.actor_id,
        occurred_at=entry.occurred_at,
        recorded_at=entry.recorded_at,
        source="manual",
        source_event_id=SourceEventId("source_event_" + "3" * 32),
        business_objects=(ref,),
        privacy_classification=snapshot.classification,
        activity="application_status_recorded",
        payload=ApplicationStatusRecorded(
            application=ref,
            previous_state=old.state,
            state=entry.state,
            basis=entry.basis,
            external_manual=entry.external_manual,
        ),
    )
    return result, event


def test_absent_workspace_does_not_return_an_empty_or_default_world(pg_engine: Engine) -> None:
    with pytest.raises(NotFoundError):
        CareerStore(pg_engine, world().workspace_id).load()


@pytest.mark.parametrize("case", range(7))
def test_real_database_roundtrip_preserves_valid_observable_worlds(
    pg_engine: Engine, case: int
) -> None:
    snapshot = world(case)
    store = CareerStore(pg_engine, snapshot.workspace_id)
    saved = store.save(snapshot, expected_generation=0)
    assert saved.generation == 1
    assert saved.snapshot == snapshot
    restored = CareerStore(pg_engine, snapshot.workspace_id).load()
    assert restored == saved
    assert store.export() == canonical_bytes(snapshot)
    assert load_contract(CareerSnapshot, store.export()) == snapshot
    assert store.load_events() == ()


def test_owner_scoping_never_falls_back_to_another_workspace(pg_engine: Engine) -> None:
    first, other = world(owner=1), world(owner=9)
    one = CareerStore(pg_engine, first.workspace_id)
    two = CareerStore(pg_engine, other.workspace_id)
    one.save(first, expected_generation=0)
    with pytest.raises(NotFoundError):
        two.load()
    two.save(other, expected_generation=0)
    assert one.load().snapshot == first
    assert two.load().snapshot == other
    with pytest.raises(PersistenceError):
        one.save(other, expected_generation=1)
    assert one.load().snapshot == first


def test_generation_conflict_cannot_overwrite_current_content(pg_engine: Engine) -> None:
    original = world()
    store = CareerStore(pg_engine, original.workspace_id)
    store.save(original, expected_generation=0)
    changed = changed_company(original)
    stored = store.save(changed, expected_generation=1)
    assert stored.generation == 2
    with pytest.raises(ConflictError):
        store.save(changed_company(original, "stale writer"), expected_generation=1)
    assert store.load() == stored


@pytest.mark.parametrize("revision", [1, 3])
def test_changed_object_requires_exact_next_revision(pg_engine: Engine, revision: int) -> None:
    original = world()
    store = CareerStore(pg_engine, original.workspace_id)
    store.save(original, expected_generation=0)
    changed = original.companies[0].model_copy(
        update={"revision": revision, "context": "Synthetic conflicting replacement."}
    )
    proposed = original.model_copy(update={"companies": (changed,)})
    with pytest.raises(ConflictError):
        store.save(proposed, expected_generation=1)
    assert store.load().snapshot == original
    assert store.load().generation == 1


def test_ordinary_save_cannot_bypass_explicit_deletion(pg_engine: Engine) -> None:
    original = world()
    store = CareerStore(pg_engine, original.workspace_id)
    store.save(original, expected_generation=0)
    with pytest.raises(PersistenceError):
        store.save(original.model_copy(update={"cvs": ()}), expected_generation=1)
    assert store.load().snapshot == original


def test_application_append_and_its_event_commit_together(pg_engine: Engine) -> None:
    original = world()
    store = CareerStore(pg_engine, original.workspace_id)
    store.save(original, expected_generation=0)
    advanced, event = advanced_application(original)
    result = store.save(advanced, expected_generation=1, events=(event,))
    assert result.generation == 2
    assert store.load().snapshot == advanced
    assert store.load_events() == (event,)
    assert store.load().snapshot.applications[0].history[:-1] == original.applications[0].history


def test_application_update_without_matching_event_rolls_back(pg_engine: Engine) -> None:
    original = world()
    store = CareerStore(pg_engine, original.workspace_id)
    store.save(original, expected_generation=0)
    advanced, _ = advanced_application(original)
    with pytest.raises(PersistenceError):
        store.save(advanced, expected_generation=1)
    assert store.load().snapshot == original
    assert store.load().generation == 1
    assert store.load_events() == ()


@pytest.mark.parametrize("field", ["state", "occurred_at", "actor_id"])
def test_event_must_describe_the_exact_appended_observation(pg_engine: Engine, field: str) -> None:
    original = world()
    store = CareerStore(pg_engine, original.workspace_id)
    store.save(original, expected_generation=0)
    advanced, event = advanced_application(original)
    if field == "state":
        payload = event.payload.model_copy(
            update={"previous_state": "ready_for_review", "state": "reviewed"}
        )
        event = event.model_copy(update={"payload": payload})
    elif field == "occurred_at":
        event = event.model_copy(update={"occurred_at": event.occurred_at - timedelta(hours=1)})
    else:
        event = event.model_copy(update={"actor_id": ActorId("actor_" + "4" * 32)})
    with pytest.raises(PersistenceError):
        store.save(advanced, expected_generation=1, events=(event,))
    assert store.load().snapshot == original
    assert store.load_events() == ()


def test_application_history_cannot_rewrite_a_previous_observation(pg_engine: Engine) -> None:
    original = world()
    store = CareerStore(pg_engine, original.workspace_id)
    store.save(original, expected_generation=0)
    advanced, event = advanced_application(original)
    app = advanced.applications[0]
    rewritten = app.history[0].model_copy(update={"actor_id": ActorId("actor_" + "4" * 32)})
    app = app.model_copy(update={"history": (rewritten, *app.history[1:])})
    proposed = advanced.model_copy(update={"applications": (app,)})
    ref = reference(app)
    payload = event.payload.model_copy(update={"application": ref})
    event = event.model_copy(update={"business_objects": (ref,), "payload": payload})
    with pytest.raises(PersistenceError):
        store.save(proposed, expected_generation=1, events=(event,))
    assert store.load().snapshot == original


def test_closed_history_cannot_be_replaced_with_a_new_preparing_history(pg_engine: Engine) -> None:
    original = world(2)
    store = CareerStore(pg_engine, original.workspace_id)
    store.save(original, expected_generation=0)
    old = original.applications[0]
    assert old.state == "closed"
    reset = old.model_copy(
        update={"revision": old.revision + 1, "state": "preparing", "history": old.history[:1]}
    )
    proposed = original.model_copy(update={"applications": (reset,)})
    with pytest.raises(PersistenceError):
        store.save(proposed, expected_generation=1)
    assert store.load().snapshot.applications[0] == old


def test_invalid_second_event_rolls_back_state_and_the_first_event(pg_engine: Engine) -> None:
    original = world()
    store = CareerStore(pg_engine, original.workspace_id)
    store.save(original, expected_generation=0)
    good = job_event(original, 1)
    bad_ref = reference(original.jobs[0]).model_copy(update={"content_digest": "f" * 64})
    bad = job_event(original, 2, business_objects=(bad_ref,), payload=JobAdded(job=bad_ref))
    with pytest.raises(PersistenceError):
        store.save(changed_company(original), expected_generation=1, events=(good, bad))
    assert store.load().snapshot == original
    assert store.load().generation == 1
    assert store.load_events() == ()


def test_source_redelivery_is_a_noop_but_changed_attribution_is_a_conflict(
    pg_engine: Engine,
) -> None:
    original = world()
    store = CareerStore(pg_engine, original.workspace_id)
    store.save(original, expected_generation=0)
    first = job_event(original)
    assert store.append_events((first,)) == (first.event_id,)
    redelivery = first.model_copy(
        update={
            "event_id": EventId("event_" + "5" * 32),
            "recorded_at": first.recorded_at + timedelta(seconds=1),
        }
    )
    assert store.append_events((redelivery,)) == ()
    conflict = redelivery.model_copy(update={"actor_id": ActorId("actor_" + "6" * 32)})
    with pytest.raises(ConflictError):
        store.append_events((conflict,))
    assert store.load_events() == (first,)


def test_event_batch_failure_does_not_leave_partial_delivery(pg_engine: Engine) -> None:
    original = world()
    store = CareerStore(pg_engine, original.workspace_id)
    store.save(original, expected_generation=0)
    first, other = job_event(original, 1), job_event(world(owner=9), 2)
    with pytest.raises(PersistenceError):
        store.append_events((first, other))
    assert store.load_events() == ()


def test_loaded_events_have_deterministic_occurrence_and_identity_order(pg_engine: Engine) -> None:
    original = world()
    store = CareerStore(pg_engine, original.workspace_id)
    store.save(original, expected_generation=0)
    early = original.as_of - timedelta(days=1)
    late, second, first = (
        job_event(original, 3),
        job_event(original, 2, occurred_at=early),
        job_event(original, 1, occurred_at=early),
    )
    store.append_events((late, second, first))
    assert store.load_events() == (first, second, late)


def test_concurrent_writers_have_one_atomic_winner(pg_engine: Engine) -> None:
    original = world()
    store = CareerStore(pg_engine, original.workspace_id)
    store.save(original, expected_generation=0)
    barrier = Barrier(2)

    def writer(suffix: str) -> str:
        barrier.wait(timeout=10)
        try:
            CareerStore(pg_engine, original.workspace_id).save(
                changed_company(original, suffix), expected_generation=1
            )
            return "committed"
        except ConflictError:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        attempts = (pool.submit(writer, "A"), pool.submit(writer, "B"))
        results = [attempt.result(timeout=20) for attempt in attempts]
    assert sorted(results) == ["committed", "conflict"]
    assert store.load().generation == 2
    assert store.load().snapshot.companies[0].context in {
        "Synthetic changed context A.",
        "Synthetic changed context B.",
    }


def test_concurrent_source_delivery_is_durably_deduplicated(pg_engine: Engine) -> None:
    original = world()
    store = CareerStore(pg_engine, original.workspace_id)
    store.save(original, expected_generation=0)
    first = job_event(original)
    other = first.model_copy(update={"event_id": EventId("event_" + "7" * 32)})
    barrier = Barrier(2)

    def delivery(event: WorkEvent) -> tuple[EventId, ...]:
        barrier.wait(timeout=10)
        return CareerStore(pg_engine, original.workspace_id).append_events((event,))

    with ThreadPoolExecutor(max_workers=2) as pool:
        attempts = (pool.submit(delivery, first), pool.submit(delivery, other))
        results = [attempt.result(timeout=20) for attempt in attempts]
    assert sorted(len(result) for result in results) == [0, 1]
    assert len(store.load_events()) == 1


def test_deletion_blocks_old_snapshot_restore_without_affecting_another_owner(
    pg_engine: Engine,
) -> None:
    original, unrelated = world(), world(owner=9)
    store = CareerStore(pg_engine, original.workspace_id)
    other = CareerStore(pg_engine, unrelated.workspace_id)
    store.save(original, expected_generation=0)
    other.save(unrelated, expected_generation=0)
    store.append_events((job_event(original),))
    backup = store.export()
    store.delete(deleted_at=datetime(2026, 10, 4, tzinfo=UTC))
    with pytest.raises((NotFoundError, DeletedWorkspaceError)):
        store.load()
    restored = load_contract(CareerSnapshot, backup)
    with pytest.raises(DeletedWorkspaceError):
        CareerStore(pg_engine, original.workspace_id).save(restored, expected_generation=0)
    assert other.load().snapshot == unrelated


def test_old_event_cannot_be_replayed_into_a_deleted_workspace(pg_engine: Engine) -> None:
    original = world()
    store = CareerStore(pg_engine, original.workspace_id)
    store.save(original, expected_generation=0)
    event = job_event(original)
    store.append_events((event,))
    store.delete(deleted_at=datetime(2026, 10, 4, tzinfo=UTC))
    with pytest.raises(DeletedWorkspaceError):
        store.append_events((event,))


def test_fit_observation_cannot_fabricate_a_missing_assessment_entity(pg_engine: Engine) -> None:
    original = world()
    store = CareerStore(pg_engine, original.workspace_id)
    store.save(original, expected_generation=0)
    job, profile = reference(original.jobs[0]), reference(original.profile)
    assessment = BusinessObjectRef(
        workspace_id=original.workspace_id,
        classification=original.classification,
        kind="assessment",
        object_id=AssessmentId("assessment_" + "a" * 32),
        revision=1,
        content_digest="a" * 64,
    )
    event = job_event(
        original,
        business_objects=(job, profile, assessment),
        activity="fit_assessment_recorded",
        payload=FitAssessmentRecorded(
            job=job,
            profile=profile,
            assessment=assessment,
            counts=AssessmentCounts(supported=0, partial=0, gap=0, unknown=1, conflict=0),
        ),
    )
    with pytest.raises(UnsupportedEventError):
        store.append_events((event,))
    assert store.load_events() == ()


def test_draft_review_event_cannot_claim_review_of_an_unreviewed_object(pg_engine: Engine) -> None:
    original = world()
    store = CareerStore(pg_engine, original.workspace_id)
    store.save(original, expected_generation=0)
    draft = original.drafts[0]
    assert draft.review is None
    ref = reference(draft)
    event = job_event(
        original,
        business_objects=(ref,),
        evidence_refs=(evidence_ref(original.profile.evidence[0]),),
        activity="draft_reviewed",
        payload=DraftReviewed(
            draft=ref, decision="accepted", reviewer_id=ACTOR, reviewed_at=original.as_of
        ),
    )
    with pytest.raises(PersistenceError):
        store.append_events((event,))
    assert store.load_events() == ()


def test_accepted_structured_draft_and_matching_review_event_roundtrip(pg_engine: Engine) -> None:
    original = world()
    store = CareerStore(pg_engine, original.workspace_id)
    store.save(original, expected_generation=0)
    draft = original.drafts[0].model_copy(update={"revision": 2})
    review = ContentReview(
        revision=draft.revision,
        content_digest=draft.content_digest,
        reviewer_id=ACTOR,
        reviewed_at=original.as_of,
        method="Synthetic structured review",
        decision="accepted",
    )
    draft = draft.model_copy(update={"review": review})
    changed = original.model_copy(update={"drafts": (draft, *original.drafts[1:])})
    ref = reference(draft)
    event = job_event(
        changed,
        business_objects=(ref,),
        evidence_refs=(evidence_ref(original.profile.evidence[0]),),
        activity="draft_reviewed",
        payload=DraftReviewed(
            draft=ref, decision=review.decision, reviewer_id=ACTOR, reviewed_at=review.reviewed_at
        ),
    )
    store.save(changed, expected_generation=1, events=(event,))
    assert store.load().snapshot == changed
    assert store.load_events() == (event,)


def test_real_database_rejects_cross_workspace_company_relationship(pg_engine: Engine) -> None:
    original, unrelated = world(), world(owner=9)
    CareerStore(pg_engine, original.workspace_id).save(original, expected_generation=0)
    CareerStore(pg_engine, unrelated.workspace_id).save(unrelated, expected_generation=0)
    foreign = original.jobs[0].model_copy(
        update={
            "id": JobId("job_" + "f" * 32),
            "opportunity_id": OpportunityId("opportunity_" + "f" * 32),
            "company_id": unrelated.companies[0].id,
        }
    )
    row = entity_row(foreign, 1, {job.id.root: job for job in original.jobs})
    identity = {
        "workspace_id": original.workspace_id.root,
        "object_id": foreign.id.root,
        "kind": "job",
        "revision": 1,
        "classification": "synthetic",
        "digest": row["payload_digest"],
    }
    with pytest.raises(IntegrityError) as caught:
        with pg_engine.begin() as connection:
            connection.execute(insert(schema.object_identities), identity)
            connection.execute(insert(schema.jobs), row)
    assert caught.value.orig.sqlstate == "23503"
    assert CareerStore(pg_engine, original.workspace_id).load().snapshot == original


@pytest.mark.parametrize(
    ("table_name", "changes"),
    [
        ("companies", {"revision": 0}),
        ("applications", {"state": "sending"}),
        ("claims", {"status": "automatically_verified"}),
        ("companies", {"classification": "secret"}),
        ("companies", {"payload_digest": "0" * 64}),
    ],
)
def test_postgresql_constraints_reject_direct_invalid_state(
    pg_engine: Engine, table_name: str, changes: dict[str, object]
) -> None:
    original = world()
    store = CareerStore(pg_engine, original.workspace_id)
    store.save(original, expected_generation=0)
    table = schema.metadata.tables[table_name]
    with pytest.raises(IntegrityError) as caught:
        with pg_engine.begin() as connection:
            connection.execute(
                update(table)
                .where(table.c.workspace_id == original.workspace_id.root)
                .values(**changes)
            )
    assert caught.value.orig.sqlstate == "23514"
    assert store.load().snapshot == original


@pytest.mark.parametrize("table_name", ["companies", "claim_evidence_links"])
def test_load_rejects_corrupt_relational_projection_without_partial_results(
    pg_engine: Engine, table_name: str
) -> None:
    original = world()
    store = CareerStore(pg_engine, original.workspace_id)
    store.save(original, expected_generation=0)
    table = schema.metadata.tables[table_name]
    with pg_engine.begin() as connection:
        connection.execute(
            update(table)
            .where(table.c.workspace_id == original.workspace_id.root)
            .values(position=99)
        )
    with pytest.raises(CorruptStorageError):
        store.load()
    with pytest.raises(CorruptStorageError):
        store.export()


def test_load_revalidates_payload_even_when_database_checksum_is_consistent(
    pg_engine: Engine,
) -> None:
    original = world()
    store = CareerStore(pg_engine, original.workspace_id)
    store.save(original, expected_generation=0)
    company = original.companies[0]
    body = json.loads(canonical_bytes(company))
    body["revision"] = company.revision + 1
    body["unregistered_authority"] = "must not become trusted"
    payload = canonical_data(body)
    digest = hashlib.sha256(payload).hexdigest()
    # A trusted SQL operator can replace a syntactically valid, checksummed row.
    # Respect the revision guards while bypassing the domain writer deliberately;
    # reads must still reject the unknown field rather than trusting its checksum.
    with pg_engine.begin() as connection:
        connection.execute(
            update(schema.companies)
            .where(schema.companies.c.id == company.id.root)
            .values(
                revision=body["revision"], payload=payload.decode("utf-8"), payload_digest=digest
            )
        )
        connection.execute(
            update(schema.object_identities)
            .where(schema.object_identities.c.object_id == company.id.root)
            .values(revision=body["revision"], digest=digest)
        )
    with pytest.raises(CorruptStorageError):
        store.load()


def test_deletion_purges_all_workspace_content_and_keeps_only_minimal_tombstone(
    pg_engine: Engine,
) -> None:
    original = world()
    store = CareerStore(pg_engine, original.workspace_id)
    store.save(original, expected_generation=0)
    store.append_events((job_event(original),))
    deleted_at = datetime(2026, 10, 4, tzinfo=UTC)
    store.delete(deleted_at=deleted_at)
    with pg_engine.connect() as connection:
        for table in schema.metadata.tables.values():
            if table.name == "deletion_ledger":
                continue
            count = connection.scalar(
                select(func.count())
                .select_from(table)
                .where(table.c.workspace_id == original.workspace_id.root)
            )
            assert count == 0, table.name
        tombstone = connection.execute(select(schema.deletion_ledger)).mappings().one()
    assert dict(tombstone) == {"workspace_id": original.workspace_id.root, "deleted_at": deleted_at}


def test_database_tombstone_guard_rejects_direct_workspace_resurrection(pg_engine: Engine) -> None:
    original = world()
    store = CareerStore(pg_engine, original.workspace_id)
    store.save(original, expected_generation=0)
    with pg_engine.connect() as connection:
        backup_header = dict(connection.execute(select(schema.career_workspaces)).mappings().one())
    store.delete(deleted_at=datetime(2026, 10, 4, tzinfo=UTC))
    with pytest.raises(DBAPIError):
        with pg_engine.begin() as connection:
            connection.execute(insert(schema.career_workspaces), backup_header)


def test_reordering_existing_records_preserves_identity_and_revision(pg_engine: Engine) -> None:
    original = world(4)
    store = CareerStore(pg_engine, original.workspace_id)
    store.save(original, expected_generation=0)
    reordered = original.model_copy(update={"cvs": tuple(reversed(original.cvs))})
    result = store.save(reordered, expected_generation=1)
    assert result.generation == 2
    assert result.snapshot == reordered
    assert [cv.id for cv in store.load().snapshot.cvs] == [cv.id for cv in reordered.cvs]
    assert {cv.id: cv.revision for cv in reordered.cvs} == {
        cv.id: cv.revision for cv in original.cvs
    }
    assert store.export() == canonical_bytes(reordered)


def test_previous_status_delivery_cannot_authorize_another_transition(pg_engine: Engine) -> None:
    original = world()
    store = CareerStore(pg_engine, original.workspace_id)
    store.save(original, expected_generation=0)
    first, old_event = advanced_application(original)
    store.save(first, expected_generation=1, events=(old_event,))
    app = first.applications[0]
    previous = app.history[-1]
    observation = previous.model_copy(
        update={
            "state": "reviewed",
            "occurred_at": previous.occurred_at + timedelta(days=1),
            "recorded_at": previous.recorded_at + timedelta(days=1),
        }
    )
    changed = app.model_copy(
        update={
            "revision": app.revision + 1,
            "state": "reviewed",
            "history": (*app.history, observation),
        }
    )
    next_snapshot = first.model_copy(update={"applications": (changed,)})
    with pytest.raises(PersistenceError):
        store.save(next_snapshot, expected_generation=2, events=(old_event,))
    assert store.load().snapshot == first
    assert store.load().generation == 2
    assert store.load_events() == (old_event,)


@pytest.mark.parametrize("revision_increment", [0, 2])
def test_database_guard_requires_exactly_next_record_revision(
    pg_engine: Engine, revision_increment: int
) -> None:
    original = world()
    store = CareerStore(pg_engine, original.workspace_id)
    store.save(original, expected_generation=0)
    company = original.companies[0]
    body = json.loads(canonical_bytes(company))
    body["revision"] += revision_increment
    body["context"] = "Synthetic direct SQL replacement."
    payload = canonical_data(body)
    with pytest.raises(IntegrityError) as caught:
        with pg_engine.begin() as connection:
            connection.execute(
                update(schema.companies)
                .where(schema.companies.c.id == company.id.root)
                .values(
                    revision=body["revision"],
                    payload=payload.decode("utf-8"),
                    payload_digest=hashlib.sha256(payload).hexdigest(),
                )
            )
    assert caught.value.orig.sqlstate == "23514"
    assert store.load().snapshot == original


@pytest.mark.parametrize(
    ("table_name", "field", "replacement"),
    [
        ("jobs", "source_reference", "https://another.actual.invalid/job"),
        ("evidence", "source_reference", "synthetic:rewritten_provenance"),
        ("claims", "asserted_by", "actor_" + "4" * 32),
    ],
)
def test_database_guard_preserves_source_identity_at_next_revision(
    pg_engine: Engine, table_name: str, field: str, replacement: str
) -> None:
    original = world()
    store = CareerStore(pg_engine, original.workspace_id)
    store.save(original, expected_generation=0)
    table = schema.metadata.tables[table_name]
    with pg_engine.connect() as connection:
        row = connection.execute(select(table).order_by(table.c.position)).mappings().first()
    assert row is not None
    body = json.loads(row["payload"])
    assert body[field] != replacement
    body["revision"] += 1
    body[field] = replacement
    payload = canonical_data(body)
    with pytest.raises(IntegrityError) as caught:
        with pg_engine.begin() as connection:
            connection.execute(
                update(table)
                .where(table.c.id == row["id"])
                .values(
                    revision=body["revision"],
                    payload=payload.decode("utf-8"),
                    payload_digest=hashlib.sha256(payload).hexdigest(),
                )
            )
    assert caught.value.orig.sqlstate == "23514"
    assert store.load().snapshot == original


def test_database_guard_preserves_application_history_prefix(pg_engine: Engine) -> None:
    original = world()
    store = CareerStore(pg_engine, original.workspace_id)
    store.save(original, expected_generation=0)
    app = original.applications[0]
    body = json.loads(canonical_bytes(app))
    body["revision"] += 1
    body["history"][0]["actor_id"] = "actor_" + "4" * 32
    payload = canonical_data(body)
    with pytest.raises(IntegrityError) as caught:
        with pg_engine.begin() as connection:
            connection.execute(
                update(schema.applications)
                .where(schema.applications.c.id == app.id.root)
                .values(
                    revision=body["revision"],
                    payload=payload.decode("utf-8"),
                    payload_digest=hashlib.sha256(payload).hexdigest(),
                )
            )
    assert caught.value.orig.sqlstate == "23514"
    assert store.load().snapshot == original


@pytest.mark.parametrize("table_name", ["work_events", "event_object_refs", "event_evidence_refs"])
def test_database_guard_rejects_historical_event_rewrites(
    pg_engine: Engine, table_name: str
) -> None:
    original = world()
    store = CareerStore(pg_engine, original.workspace_id)
    store.save(original, expected_generation=0)
    event = job_event(original, evidence_refs=(evidence_ref(original.profile.evidence[0]),))
    store.append_events((event,))
    table = schema.metadata.tables[table_name]
    with pytest.raises(IntegrityError) as caught:
        with pg_engine.begin() as connection:
            connection.execute(
                update(table)
                .where(table.c.workspace_id == original.workspace_id.root)
                .values(
                    **(
                        {"recorded_at": event.recorded_at}
                        if table_name == "work_events"
                        else {"position": 0}
                    )
                )
            )
    assert caught.value.orig.sqlstate == "23514"
    assert store.load_events() == (event,)


@pytest.mark.parametrize("mutation", ["update", "delete"])
def test_database_guard_keeps_deletion_tombstones_immutable(
    pg_engine: Engine, mutation: str
) -> None:
    original = world()
    store = CareerStore(pg_engine, original.workspace_id)
    store.save(original, expected_generation=0)
    deleted_at = original.as_of + timedelta(days=1)
    store.delete(deleted_at)
    with pytest.raises(IntegrityError) as caught:
        with pg_engine.begin() as connection:
            statement = (
                update(schema.deletion_ledger).values(deleted_at=deleted_at + timedelta(days=1))
                if mutation == "update"
                else delete(schema.deletion_ledger)
            )
            connection.execute(
                statement.where(schema.deletion_ledger.c.workspace_id == original.workspace_id.root)
            )
    assert caught.value.orig.sqlstate == "23514"
    assert store.deletion_record() == DeletionRecord(original.workspace_id, deleted_at)


def test_retention_uses_recording_time_and_preserves_exact_ninety_day_boundary(
    pg_engine: Engine,
) -> None:
    original, unrelated = world(), world(owner=9)
    with pg_engine.connect() as connection:
        now = connection.scalar(select(func.current_timestamp()))
    assert isinstance(now, datetime)
    cutoff = now - timedelta(days=90)
    original = original.model_copy(
        update={
            "jobs": tuple(
                job.model_copy(update={"posted_at": now - timedelta(days=100)})
                for job in original.jobs
            )
        }
    )
    unrelated = unrelated.model_copy(
        update={
            "jobs": tuple(
                job.model_copy(update={"posted_at": now - timedelta(days=100)})
                for job in unrelated.jobs
            )
        }
    )
    store = CareerStore(pg_engine, original.workspace_id)
    other = CareerStore(pg_engine, unrelated.workspace_id)
    store.save(original, expected_generation=0)
    other.save(unrelated, expected_generation=0)
    evidence = (evidence_ref(original.profile.evidence[0]),)
    occurrence = cutoff - timedelta(days=1)
    older, boundary, recent = (
        job_event(
            original, index, occurred_at=occurrence, recorded_at=recorded, evidence_refs=evidence
        )
        for index, recorded in enumerate(
            (cutoff - timedelta(microseconds=1), cutoff, cutoff + timedelta(microseconds=1)),
            start=1,
        )
    )
    untouched = job_event(unrelated, occurred_at=occurrence, recorded_at=older.recorded_at)
    store.append_events((older, boundary, recent))
    other.append_events((untouched,))
    assert store.prune_events(now) == 1
    assert store.load_events() == (boundary, recent)
    assert other.load_events() == (untouched,)
    assert store.load().snapshot == original
    with pg_engine.connect() as connection:
        for table in (schema.work_events, schema.event_object_refs, schema.event_evidence_refs):
            assert (
                connection.scalar(
                    select(func.count())
                    .select_from(table)
                    .where(
                        table.c.event_id == older.event_id.root,
                        table.c.workspace_id == original.workspace_id.root,
                    )
                )
                == 0
            )
    assert store.prune_events(now) == 0


def test_restored_minimal_deletion_ledger_blocks_snapshot_and_event_backup(
    pg_engine: Engine, restored_pg_engine: Engine
) -> None:
    original = world()
    source = CareerStore(pg_engine, original.workspace_id)
    source.save(original, expected_generation=0)
    old_event = job_event(original)
    source.append_events((old_event,))
    backup = source.export()
    source.delete(original.as_of + timedelta(days=1))
    record = source.deletion_record()
    assert record is not None
    restored = CareerStore(restored_pg_engine, original.workspace_id)
    assert restored.deletion_record() is None
    restored.apply_deletion_record(record)
    restored.apply_deletion_record(record)
    assert restored.deletion_record() == record
    with pytest.raises(DeletedWorkspaceError):
        restored.save(load_contract(CareerSnapshot, backup), expected_generation=0)
    with pytest.raises(DeletedWorkspaceError):
        restored.append_events((old_event,))
    with pytest.raises(DeletedWorkspaceError):
        restored.load()


def test_dml_runtime_role_can_commit_state_and_explicit_workspace_deletion(
    runtime_engine: Engine,
) -> None:
    original = world()
    store = CareerStore(runtime_engine, original.workspace_id)
    store.save(original, expected_generation=0)
    changed = changed_company(original)
    store.save(changed, expected_generation=1, events=(job_event(changed),))
    assert store.load().snapshot == changed
    assert len(store.load_events()) == 1
    store.delete(original.as_of + timedelta(days=1))
    assert store.deletion_record() is not None
    with pytest.raises(DeletedWorkspaceError):
        store.load()


@pytest.mark.parametrize(
    "statement",
    [
        "CREATE TABLE unapproved_runtime_table (id integer)",
        "ALTER TABLE companies DISABLE TRIGGER ALL",
        "DROP TABLE companies",
        "TRUNCATE companies",
    ],
)
def test_dml_runtime_role_cannot_bypass_guards_with_ddl_or_truncation(
    runtime_engine: Engine, statement: str
) -> None:
    original = world()
    store = CareerStore(runtime_engine, original.workspace_id)
    store.save(original, expected_generation=0)
    with pytest.raises(DBAPIError) as caught:
        with runtime_engine.begin() as connection:
            connection.exec_driver_sql(statement)
    assert caught.value.orig.sqlstate == "42501"
    assert store.load().snapshot == original


@pytest.mark.parametrize("table_name", ["companies", "object_identities", "career_workspaces"])
def test_dml_runtime_role_cannot_delete_current_provenance_without_tombstone(
    runtime_engine: Engine, table_name: str
) -> None:
    original = world()
    store = CareerStore(runtime_engine, original.workspace_id)
    store.save(original, expected_generation=0)
    table = schema.metadata.tables[table_name]
    with pytest.raises(IntegrityError) as caught:
        with runtime_engine.begin() as connection:
            connection.execute(
                delete(table).where(table.c.workspace_id == original.workspace_id.root)
            )
    assert caught.value.orig.sqlstate == "23514"
    assert store.load().snapshot == original


@pytest.mark.parametrize("table_name", ["work_events", "event_object_refs", "event_evidence_refs"])
def test_dml_runtime_role_cannot_erase_recent_observations(
    runtime_engine: Engine, table_name: str
) -> None:
    original = world()
    store = CareerStore(runtime_engine, original.workspace_id)
    store.save(original, expected_generation=0)
    event = job_event(original, evidence_refs=(evidence_ref(original.profile.evidence[0]),))
    store.append_events((event,))
    table = schema.metadata.tables[table_name]
    with pytest.raises(IntegrityError) as caught:
        with runtime_engine.begin() as connection:
            connection.execute(
                delete(table).where(table.c.workspace_id == original.workspace_id.root)
            )
    assert caught.value.orig.sqlstate == "23514"
    assert store.load_events() == (event,)


def test_temporary_ledger_shadow_cannot_resurrect_a_deleted_workspace(
    runtime_engine: Engine,
) -> None:
    original = world()
    store = CareerStore(runtime_engine, original.workspace_id)
    store.save(original, expected_generation=0)
    with runtime_engine.connect() as connection:
        header = dict(connection.execute(select(schema.career_workspaces)).mappings().one())
        schema_name = connection.exec_driver_sql("SELECT current_schema()").scalar_one()
    store.delete(original.as_of + timedelta(days=1))
    scoped_workspaces = schema.career_workspaces.to_metadata(MetaData(), schema=schema_name)
    with pytest.raises(IntegrityError) as caught:
        with runtime_engine.begin() as connection:
            connection.exec_driver_sql(
                "CREATE TEMP TABLE deletion_ledger (workspace_id text, deleted_at timestamptz)"
            )
            connection.execute(insert(scoped_workspaces), header)
    assert caught.value.orig.sqlstate == "23514"
    assert store.deletion_record() is not None
