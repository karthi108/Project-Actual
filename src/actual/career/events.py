"""Closed career observations; no command, authentication or effect authority."""

from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from actual.core.events import EventHeader
from actual.core.primitives import ActorId, Contract, Instant, canonical_data, content_digest
from actual.core.references import BusinessObjectRef, EvidenceRef, ObjectKind

from .applications import (
    ApplicationState,
    ObservationBasis,
    allowed_transition,
)

type Activity = Literal[
    "job_added",
    "requirements_reviewed",
    "fit_assessment_recorded",
    "cv_recommended",
    "draft_reviewed",
    "application_status_recorded",
]
type Count = Annotated[int, Field(strict=True, ge=0, le=1000)]


def _kind(reference: BusinessObjectRef, expected: ObjectKind) -> None:
    if reference.kind != expected:
        raise ValueError("Payload reference has the wrong business-object kind")


def _unique(references: tuple[BusinessObjectRef, ...]) -> None:
    keys = [(reference.kind, reference.object_id.root) for reference in references]
    if len(set(keys)) != len(keys):
        raise ValueError("Payload references cannot repeat a business object")


class JobAdded(Contract):
    activity: Literal["job_added"] = "job_added"
    job: BusinessObjectRef

    @model_validator(mode="after")
    def reference_kinds(self) -> Self:
        _kind(self.job, "job")
        return self


class RequirementsReviewed(Contract):
    activity: Literal["requirements_reviewed"] = "requirements_reviewed"
    job: BusinessObjectRef
    requirements: Annotated[tuple[BusinessObjectRef, ...], Field(min_length=1, max_length=256)]
    reviewer_id: ActorId
    reviewed_at: Instant

    @model_validator(mode="after")
    def reference_kinds(self) -> Self:
        _kind(self.job, "job")
        for reference in self.requirements:
            _kind(reference, "requirement")
        _unique(self.requirements)
        return self


class AssessmentCounts(Contract):
    """Bounded requirement-category counts, never a fit or hiring score."""

    supported: Count
    partial: Count
    gap: Count
    unknown: Count
    conflict: Count


class FitAssessmentRecorded(Contract):
    activity: Literal["fit_assessment_recorded"] = "fit_assessment_recorded"
    job: BusinessObjectRef
    profile: BusinessObjectRef
    assessment: BusinessObjectRef
    counts: AssessmentCounts

    @model_validator(mode="after")
    def reference_kinds(self) -> Self:
        _kind(self.job, "job")
        _kind(self.profile, "profile")
        _kind(self.assessment, "assessment")
        return self


class CVRecommended(Contract):
    activity: Literal["cv_recommended"] = "cv_recommended"
    job: BusinessObjectRef
    profile: BusinessObjectRef
    cvs: Annotated[tuple[BusinessObjectRef, ...], Field(min_length=1, max_length=32)]

    @model_validator(mode="after")
    def reference_kinds(self) -> Self:
        _kind(self.job, "job")
        _kind(self.profile, "profile")
        for reference in self.cvs:
            _kind(reference, "cv")
        _unique(self.cvs)
        return self


class DraftReviewed(Contract):
    activity: Literal["draft_reviewed"] = "draft_reviewed"
    draft: BusinessObjectRef
    decision: Literal["accepted", "rejected"]
    reviewer_id: ActorId
    reviewed_at: Instant

    @model_validator(mode="after")
    def reference_kinds(self) -> Self:
        _kind(self.draft, "draft")
        return self


class ApplicationStatusRecorded(Contract):
    activity: Literal["application_status_recorded"] = "application_status_recorded"
    application: BusinessObjectRef
    previous_state: ApplicationState | None
    state: ApplicationState
    basis: ObservationBasis
    external_manual: Annotated[bool, Field(strict=True)] = False

    @model_validator(mode="after")
    def reported_transition(self) -> Self:
        _kind(self.application, "application")
        if self.previous_state is None:
            if self.state != "preparing" or self.external_manual:
                raise ValueError("Initial application observation starts with preparing")
        elif not allowed_transition(
            self.previous_state, self.state, self.basis, self.external_manual
        ):
            raise ValueError("Application observation has a disallowed transition")
        return self


type EventPayload = Annotated[
    JobAdded
    | RequirementsReviewed
    | FitAssessmentRecorded
    | CVRecommended
    | DraftReviewed
    | ApplicationStatusRecorded,
    Field(discriminator="activity"),
]


