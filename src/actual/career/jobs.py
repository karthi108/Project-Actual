"""Source-backed job revisions and explicitly proposed requirement interpretations."""

from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from actual.core.primitives import (
    Classification,
    CompanyId,
    Contract,
    Digest,
    Instant,
    JobId,
    Label,
    OpportunityId,
    RequirementId,
    Revision,
    SourceReference,
    Text,
    WorkspaceId,
    content_digest,
)
from actual.core.workflow import ContentReview
from actual.profile.contracts import Assertion


class Company(Contract):
    id: CompanyId
    workspace_id: WorkspaceId
    revision: Revision
    classification: Classification
    name: Label
    context: Text

    @property
    def content_digest(self) -> str:
        return content_digest(self.model_dump(mode="json"))


class Job(Contract):
    id: JobId
    workspace_id: WorkspaceId
    revision: Revision
    classification: Classification
    company_id: CompanyId
    opportunity_id: OpportunityId
    title: Label
    text: Text
    source_reference: SourceReference
    posted_at: Instant
    decision: Literal["new", "pursuing", "rejected", "archived"]

    @property
    def content_digest(self) -> str:
        return content_digest(self.model_dump(mode="json"))


class Requirement(Contract):
    """A normalized proposal; a valid schema never proves accurate extraction."""

    id: RequirementId
    workspace_id: WorkspaceId
    revision: Revision
    classification: Classification
    job_id: JobId
    job_revision: Revision
    job_digest: Digest
    assertion: Assertion
    priority: Literal["essential", "preferred", "ambiguous"]
    source_start: Annotated[int, Field(strict=True, ge=0, le=12000)]
    source_end: Annotated[int, Field(strict=True, gt=0, le=12000)]
    source_quote: Text
    origin: Literal["user_report", "ai_proposal"]
    review: ContentReview | None = None

    @property
    def content_digest(self) -> str:
        return content_digest(self.model_dump(mode="json", exclude={"review"}))

    @model_validator(mode="after")
    def valid_source_and_review(self) -> Self:
        if self.source_end <= self.source_start:
            raise ValueError("Requirement source span must have positive extent")
        if self.review is not None and (
            self.review.revision != self.revision
            or self.review.content_digest != self.content_digest
        ):
            raise ValueError("Review does not identify this exact requirement revision")
        return self
