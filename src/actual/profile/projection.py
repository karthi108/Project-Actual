"""Deterministic candidate support views; declarations remain declarations.

The internal projection admits the current synthetic graph once. Its groups are
the only candidate facts required by matching. The public view carries stable
references and explicit review distinctions, not a verification certificate.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Annotated, Any, Literal, Self

from pydantic import BaseModel, Field, TypeAdapter, model_validator

from actual.core.primitives import (
    ActorId,
    ClaimId,
    Contract,
    Digest,
    EvidenceId,
    Instant,
    ProfileId,
    Revision,
    Symbol,
    WorkspaceId,
)
from actual.core.references import ClaimRef, EvidenceRef
from actual.core.workflow import ContentReview
from actual.profile.contracts import (
    Assertion,
    AssertionKind,
    AssertionUnit,
    Claim,
    ClaimStatus,
    EvidenceRecord,
    EvidenceReview,
    Profile,
    claim_ref,
    evidence_ref,
)
from actual.profile.experience import ExperienceContext

type AssertionScope = tuple[AssertionKind, str, AssertionUnit]
type ProfileSupportState = Literal["supported", "unverified", "conflict", "unknown"]
_INSTANT: TypeAdapter[datetime] = TypeAdapter(Instant)


def _scope(assertion: Assertion) -> AssertionScope:
    return assertion.kind, assertion.subject, assertion.unit


def admit_profile(profile: Profile) -> Profile:
    """Reject foreign/extra model nodes before serializers can drop their fields."""
    allowed = {
        Profile,
        Claim,
        EvidenceRecord,
        Assertion,
        EvidenceReview,
        ExperienceContext,
        ContentReview,
        WorkspaceId,
        ProfileId,
        ActorId,
        ClaimId,
        EvidenceId,
        EvidenceRef,
    }

    def visit(value: Any) -> None:
        if isinstance(value, BaseModel):
            if (
                type(value) not in allowed
                or set(value.__dict__) - set(type(value).model_fields)
                or value.__pydantic_extra__ is not None
            ):
                raise ValueError("Profile graph contains an unsupported record")
            for child in value.__dict__.values():
                visit(child)
        elif isinstance(value, (tuple, list)):
            for child in value:
                visit(child)

    if type(profile) is not Profile:
        raise ValueError("An exact current synthetic Profile is required")
    visit(profile)
    checked = Profile.model_validate(profile)
    if checked.classification != "synthetic":
        raise ValueError("Profile projection remains synthetic-development only")
    return checked


@dataclass(frozen=True, kw_only=True)
class EvidenceGroup:
    scope: AssertionScope
    claims: tuple[Claim, ...]
    evidence: tuple[EvidenceRecord, ...]
    reviewed_claims: tuple[Claim, ...]
    contrary_evidence: tuple[EvidenceRecord, ...]


@dataclass(frozen=True, kw_only=True)
class EvidenceProjection:
    workspace_id: WorkspaceId
    profile_id: ProfileId
    profile_revision: int
    profile_digest: str
    classification: Literal["synthetic"]
    groups: tuple[EvidenceGroup, ...]


def project_evidence(profile: Profile, *, as_of: datetime | None = None) -> EvidenceProjection:
    """Group current scope without deriving levels, dates or accumulated duration."""
    checked = admit_profile(profile)
    if as_of is not None:
        instant = _INSTANT.validate_python(as_of, strict=True)
        for source in checked.evidence:
            if source.collected_at > instant or (
                source.review is not None and source.review.reviewed_at > instant
            ):
                raise ValueError("Profile projection cannot contain future source/review facts")
        for claim in checked.claims:
            if (claim.asserted_at is not None and claim.asserted_at > instant) or (
                claim.review is not None and claim.review.reviewed_at > instant
            ):
                raise ValueError("Profile projection cannot contain future claim/review facts")
    items: tuple[Claim | EvidenceRecord, ...] = (*checked.claims, *checked.evidence)
    scopes = sorted({_scope(item.assertion) for item in items})
    groups: list[EvidenceGroup] = []
    for scope in scopes:
        claims = tuple(
            sorted(
                (item for item in checked.claims if _scope(item.assertion) == scope),
                key=lambda item: item.id.root,
            )
        )
        evidence = tuple(
            sorted(
                (item for item in checked.evidence if _scope(item.assertion) == scope),
                key=lambda item: item.id.root,
            )
        )
        groups.append(
            EvidenceGroup(
                scope=scope,
                claims=claims,
                evidence=evidence,
                reviewed_claims=tuple(
                    claim for claim in claims if claim.status == "reviewed_supported"
                ),
                contrary_evidence=tuple(
                    record for record in evidence if record.qualifies_contradiction
                ),
            )
        )
    return EvidenceProjection(
        workspace_id=checked.workspace_id,
        profile_id=checked.id,
        profile_revision=checked.revision,
        profile_digest=checked.content_digest,
        classification="synthetic",
        groups=tuple(groups),
    )


class ClaimDeclaration(Contract):
    """A source-attributed structured declaration, not certified prose."""

    assertion: Assertion
    claim_ref: ClaimRef
    status: ClaimStatus
    origin: Literal["user_report", "ai_proposal", "imported_document", "synthetic_fixture"]


class ProfileFactView(Contract):
    kind: AssertionKind
    subject: Symbol
    unit: AssertionUnit
    state: ProfileSupportState
    declarations: Annotated[tuple[ClaimDeclaration, ...], Field(max_length=128)]
    supported_value: Annotated[int, Field(strict=True, ge=0, le=600)] | None
    reviewed_source_value: Annotated[int, Field(strict=True, ge=0, le=600)] | None
    eligible_claim_refs: Annotated[tuple[ClaimRef, ...], Field(max_length=128)]
    eligible_evidence_refs: Annotated[tuple[EvidenceRef, ...], Field(max_length=256)]
    reviewed_source_refs: Annotated[tuple[EvidenceRef, ...], Field(max_length=256)]
    unreviewed_evidence_refs: Annotated[tuple[EvidenceRef, ...], Field(max_length=256)]
    withdrawn_claim_refs: Annotated[tuple[ClaimRef, ...], Field(max_length=128)]
    withdrawn_evidence_refs: Annotated[tuple[EvidenceRef, ...], Field(max_length=256)]
    contrary_evidence_refs: Annotated[tuple[EvidenceRef, ...], Field(max_length=256)]
    contextual_evidence_refs: Annotated[tuple[EvidenceRef, ...], Field(max_length=256)] = ()
    declaration_exceeds_support: Annotated[bool, Field(strict=True)]

    @model_validator(mode="after")
    def scoped_structure(self) -> Self:
        # Reuse accepted kind/unit/value/subject bounds without inventing a value.
        for value in (self.supported_value, self.reviewed_source_value, 0):
            if value is not None:
                Assertion(kind=self.kind, subject=self.subject, unit=self.unit, value=value)
        scope = self.kind, self.subject, self.unit
        if any(_scope(item.assertion) != scope for item in self.declarations):
            raise ValueError("Profile row declarations must preserve assertion scope")
        if (self.state == "supported") != (self.supported_value is not None):
            raise ValueError("Only a supported profile row exposes eligible support")
        if self.state == "supported" and (
            not self.eligible_claim_refs
            or not self.eligible_evidence_refs
            or self.contrary_evidence_refs
        ):
            raise ValueError("Profile support requires current claim/source references")
        if (self.state == "conflict") != bool(self.contrary_evidence_refs):
            raise ValueError("Profile conflict requires explicit current contrary evidence")
        if self.state != "supported" and (self.eligible_claim_refs or self.eligible_evidence_refs):
            raise ValueError("Uncertain profile states cannot expose eligible support")
        if (self.reviewed_source_value is None) != (not self.reviewed_source_refs):
            raise ValueError("Reviewed source values retain their source references")
        declarations = {item.claim_ref.claim_id: item for item in self.declarations}
        for ref in self.eligible_claim_refs:
            declaration = declarations.get(ref.claim_id)
            if (
                declaration is None
                or declaration.claim_ref != ref
                or declaration.status != "reviewed_supported"
                or declaration.assertion.value != self.supported_value
            ):
                raise ValueError("Eligible profile facts require exact reviewed claim declarations")
        if set(self.contextual_evidence_refs) & set(self.eligible_evidence_refs):
            raise ValueError("Contextual experience cannot become eligible generic tenure")
        expected_discrepancy = self.reviewed_source_value is not None and any(
            item.status not in ("withdrawn", "contradicted")
            and item.assertion.value > self.reviewed_source_value
            for item in self.declarations
        )
        if self.declaration_exceeds_support != expected_discrepancy:
            raise ValueError("Profile declaration discrepancy must preserve reviewed support")
        collections: tuple[tuple[ClaimRef | EvidenceRef, ...], ...] = (
            tuple(item.claim_ref for item in self.declarations),
            self.eligible_claim_refs,
            self.eligible_evidence_refs,
            self.reviewed_source_refs,
            self.unreviewed_evidence_refs,
            self.withdrawn_claim_refs,
            self.withdrawn_evidence_refs,
            self.contrary_evidence_refs,
            self.contextual_evidence_refs,
        )
        for refs in collections:
            ids = [
                ref.claim_id.root if isinstance(ref, ClaimRef) else ref.evidence_id.root
                for ref in refs
            ]
            if ids != sorted(set(ids)):
                raise ValueError("Profile references require unique deterministic ordering")
        return self


class ExperienceEvidenceView(Contract):
    """Explicit context is bound to its source review, never a tenure total."""

    evidence_ref: EvidenceRef
    assertion: Assertion
    relation: Literal["supports", "contradicts"]
    context: ExperienceContext
    source_kind: Literal[
        "user_report", "project_artifact", "imported_document", "ai_proposal", "synthetic_fixture"
    ]
    status: Literal["active", "withdrawn"]
    review_kind: (
        Literal[
            "human_confirmation", "source_review", "independent_verification", "synthetic_review"
        ]
        | None
    )
    qualifies_review: Annotated[bool, Field(strict=True)]

    @model_validator(mode="after")
    def source_review_scope(self) -> Self:
        if self.assertion.kind != "experience":
            raise ValueError("Experience view requires a source-authored duration assertion")
        if self.qualifies_review and (
            self.status != "active"
            or self.review_kind in (None, "human_confirmation")
            or self.source_kind in ("user_report", "ai_proposal")
            and self.review_kind != "independent_verification"
        ):
            raise ValueError("Experience view cannot promote a nonqualifying source review")
        return self


class EvidenceBackedProfileView(Contract):
    """Synthetic support snapshot. References do not authenticate real-world facts."""

    workspace_id: WorkspaceId
    profile_id: ProfileId
    profile_revision: Revision
    profile_digest: Digest
    classification: Literal["synthetic"]
    snapshot_as_of: Instant
    rows: Annotated[tuple[ProfileFactView, ...], Field(max_length=384)]
    experience: Annotated[tuple[ExperienceEvidenceView, ...], Field(max_length=256)]

    @model_validator(mode="after")
    def owned_order(self) -> Self:
        scopes = [(row.kind, row.subject, row.unit) for row in self.rows]
        if scopes != sorted(set(scopes)):
            raise ValueError("Profile projection scopes require unique deterministic ordering")
        refs: list[ClaimRef | EvidenceRef] = []
        for row in self.rows:
            refs.extend(item.claim_ref for item in row.declarations)
            refs.extend(row.eligible_claim_refs)
            refs.extend(row.eligible_evidence_refs)
            refs.extend(row.reviewed_source_refs)
            refs.extend(row.unreviewed_evidence_refs)
            refs.extend(row.withdrawn_claim_refs)
            refs.extend(row.withdrawn_evidence_refs)
            refs.extend(row.contrary_evidence_refs)
            refs.extend(row.contextual_evidence_refs)
        refs.extend(item.evidence_ref for item in self.experience)
        if any(
            ref.workspace_id != self.workspace_id
            or ref.profile_id != self.profile_id
            or ref.classification != self.classification
            for ref in refs
        ):
            raise ValueError("Profile view references cannot change owner or classification")
        ids = [item.evidence_ref.evidence_id.root for item in self.experience]
        if ids != sorted(set(ids)):
            raise ValueError("Experience contexts require unique deterministic source ordering")
        if any(
            instant is not None and instant > self.snapshot_as_of
            for item in self.experience
            for instant in (item.context.started_at, item.context.ended_at)
        ):
            raise ValueError("Experience view cannot expose future activity instants")
        return self


def _public_row(group: EvidenceGroup) -> ProfileFactView:
    sources = {record.id: record for record in group.evidence}
    reviewed_sources = tuple(
        record
        for record in group.evidence
        if record.qualifies_support and record.experience_context is None
    )
    eligible_claims = tuple(
        claim
        for claim in group.reviewed_claims
        if any(
            sources[ref.evidence_id].qualifies_support
            and sources[ref.evidence_id].experience_context is None
            and sources[ref.evidence_id].assertion.value >= claim.assertion.value
            for ref in claim.evidence_refs
        )
    )
    contrary = bool(group.contrary_evidence)
    value = (
        max(claim.assertion.value for claim in eligible_claims)
        if eligible_claims and not contrary
        else None
    )
    selected = tuple(claim for claim in eligible_claims if claim.assertion.value == value)
    eligible_sources = {
        ref.evidence_id.root: sources[ref.evidence_id]
        for claim in selected
        for ref in claim.evidence_refs
        if sources[ref.evidence_id].qualifies_support
        and sources[ref.evidence_id].experience_context is None
        and value is not None
        and sources[ref.evidence_id].assertion.value >= value
    }
    reviewed_value = (
        max(record.assertion.value for record in reviewed_sources) if reviewed_sources else None
    )
    state: ProfileSupportState = (
        "conflict"
        if contrary
        else "supported"
        if value is not None
        else "unverified"
        if any(claim.status != "withdrawn" for claim in group.claims)
        or any(record.status == "active" for record in group.evidence)
        else "unknown"
    )
    return ProfileFactView(
        kind=group.scope[0],
        subject=group.scope[1],
        unit=group.scope[2],
        state=state,
        declarations=tuple(
            ClaimDeclaration(
                assertion=claim.assertion,
                claim_ref=claim_ref(claim),
                status=claim.status,
                origin=claim.origin,
            )
            for claim in group.claims
        ),
        supported_value=value,
        reviewed_source_value=reviewed_value,
        eligible_claim_refs=tuple(claim_ref(claim) for claim in selected),
        eligible_evidence_refs=tuple(
            evidence_ref(eligible_sources[key]) for key in sorted(eligible_sources)
        ),
        reviewed_source_refs=tuple(evidence_ref(record) for record in reviewed_sources),
        unreviewed_evidence_refs=tuple(
            evidence_ref(record)
            for record in group.evidence
            if record.status == "active" and not record._qualifies_review
        ),
        withdrawn_claim_refs=tuple(
            claim_ref(claim) for claim in group.claims if claim.status == "withdrawn"
        ),
        withdrawn_evidence_refs=tuple(
            evidence_ref(record) for record in group.evidence if record.status == "withdrawn"
        ),
        contrary_evidence_refs=tuple(evidence_ref(record) for record in group.contrary_evidence),
        contextual_evidence_refs=tuple(
            evidence_ref(record)
            for record in group.evidence
            if record.experience_context is not None
        ),
        declaration_exceeds_support=reviewed_value is not None
        and any(
            claim.status not in ("withdrawn", "contradicted")
            and claim.assertion.value > reviewed_value
            for claim in group.claims
        ),
    )


def evidence_backed_profile(profile: Profile, *, as_of: datetime) -> EvidenceBackedProfileView:
    """Derive a source-bound view. Review labels remain explicit synthetic provenance."""
    if as_of is None:
        raise ValueError("A profile view requires an explicit snapshot instant")
    projection = project_evidence(profile, as_of=as_of)
    context_sources = sorted(
        (
            record
            for group in projection.groups
            for record in group.evidence
            if record.experience_context is not None
        ),
        key=lambda record: record.id.root,
    )
    experience: list[ExperienceEvidenceView] = []
    for record in context_sources:
        assert record.experience_context is not None
        experience.append(
            ExperienceEvidenceView(
                evidence_ref=evidence_ref(record),
                assertion=record.assertion,
                relation=record.relation,
                context=record.experience_context,
                source_kind=record.source_kind,
                status=record.status,
                review_kind=record.review.kind if record.review is not None else None,
                qualifies_review=record._qualifies_review,
            )
        )
    return EvidenceBackedProfileView(
        workspace_id=projection.workspace_id,
        profile_id=projection.profile_id,
        profile_revision=projection.profile_revision,
        profile_digest=projection.profile_digest,
        classification="synthetic",
        snapshot_as_of=as_of,
        rows=tuple(_public_row(group) for group in projection.groups),
        experience=tuple(experience),
    )


def validate_profile_view(
    profile: Profile, view: EvidenceBackedProfileView
) -> EvidenceBackedProfileView:
    """References and a valid schema alone cannot establish current support."""
    if type(view) is not EvidenceBackedProfileView:
        raise ValueError("An exact evidence-backed profile view is required")
    checked = EvidenceBackedProfileView.model_validate(view)
    if checked != evidence_backed_profile(profile, as_of=checked.snapshot_as_of):
        raise ValueError("Profile view does not match current source-bound support")
    return checked
