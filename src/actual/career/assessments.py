"""Transient source-bound evidence matrices, not hiring scores or authority."""

from typing import Annotated, Literal, Self
from uuid import UUID, uuid5

from pydantic import Field, field_validator, model_validator

from actual.career.events import AssessmentCounts
from actual.career.requirements import InterpretedRequirement
from actual.core.primitives import (
    AssessmentId,
    Contract,
    Digest,
    JobId,
    Label,
    ProfileId,
    RequirementId,
    Revision,
    WorkspaceId,
    content_digest,
)
from actual.core.references import ClaimRef, EvidenceRef

type FitStatus = Literal["supported", "partial", "gap", "unknown", "conflict"]
type AssessmentReason = Literal[
    "reviewed_support",
    "reviewed_skill_shortfall",
    "reviewed_threshold_shortfall",
    "reviewed_no_support",
    "unreviewed_or_missing",
    "conflicting_evidence",
    "unresolved_requirement",
]
_ASSESSMENT_NAMESPACE = UUID("e3f8e7bf-711b-4c34-8e92-07f403ea4db3")


def assessment_identity(payload: dict[str, object]) -> AssessmentId:
    return AssessmentId("assessment_" + uuid5(_ASSESSMENT_NAMESPACE, content_digest(payload)).hex)


type RequirementLike = InterpretedRequirement


class RequirementAssessment(Contract):
    requirement: RequirementLike
    status: FitStatus
    claim_refs: Annotated[tuple[ClaimRef, ...], Field(max_length=128)] = ()
    evidence_refs: Annotated[tuple[EvidenceRef, ...], Field(max_length=256)] = ()
    observed_value: Annotated[int, Field(strict=True, ge=0, le=600)] | None = None
    declared_shortfall: Annotated[bool, Field(strict=True)] = False
    reason: AssessmentReason
    explanation: Label

    @model_validator(mode="after")
    def decision_structure(self) -> Self:
        if len({ref.claim_id for ref in self.claim_refs}) != len(self.claim_refs):
            raise ValueError("Assessment claim references cannot repeat")
        if len({ref.evidence_id for ref in self.evidence_refs}) != len(self.evidence_refs):
            raise ValueError("Assessment evidence references cannot repeat")
        refs: tuple[ClaimRef | EvidenceRef, ...] = (*self.claim_refs, *self.evidence_refs)
        if any(
            ref.workspace_id != self.requirement.workspace_id
            or ref.classification != self.requirement.classification
            for ref in refs
        ):
            raise ValueError("Assessment references must retain requirement owner/privacy")
        if self.requirement.resolution == "abstained":
            if (
                self.status != "unknown"
                or self.reason != "unresolved_requirement"
                or self.claim_refs
                or self.evidence_refs
                or self.observed_value is not None
                or self.declared_shortfall
            ):
                raise ValueError("Unresolved requirements cannot imply scoped evidence support")
            return self
        assertion = self.requirement.assertion
        assert assertion is not None
        if self.requirement.constraints.experience_scope == "legacy_backend" and self.status in (
            "supported",
            "partial",
        ):
            raise ValueError("Generic profile months cannot establish positive backend scope")
        maximum = {"skill": 3, "language": 6, "experience": 600}[assertion.kind]
        if self.observed_value is not None and self.observed_value > maximum:
            raise ValueError("Observed value must retain the assertion's bounded unit")
        if self.status in ("supported", "partial", "gap"):
            if not self.claim_refs or not self.evidence_refs or self.observed_value is None:
                raise ValueError("Positive or explicit shortfall decisions require scoped support")
            if self.status == "supported" and (
                self.reason != "reviewed_support" or self.observed_value < assertion.value
            ):
                raise ValueError("Supported decision must cover the explicit threshold")
            if self.status == "partial" and (
                self.reason != "reviewed_skill_shortfall"
                or assertion.kind != "skill"
                or not 0 < self.observed_value < assertion.value
            ):
                raise ValueError("Partial means reviewed lower nonzero skill support")
            if self.status == "gap" and not (
                self.observed_value < assertion.value
                and (
                    assertion.kind != "skill"
                    and self.reason == "reviewed_threshold_shortfall"
                    or assertion.kind == "skill"
                    and self.observed_value == 0
                    and self.reason == "reviewed_no_support"
                )
            ):
                raise ValueError("A gap needs an explicit reviewed unmet threshold")
        elif self.observed_value is not None:
            raise ValueError("Uncertain decisions cannot expose reviewed positive scope")
        if self.status == "unknown" and self.reason != "unreviewed_or_missing":
            raise ValueError("Unknown decision preserves missing/unreviewed support")
        if self.status == "conflict" and self.reason != "conflicting_evidence":
            raise ValueError("Conflicts require explicit contrary handling")
        if self.status == "conflict" and not self.evidence_refs:
            raise ValueError("Conflicts require current scoped evidence references")
        if self.declared_shortfall and self.status != "unknown":
            raise ValueError("Declared shortfall describes an unverified declaration only")
        return self


