"""Immutable structured assertions, reviewed sources and owner-scoped profiles.

These contracts establish bounded factual support, not prose truth, source
authenticity, hiring suitability or authorization.
"""

from typing import Annotated, Literal, Self

from pydantic import Field, ValidationError, model_validator

from actual.core.primitives import (
    ActorId,
    ClaimId,
    Classification,
    Contract,
    Digest,
    EvidenceId,
    Instant,
    Label,
    ProfileId,
    Revision,
    SourceReference,
    Symbol,
    Text,
    WorkspaceId,
    classification_allows,
    content_digest,
)
from actual.core.references import ClaimRef, EvidenceRef
from actual.core.workflow import ContentReview

type ClaimStatus = Literal[
    "self_reported", "candidate_support", "reviewed_supported", "contradicted", "withdrawn"
]
type AssertionKind = Literal["skill", "language", "experience"]
type AssertionUnit = Literal["skill_level", "cefr_level", "months"]


class Assertion(Contract):
    kind: AssertionKind
    subject: Symbol
    unit: AssertionUnit
    value: Annotated[int, Field(strict=True, ge=0, le=600)]

    @model_validator(mode="after")
    def scope(self) -> Self:
        units: dict[AssertionKind, tuple[AssertionUnit, int]] = {
            "skill": ("skill_level", 3),
            "language": ("cefr_level", 6),
            "experience": ("months", 600),
        }
        unit, maximum = units[self.kind]
        if self.unit != unit or self.value > maximum:
            raise ValueError("Assertion kind, unit and value scope differ")
        if (self.kind == "experience") != (self.subject == "experience"):
            raise ValueError("Experience duration requires the experience subject")
        return self


def _same_scope(left: Assertion, right: Assertion) -> bool:
    return (left.kind, left.subject, left.unit) == (right.kind, right.subject, right.unit)


class EvidenceReview(Contract):
    reviewer_id: ActorId
    kind: Literal[
        "human_confirmation", "source_review", "independent_verification", "synthetic_review"
    ]
    method: Label
    reviewed_at: Instant
    content_digest: Digest
    independent_source_reference: SourceReference | None = None

    @model_validator(mode="after")
    def independent_source(self) -> Self:
        if self.kind == "independent_verification" and self.independent_source_reference is None:
            raise ValueError("Independent verification requires a separate source reference")
        return self


class EvidenceRecord(Contract):
    id: EvidenceId
    workspace_id: WorkspaceId
    profile_id: ProfileId
    revision: Revision
    classification: Classification
    assertion: Assertion
    relation: Literal["supports", "contradicts"]
    excerpt: Text
    source_kind: Literal[
        "user_report", "project_artifact", "imported_document", "ai_proposal", "synthetic_fixture"
    ]
    source_reference: SourceReference
    source_actor_id: ActorId | None = None
    collected_at: Instant
    review: EvidenceReview | None = None
    status: Literal["active", "withdrawn"] = "active"

    @property
    def content_digest(self) -> str:
        return content_digest(
            self.model_dump(
                mode="json",
                include={
                    "assertion",
                    "relation",
                    "excerpt",
                    "source_kind",
                    "source_reference",
                    "source_actor_id",
                    "collected_at",
                    "classification",
                },
            )
        )

    @property
    def snapshot_digest(self) -> str:
        """Dependency identity includes current review and withdrawal state."""
        return content_digest(self.model_dump(mode="json"))

    @model_validator(mode="after")
    def review_binding(self) -> Self:
        if self.source_kind == "synthetic_fixture" and self.classification != "synthetic":
            raise ValueError("Synthetic evidence cannot be classified as real source data")
        if self.review is None:
            return self
        if self.review.content_digest != self.content_digest:
            raise ValueError("Evidence review does not bind the current source content")
        if self.review.reviewed_at < self.collected_at:
            raise ValueError("Evidence review precedes source collection")
        if self.review.kind == "synthetic_review" and self.classification != "synthetic":
            raise ValueError("Synthetic review cannot establish real-profile support")
        if self.review.kind == "independent_verification" and (
            self.review.independent_source_reference is None
            or self.review.independent_source_reference.strip() == self.source_reference.strip()
        ):
            raise ValueError("Independent verification requires a distinct separate source")
        return self

    @property
    def _qualifies_review(self) -> bool:
        if self.status != "active" or self.review is None:
            return False
        if self.review.kind == "human_confirmation":
            return False
        if self.source_kind in ("user_report", "ai_proposal"):
            return self.review.kind == "independent_verification"
        return self.review.kind in ("source_review", "independent_verification", "synthetic_review")

    @property
    def qualifies_support(self) -> bool:
        """Reviewed positive structured support, never a verification certificate."""
        return self.relation == "supports" and self._qualifies_review


