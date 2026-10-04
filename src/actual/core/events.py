"""Shared observation metadata only; concrete activities/payloads belong to domains."""

from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from .primitives import (
    ActorId,
    Classification,
    Contract,
    CorrelationId,
    EventId,
    Instant,
    SourceEventId,
    WorkspaceId,
    classification_allows,
)
from .references import BusinessObjectRef, EvidenceRef

type EventSource = Literal["manual", "careerlab", "local_domain"]
type ObjectRefs = Annotated[tuple[BusinessObjectRef, ...], Field(min_length=1, max_length=256)]
type EvidenceRefs = Annotated[tuple[EvidenceRef, ...], Field(max_length=256)]


class EventHeader(Contract):
    """Not a complete semantic event; contains no activity, payload or authority."""

    event_id: EventId
    workspace_id: WorkspaceId
    actor_id: ActorId
    occurred_at: Instant
    recorded_at: Instant
    source: EventSource
    business_objects: ObjectRefs
    privacy_classification: Classification
    source_event_id: SourceEventId | None = None
    correlation_id: CorrelationId | None = None
    evidence_refs: EvidenceRefs = ()

    @model_validator(mode="after")
    def metadata_invariants(self) -> Self:
        if self.recorded_at < self.occurred_at:
            raise ValueError("Recording cannot precede source occurrence")
        keys = [(ref.kind, ref.object_id.root) for ref in self.business_objects]
        if len(set(keys)) != len(keys):
            raise ValueError("References cannot repeat a business object")
        if any(ref.workspace_id != self.workspace_id for ref in self.business_objects):
            raise ValueError("Business-object reference crosses event workspace")
        if any(ref.workspace_id != self.workspace_id for ref in self.evidence_refs):
            raise ValueError("Evidence reference crosses event workspace")
        if any(
            not classification_allows(self.privacy_classification, ref.classification)
            for ref in self.business_objects
        ) or any(
            not classification_allows(self.privacy_classification, ref.classification)
            for ref in self.evidence_refs
        ):
            raise ValueError("Event classification cannot understate or mix referenced data")
        evidence_keys = [(ref.profile_id.root, ref.evidence_id.root) for ref in self.evidence_refs]
        if len(set(evidence_keys)) != len(evidence_keys):
            raise ValueError("Evidence references cannot repeat an evidence object")
        return self
