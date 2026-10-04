"""Resolve new observations against actual state; retain closed historical events."""

from sqlalchemy import Connection, select

from actual.career.events import (
    ApplicationStatusRecorded,
    CVRecommended,
    DraftReviewed,
    FitAssessmentRecorded,
    JobAdded,
    RequirementsReviewed,
    WorkEvent,
    validate_references,
)
from actual.career.snapshot import CareerSnapshot
from actual.core.primitives import canonical_bytes, load_contract
from actual.core.references import EvidenceRef
from actual.profile.contracts import evidence_ref

from . import schema
from .errors import CorruptStorageError, PersistenceError, UnsupportedEventError
from .mapping import Row, catalog, checksum


def validate_event(event: WorkEvent, snapshot: CareerSnapshot) -> None:
    try:
        _validate_event(event, snapshot)
    except (ValueError, TypeError, KeyError):
        raise PersistenceError("Observation failed current-state validation") from None


def _validate_event(event: WorkEvent, snapshot: CareerSnapshot) -> None:
    if event.workspace_id != snapshot.workspace_id:
        raise ValueError("Event belongs to another workspace")
    if isinstance(event.payload, FitAssessmentRecorded):
        raise UnsupportedEventError("Assessment observations require a future Assessment contract")
    validate_references(
        event,
        catalog(snapshot),
        tuple(evidence_ref(record) for record in snapshot.profile.evidence),
    )
    payload = event.payload
    jobs = {job.id.root: job for job in snapshot.jobs}
    if isinstance(payload, JobAdded):
        if event.occurred_at < jobs[payload.job.object_id.root].posted_at:
            raise ValueError("Job observation precedes posting")
    elif isinstance(payload, RequirementsReviewed):
        requirements = {record.id.root: record for record in snapshot.requirements}
        for reference in payload.requirements:
            record = requirements[reference.object_id.root]
            review = record.review
            if (
                record.job_id != payload.job.object_id
                or review is None
                or (
                    review.decision != "accepted"
                    or review.reviewer_id != payload.reviewer_id
                    or review.reviewed_at != payload.reviewed_at
                )
            ):
                raise ValueError("Requirement observation differs from stored review")
    elif isinstance(payload, CVRecommended):
        cvs = {cv.id.root: cv for cv in snapshot.cvs}
        if payload.profile.object_id != snapshot.profile.id or any(
            cvs[reference.object_id.root].profile_id != payload.profile.object_id
            for reference in payload.cvs
        ):
            raise ValueError("CV observation differs from stored profile relationships")
    elif isinstance(payload, DraftReviewed):
        drafts = {draft.id.root: draft for draft in snapshot.drafts}
        draft = drafts[payload.draft.object_id.root]
        review = draft.review
        if review is None or (
            review.decision != payload.decision
            or review.reviewer_id != payload.reviewer_id
            or review.reviewed_at != payload.reviewed_at
        ):
            raise ValueError("Draft observation differs from stored content review")
        if any(reference.profile_id != draft.profile_id for reference in event.evidence_refs):
            raise ValueError("Draft observation cites another profile")
        if payload.decision == "accepted":
            claims = {claim.id: claim for claim in snapshot.profile.claims}
            evidence = {record.id: record for record in snapshot.profile.evidence}
            expected: set[EvidenceRef] = set()
            for proposal in draft.assertions:
                for claim_reference in proposal.source_claim_refs:
                    claim = claims[claim_reference.claim_id]
                    if (
                        claim.status != "reviewed_supported"
                        or (claim.assertion.kind, claim.assertion.subject, claim.assertion.unit)
                        != (
                            proposal.assertion.kind,
                            proposal.assertion.subject,
                            proposal.assertion.unit,
                        )
                        or claim.assertion.value < proposal.assertion.value
                    ):
                        continue
                    for source in claim.evidence_refs:
                        source_evidence = evidence[source.evidence_id]
                        if (
                            source_evidence.qualifies_support
                            and source_evidence.assertion.value >= proposal.assertion.value
                        ):
                            expected.add(source)
            if not expected or set(event.evidence_refs) != expected:
                raise ValueError(
                    "Accepted draft observation differs from its qualifying provenance"
                )
    elif isinstance(payload, ApplicationStatusRecorded):
        applications = {app.id.root: app for app in snapshot.applications}
        app = applications[payload.application.object_id.root]
        observed = app.history[-1]
        previous = app.history[-2].state if len(app.history) > 1 else None
        if (
            payload.previous_state != previous
            or payload.state != observed.state
            or payload.basis != observed.basis
            or payload.external_manual != observed.external_manual
            or event.actor_id != observed.actor_id
            or event.occurred_at != observed.occurred_at
            or event.recorded_at < observed.recorded_at
        ):
            raise ValueError("Application observation differs from stored history")


def event_rows(event: WorkEvent) -> dict[str, list[Row]]:
    workspace = event.workspace_id.root
    event_id = event.event_id.root
    return {
        schema.work_events.name: [
            {
                "workspace_id": workspace,
                "event_id": event_id,
                "source": event.source,
                "source_event_id": event.source_event_id.root if event.source_event_id else None,
                "occurred_at": event.occurred_at,
                "recorded_at": event.recorded_at,
                "classification": event.privacy_classification,
                "activity": event.activity,
                "payload": canonical_bytes(event).decode("utf-8"),
                "payload_digest": checksum(event),
            }
        ],
        schema.event_object_refs.name: [
            {
                "workspace_id": workspace,
                "event_id": event_id,
                "position": index,
                "kind": ref.kind,
                "object_id": ref.object_id.root,
                "revision": ref.revision,
                "digest": ref.content_digest,
                "classification": ref.classification,
            }
            for index, ref in enumerate(event.business_objects)
        ],
        schema.event_evidence_refs.name: [
            {
                "workspace_id": workspace,
                "event_id": event_id,
                "position": index,
                "profile_id": ref.profile_id.root,
                "evidence_id": ref.evidence_id.root,
                "revision": ref.revision,
                "digest": ref.content_digest,
                "classification": ref.classification,
            }
            for index, ref in enumerate(event.evidence_refs)
        ],
    }


def load_event(connection: Connection, row: Row) -> WorkEvent:
    try:
        event = load_contract(WorkEvent, row["payload"].encode("utf-8"))
        expected = event_rows(event)
        if row != expected[schema.work_events.name][0]:
            raise ValueError("Event projection mismatch")
        for table in (schema.event_object_refs, schema.event_evidence_refs):
            actual = [
                dict(item)
                for item in connection.execute(
                    select(table)
                    .where(
                        table.c.workspace_id == event.workspace_id.root,
                        table.c.event_id == event.event_id.root,
                    )
                    .order_by(table.c.position)
                ).mappings()
            ]
            if actual != expected[table.name]:
                raise ValueError("Event reference projection mismatch")
        return event
    except (ValueError, TypeError, KeyError, UnicodeError):
        raise CorruptStorageError("Stored event failed integrity validation") from None