class Claim(Contract):
    id: ClaimId
    workspace_id: WorkspaceId
    profile_id: ProfileId
    revision: Revision
    classification: Classification
    assertion: Assertion
    text: Text
    origin: Literal["user_report", "ai_proposal", "imported_document", "synthetic_fixture"]
    asserted_by: ActorId | None = None
    asserted_at: Instant | None = None
    status: ClaimStatus
    evidence_refs: Annotated[tuple[EvidenceRef, ...], Field(max_length=64)] = ()
    review: ContentReview | None = None

    @property
    def content_digest(self) -> str:
        return content_digest(
            self.model_dump(
                mode="json",
                include={
                    "assertion",
                    "text",
                    "origin",
                    "asserted_by",
                    "asserted_at",
                    "classification",
                    "evidence_refs",
                },
            )
        )

    @property
    def snapshot_digest(self) -> str:
        """Downstream identity includes the assertion's current review/status."""
        return content_digest(self.model_dump(mode="json"))

    @model_validator(mode="after")
    def review_binding(self) -> Self:
        if self.origin == "synthetic_fixture" and self.classification != "synthetic":
            raise ValueError("Synthetic assertions cannot be classified as real-profile facts")
        if len({ref.evidence_id.root for ref in self.evidence_refs}) != len(self.evidence_refs):
            raise ValueError("Claim evidence references must be unique")
        if any(
            not classification_allows(self.classification, ref.classification)
            for ref in self.evidence_refs
        ):
            raise ValueError("Claim classification cannot downgrade linked evidence privacy")
        if self.review is not None:
            if (
                self.review.revision != self.revision
                or self.review.content_digest != self.content_digest
            ):
                raise ValueError("Claim review does not bind the exact revision/content")
            if self.asserted_at is not None and self.review.reviewed_at < self.asserted_at:
                raise ValueError("Claim review precedes the assertion")
            if self.status != "reviewed_supported" and self.review.decision == "accepted":
                raise ValueError("An accepted current review requires reviewed-supported status")
        if self.status == "reviewed_supported" and (
            self.review is None or self.review.decision != "accepted" or not self.evidence_refs
        ):
            raise ValueError(
                "Reviewed-supported claims require explicit review and scoped evidence"
            )
        return self


def evidence_ref(evidence: EvidenceRecord) -> EvidenceRef:
    checked = EvidenceRecord.model_validate(evidence)
    return EvidenceRef(
        workspace_id=checked.workspace_id,
        classification=checked.classification,
        profile_id=checked.profile_id,
        evidence_id=checked.id,
        revision=checked.revision,
        content_digest=checked.snapshot_digest,
    )


def claim_ref(claim: Claim) -> ClaimRef:
    checked = Claim.model_validate(claim)
    return ClaimRef(
        workspace_id=checked.workspace_id,
        classification=checked.classification,
        profile_id=checked.profile_id,
        claim_id=checked.id,
        revision=checked.revision,
        content_digest=checked.snapshot_digest,
    )


