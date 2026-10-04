"""Versioned factual proposals and exact-content reviews; no sending authority."""

from typing import Annotated, Self

from pydantic import Field, model_validator

from actual.core.primitives import (
    Classification,
    Contract,
    CVId,
    DraftId,
    Label,
    ProfileId,
    Revision,
    Text,
    WorkspaceId,
    classification_allows,
    content_digest,
)
from actual.core.references import ClaimRef
from actual.core.workflow import ContentReview
from actual.profile.contracts import Assertion


class CVVariant(Contract):
    id: CVId
    workspace_id: WorkspaceId
    profile_id: ProfileId
    revision: Revision
    classification: Classification
    name: Label
    summary: Text
    claim_refs: Annotated[tuple[ClaimRef, ...], Field(max_length=200)]

    @property
    def content_digest(self) -> str:
        return content_digest(self.model_dump(mode="json"))

    @model_validator(mode="after")
    def valid_claim_owners(self) -> Self:
        identities = [ref.claim_id.root for ref in self.claim_refs]
        if len(set(identities)) != len(identities):
            raise ValueError("CV cannot repeat a profile claim")
        if any(
            ref.workspace_id != self.workspace_id or ref.profile_id != self.profile_id
            for ref in self.claim_refs
        ):
            raise ValueError("CV claims must belong to its workspace and profile")
        if any(
            not classification_allows(self.classification, ref.classification)
            for ref in self.claim_refs
        ):
            raise ValueError("CV classification cannot understate or mix its claim sources")
        return self


class DraftAssertion(Contract):
    assertion: Assertion
    text: Text
    source_claim_refs: Annotated[tuple[ClaimRef, ...], Field(max_length=200)]

    @model_validator(mode="after")
    def distinct_sources(self) -> Self:
        identities = [ref.claim_id.root for ref in self.source_claim_refs]
        if len(set(identities)) != len(identities):
            raise ValueError("Draft assertion cannot repeat a supporting profile claim")
        return self


class Draft(Contract):
    id: DraftId
    workspace_id: WorkspaceId
    profile_id: ProfileId
    revision: Revision
    classification: Classification
    name: Label
    summary: Text
    assertions: Annotated[tuple[DraftAssertion, ...], Field(max_length=200)]
    review: ContentReview | None = None

    @property
    def content_digest(self) -> str:
        return content_digest(self.model_dump(mode="json", exclude={"review"}))

    @model_validator(mode="after")
    def valid_owners_and_review(self) -> Self:
        if any(
            ref.workspace_id != self.workspace_id or ref.profile_id != self.profile_id
            for assertion in self.assertions
            for ref in assertion.source_claim_refs
        ):
            raise ValueError("Draft sources must belong to its workspace and profile")
        if any(
            not classification_allows(self.classification, ref.classification)
            for assertion in self.assertions
            for ref in assertion.source_claim_refs
        ):
            raise ValueError("Draft classification cannot understate or mix its claim sources")
        if self.review is not None and (
            self.review.revision != self.revision
            or self.review.content_digest != self.content_digest
        ):
            raise ValueError("Review does not identify this exact draft revision")
        return self