def _payload_refs(payload: EventPayload) -> tuple[BusinessObjectRef, ...]:
    if isinstance(payload, JobAdded):
        return (payload.job,)
    if isinstance(payload, RequirementsReviewed):
        return (payload.job, *payload.requirements)
    if isinstance(payload, FitAssessmentRecorded):
        return (payload.job, payload.profile, payload.assessment)
    if isinstance(payload, CVRecommended):
        return (payload.job, payload.profile, *payload.cvs)
    if isinstance(payload, DraftReviewed):
        return (payload.draft,)
    return (payload.application,)


class WorkEvent(EventHeader):
    activity: Activity
    payload: EventPayload

    @model_validator(mode="after")
    def observation_invariants(self) -> Self:
        if self.activity != self.payload.activity:
            raise ValueError("Event activity differs from its payload discriminator")
        expected = _payload_refs(self.payload)
        if set(self.business_objects) != set(expected):
            raise ValueError("Envelope references must exactly match payload references")
        if isinstance(self.payload, (FitAssessmentRecorded, CVRecommended)) and any(
            reference.profile_id != self.payload.profile.object_id
            for reference in self.evidence_refs
        ):
            raise ValueError("Evidence reference belongs to a different profile")
        if isinstance(self.payload, (RequirementsReviewed, DraftReviewed)):
            if self.payload.reviewer_id != self.actor_id:
                raise ValueError("Review attribution differs from event actor")
            if self.payload.reviewed_at > self.occurred_at:
                raise ValueError("Review cannot follow its reported occurrence")
        reviewed_assessment = isinstance(self.payload, FitAssessmentRecorded) and any(
            (
                self.payload.counts.supported,
                self.payload.counts.partial,
                self.payload.counts.gap,
                self.payload.counts.conflict,
            )
        )
        if (
            reviewed_assessment
            or isinstance(self.payload, DraftReviewed)
            and self.payload.decision == "accepted"
        ) and not self.evidence_refs:
            raise ValueError("Reviewed assessment/accepted draft requires evidence references")
        return self


def validate_references(
    event: WorkEvent,
    objects: tuple[BusinessObjectRef, ...],
    evidence: tuple[EvidenceRef, ...],
) -> None:
    """Compare with supplied current catalog snapshots; no storage or authentication."""
    checked = WorkEvent.model_validate(event)
    current_objects = tuple(BusinessObjectRef.model_validate(ref) for ref in objects)
    current_evidence = tuple(EvidenceRef.model_validate(ref) for ref in evidence)
    if any(ref.workspace_id != checked.workspace_id for ref in current_objects) or any(
        ref.workspace_id != checked.workspace_id for ref in current_evidence
    ):
        raise ValueError("Trusted catalog contains a foreign workspace")
    object_keys = [(ref.kind, ref.object_id.root) for ref in current_objects]
    evidence_keys = [(ref.profile_id.root, ref.evidence_id.root) for ref in current_evidence]
    if len(set(object_keys)) != len(object_keys) or len(set(evidence_keys)) != len(evidence_keys):
        raise ValueError("Current catalog cannot contain duplicate object identities")
    if not set(checked.business_objects) <= set(current_objects):
        raise ValueError("Business-object reference is missing, stale or content-mismatched")
    if not set(checked.evidence_refs) <= set(current_evidence):
        raise ValueError("Evidence reference is missing, stale or content-mismatched")


def delivery_relation(
    prior: WorkEvent, current: WorkEvent
) -> Literal["unrelated", "duplicate", "conflict"]:
    """Pure redelivery classification; it does not persist or suppress effects."""
    previous, incoming = WorkEvent.model_validate(prior), WorkEvent.model_validate(current)
    if previous.source_event_id is None or incoming.source_event_id is None:
        return "unrelated"
    previous_key = (previous.workspace_id, previous.source, previous.source_event_id)
    incoming_key = (incoming.workspace_id, incoming.source, incoming.source_event_id)
    if previous_key != incoming_key:
        return "unrelated"
    first = _semantic_digest(previous)
    second = _semantic_digest(incoming)
    return "duplicate" if first == second else "conflict"


def _semantic_digest(event: WorkEvent) -> str:
    data = event.model_dump(mode="json", exclude={"event_id", "recorded_at"})
    # Envelope reference collections are sets. Payload collections retain their
    # authored ordering, so a changed ordered recommendation remains a conflict.
    for field in ("business_objects", "evidence_refs"):
        data[field] = sorted(data[field], key=canonical_data)
    return content_digest(data)