class Profile(Contract):
    id: ProfileId
    workspace_id: WorkspaceId
    revision: Revision
    classification: Classification
    name: Label
    claims: Annotated[tuple[Claim, ...], Field(max_length=128)] = ()
    evidence: Annotated[tuple[EvidenceRecord, ...], Field(max_length=256)] = ()

    @property
    def content_digest(self) -> str:
        return content_digest(self.model_dump(mode="json"))

    @model_validator(mode="after")
    def scoped_relationships(self) -> Self:
        claims = {claim.id.root: claim for claim in self.claims}
        evidence = {record.id.root: record for record in self.evidence}
        if len(claims) != len(self.claims) or len(evidence) != len(self.evidence):
            raise ValueError("Profile record identities must be unique")
        items: tuple[Claim | EvidenceRecord, ...] = (*self.claims, *self.evidence)
        for item in items:
            if item.workspace_id != self.workspace_id or item.profile_id != self.id:
                raise ValueError("Profile contains a record belonging to another owner/profile")
            if not classification_allows(self.classification, item.classification):
                raise ValueError(
                    "Profile classification cannot mix synthetic/real or downgrade privacy"
                )
        for claim in self.claims:
            sources: list[EvidenceRecord] = []
            for ref in claim.evidence_refs:
                record = evidence.get(ref.evidence_id.root)
                if record is None or ref != evidence_ref(record):
                    raise ValueError(
                        "Evidence reference is absent, stale, edited or belongs elsewhere"
                    )
                if not _same_scope(claim.assertion, record.assertion):
                    raise ValueError("Evidence references must cover the assertion subject/unit")
                if not classification_allows(claim.classification, record.classification):
                    raise ValueError(
                        "Claim classification cannot downgrade linked evidence privacy"
                    )
                sources.append(record)
            # Contrary reviewed facts belong to the whole scoped profile. A
            # proposal cannot hide them by selecting only favorable references.
            contrary = any(
                record.relation == "contradicts"
                and record._qualifies_review
                and _same_scope(claim.assertion, record.assertion)
                for record in self.evidence
            )
            if contrary and claim.status not in ("contradicted", "withdrawn"):
                raise ValueError("Reviewed contrary evidence must remain an explicit conflict")
            if claim.status == "contradicted" and not contrary:
                raise ValueError("Contradicted claims require current reviewed contrary evidence")
            qualifying = [
                record
                for record in sources
                if record.qualifies_support and record.assertion.value >= claim.assertion.value
            ]
            if claim.status == "reviewed_supported":
                if contrary or not qualifying:
                    raise ValueError(
                        "Reviewed-supported claim lacks sufficient current reviewed support"
                    )
                assert claim.review is not None  # Enforced by Claim validation.
                for record in qualifying:
                    assert record.review is not None
                    if claim.review.reviewed_at < record.review.reviewed_at:
                        raise ValueError("Claim review precedes supporting source review")
        return self


def supports_assertion(profile: Profile, assertion: Assertion, refs: tuple[ClaimRef, ...]) -> bool:
    """Check structured units only; free prose is never certified by this predicate."""
    if type(refs) is not tuple or len(refs) > 128:
        return False
    try:
        checked = Profile.model_validate(profile)
        requested = Assertion.model_validate(assertion)
        claims = {claim.id.root: claim for claim in checked.claims}
        seen: set[str] = set()
        selected: list[Claim] = []
        for reference in refs:
            ref = ClaimRef.model_validate(reference)
            claim = claims.get(ref.claim_id.root)
            if claim is None or ref != claim_ref(claim) or ref.claim_id.root in seen:
                return False
            seen.add(ref.claim_id.root)
            selected.append(claim)
    except (ValidationError, ValueError):
        return False
    return any(
        claim.status == "reviewed_supported"
        and _same_scope(claim.assertion, requested)
        and claim.assertion.value >= requested.value
        for claim in selected
    )
