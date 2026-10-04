"""Typed version-bound references; owner fields confer no authority."""

from typing import Literal, Self

from pydantic import model_validator

from .primitives import (
    ApplicationId,
    AssessmentId,
    ClaimId,
    Classification,
    CompanyId,
    Contract,
    CVId,
    Digest,
    DraftId,
    EvidenceId,
    JobId,
    ProfileId,
    RequirementId,
    Revision,
    WorkspaceId,
)

type ObjectId = (
    CompanyId
    | JobId
    | ProfileId
    | ClaimId
    | EvidenceId
    | CVId
    | DraftId
    | ApplicationId
    | RequirementId
    | AssessmentId
)
type ObjectKind = Literal[
    "company",
    "job",
    "profile",
    "claim",
    "evidence",
    "cv",
    "draft",
    "application",
    "requirement",
    "assessment",
]


class BusinessObjectRef(Contract):
    workspace_id: WorkspaceId
    classification: Classification
    kind: ObjectKind
    object_id: ObjectId
    revision: Revision
    content_digest: Digest

    @model_validator(mode="after")
    def kind_matches(self) -> Self:
        if self.object_id.prefix != self.kind:
            raise ValueError("Object kind and identifier type differ")
        return self


class EvidenceRef(Contract):
    workspace_id: WorkspaceId
    classification: Classification
    profile_id: ProfileId
    evidence_id: EvidenceId
    revision: Revision
    content_digest: Digest


class ClaimRef(Contract):
    workspace_id: WorkspaceId
    classification: Classification
    profile_id: ProfileId
    claim_id: ClaimId
    revision: Revision
    content_digest: Digest