class JobFitAssessment(Contract):
    """Revalidate against current sources before reuse; no storage/event authority."""

    id: AssessmentId
    workspace_id: WorkspaceId
    classification: Literal["synthetic"]
    job_id: JobId
    job_revision: Revision
    job_digest: Digest
    profile_id: ProfileId
    profile_revision: Revision
    profile_digest: Digest
    rows: Annotated[tuple[RequirementAssessment, ...], Field(max_length=8)]
    proposal_only: Literal[True] = True

    @field_validator("proposal_only", mode="before")
    @classmethod
    def untrusted_only(cls, value: object) -> object:
        if value is not True:
            raise ValueError("An assessment is always an untrusted proposal")
        return value

    @model_validator(mode="after")
    def references_and_order(self) -> Self:
        identities: set[RequirementId] = set()
        subjects: set[str] = set()
        starts: list[tuple[int, str]] = []
        for row in self.rows:
            requirement = row.requirement
            if (
                requirement.workspace_id != self.workspace_id
                or requirement.classification != self.classification
                or requirement.job_id != self.job_id
                or requirement.job_revision != self.job_revision
                or requirement.job_digest != self.job_digest
            ):
                raise ValueError("Assessment must bind one exact owner-scoped job revision")
            if requirement.id in identities:
                raise ValueError("Assessment requirement identity cannot repeat")
            identities.add(requirement.id)
            if requirement.canonical_concept is not None:
                if requirement.canonical_concept in subjects:
                    raise ValueError("One canonical concept cannot add duplicate weight")
                subjects.add(requirement.canonical_concept)
            refs: tuple[ClaimRef | EvidenceRef, ...] = (*row.claim_refs, *row.evidence_refs)
            if any(ref.profile_id != self.profile_id for ref in refs):
                raise ValueError("Assessment references cannot select another profile")
            starts.append((requirement.concept_start, requirement.id.root))
        if starts != sorted(starts):
            raise ValueError("Assessment rows require deterministic source order")
        if self.id != assessment_identity(self.model_dump(mode="json", exclude={"id"})):
            raise ValueError("Assessment identity must bind its complete deterministic content")
        return self

    @property
    def counts(self) -> AssessmentCounts:
        return AssessmentCounts(
            supported=sum(row.status == "supported" for row in self.rows),
            partial=sum(row.status == "partial" for row in self.rows),
            gap=sum(row.status == "gap" for row in self.rows),
            unknown=sum(row.status == "unknown" for row in self.rows),
            conflict=sum(row.status == "conflict" for row in self.rows),
        )

    @property
    def content_digest(self) -> str:
        return content_digest(self.model_dump(mode="json"))

    @property
    def strengths(self) -> tuple[RequirementAssessment, ...]:
        return tuple(row for row in self.rows if row.status == "supported")

    @property
    def gaps(self) -> tuple[RequirementAssessment, ...]:
        return tuple(row for row in self.rows if row.status in ("partial", "gap"))

    @property
    def unknowns(self) -> tuple[RequirementAssessment, ...]:
        return tuple(row for row in self.rows if row.status in ("unknown", "conflict"))
