"""Deterministic current scoped evidence comparisons, never semantic inference."""

import json
from typing import Any

from pydantic import BaseModel

from actual.career.assessments import (
    AssessmentReason,
    FitStatus,
    JobFitAssessment,
    RequirementAssessment,
    RequirementLike,
    assessment_identity,
)
from actual.career.jobs import Job
from actual.career.requirements import InterpretedRequirement, RequirementConstraints
from actual.core.primitives import (
    ActorId,
    ClaimId,
    EvidenceId,
    ProfileId,
    WorkspaceId,
)
from actual.core.workflow import ContentReview
from actual.job_intelligence.errors import IntelligenceCode, IntelligenceFailure
from actual.job_intelligence.normalize import checked_job, normalize_requirement
from actual.profile.contracts import (
    Assertion,
    Claim,
    EvidenceRecord,
    EvidenceReview,
    Profile,
    claim_ref,
    evidence_ref,
)

MATCHING_VERSION = "career-evidence-matching-v2"


def checked_profile(profile: Profile) -> Profile:
    allowed = {
        Profile,
        Claim,
        EvidenceRecord,
        Assertion,
        EvidenceReview,
        ContentReview,
        WorkspaceId,
        ProfileId,
        ActorId,
        ClaimId,
        EvidenceId,
    }
    # Exact graph admission catches data that a serializer could otherwise drop.
    from actual.core.references import EvidenceRef

    allowed.add(EvidenceRef)

    def visit(value: Any) -> None:
        if isinstance(value, BaseModel):
            if (
                type(value) not in allowed
                or set(value.__dict__) - set(type(value).model_fields)
                or value.__pydantic_extra__ is not None
            ):
                raise IntelligenceFailure(IntelligenceCode.INPUT_REJECTED)
            for child in value.__dict__.values():
                visit(child)
        elif isinstance(value, (tuple, list)):
            for child in value:
                visit(child)

    try:
        if type(profile) is not Profile:
            raise IntelligenceFailure(IntelligenceCode.INPUT_REJECTED)
        visit(profile)
        result = Profile.model_validate(profile)
        if result.classification != "synthetic":
            raise IntelligenceFailure(IntelligenceCode.INPUT_REJECTED)
        return result
    except IntelligenceFailure:
        raise
    except Exception:
        raise IntelligenceFailure(IntelligenceCode.INPUT_REJECTED) from None


def _scope(left: Assertion, right: Assertion) -> bool:
    return (left.kind, left.subject, left.unit) == (right.kind, right.subject, right.unit)


def _explanation(reason: AssessmentReason, requirement: RequirementLike, value: int | None) -> str:
    if requirement.resolution == "abstained":
        return "Requirement meaning is unresolved; candidate support is not assessed."
    assertion = requirement.assertion
    assert assertion is not None
    subject, needed = assertion.subject, assertion.value
    unit = assertion.unit
    if reason == "reviewed_support":
        return f"Reviewed {subject} support {value} {unit} covers the stated minimum {needed}."
    if reason == "reviewed_skill_shortfall":
        return f"Reviewed {subject} skill level {value} is below the required level {needed}."
    if reason == "reviewed_threshold_shortfall":
        return f"Reviewed {subject} value {value} {unit} falls below the stated minimum {needed}."
    if reason == "reviewed_no_support":
        return f"Reviewed {subject} evidence explicitly records no scoped support."
    if reason == "conflicting_evidence":
        return f"Current reviewed {subject} evidence conflicts; resolve it before acceptance."
    return (
        f"Current reviewed support for {subject} is missing or insufficient; "
        "declarations remain unverified."
    )


def _match(profile: Profile, requirement: RequirementLike) -> RequirementAssessment:
    if requirement.resolution == "abstained":
        return RequirementAssessment(
            requirement=requirement,
            status="unknown",
            reason="unresolved_requirement",
            explanation=_explanation("unresolved_requirement", requirement, None),
        )
    assertion = requirement.assertion
    assert assertion is not None
    claims = sorted(
        (claim for claim in profile.claims if _scope(claim.assertion, assertion)),
        key=lambda claim: claim.id.root,
    )
    evidence = {record.id: record for record in profile.evidence}
    contrary = [
        record
        for record in profile.evidence
        if _scope(record.assertion, assertion)
        and record.relation == "contradicts"
        and record._qualifies_review
    ]
    value: int | None = None
    declared = False
    selected_claims = claims
    selected_evidence = [
        evidence[ref.evidence_id] for claim in claims for ref in claim.evidence_refs
    ]
    status: FitStatus
    reason: AssessmentReason
    if contrary or any(claim.status == "contradicted" for claim in claims):
        status, reason = "conflict", "conflicting_evidence"
        selected_evidence.extend(contrary)
    else:
        reviewed = [claim for claim in claims if claim.status == "reviewed_supported"]
        if reviewed:
            value = max(claim.assertion.value for claim in reviewed)
            selected_claims = [claim for claim in reviewed if claim.assertion.value == value]
            selected_evidence = [
                evidence[ref.evidence_id]
                for claim in selected_claims
                for ref in claim.evidence_refs
                if evidence[ref.evidence_id].qualifies_support
                and evidence[ref.evidence_id].assertion.value >= value
            ]
            if (
                value >= assertion.value
                and requirement.constraints.experience_scope == "legacy_backend"
            ):
                # The accepted scalar cannot establish a backend category. Keep
                # the authored lower-duration gap, but never infer positive scope
                # from generic months or the prose accompanying a reviewed source.
                status, reason = "unknown", "unreviewed_or_missing"
                value = None
                selected_claims = []
                selected_evidence = []
            elif value >= assertion.value:
                status, reason = "supported", "reviewed_support"
            elif assertion.kind != "skill":
                status, reason = "gap", "reviewed_threshold_shortfall"
            elif value > 0:
                status, reason = "partial", "reviewed_skill_shortfall"
            else:
                status, reason = "gap", "reviewed_no_support"
        else:
            status, reason = "unknown", "unreviewed_or_missing"
            declared = any(
                claim.status in ("self_reported", "candidate_support", "withdrawn")
                and claim.assertion.value < assertion.value
                for claim in claims
            )
    unique_evidence = {record.id.root: record for record in selected_evidence}
    return RequirementAssessment(
        requirement=requirement,
        status=status,
        claim_refs=tuple(claim_ref(claim) for claim in selected_claims),
        evidence_refs=tuple(evidence_ref(unique_evidence[key]) for key in sorted(unique_evidence)),
        observed_value=value,
        declared_shortfall=declared,
        reason=reason,
        explanation=_explanation(reason, requirement, value),
    )


def match_requirements(
    job: Job, profile: Profile, requirements: tuple[RequirementLike, ...]
) -> JobFitAssessment:
    """Resolve every dependency against current inputs; reject stale or forged data."""
    checked_source = checked_job(job)
    checked_candidate = checked_profile(profile)
    if (
        checked_source.workspace_id != checked_candidate.workspace_id
        or type(requirements) is not tuple
        or len(requirements) > 8
    ):
        raise IntelligenceFailure(IntelligenceCode.INPUT_REJECTED)
    try:
        checked_requirements: list[RequirementLike] = []
        ids: set[str] = set()
        concepts: set[str] = set()
        spans: set[tuple[int, int]] = set()
        for requirement in requirements:
            if (
                type(requirement) is not InterpretedRequirement
                or set(requirement.__dict__) - set(InterpretedRequirement.model_fields)
                or requirement.__pydantic_extra__ is not None
            ):
                raise IntelligenceFailure(IntelligenceCode.INVALID_REQUIREMENT)
            for child, expected_kind in (
                (requirement.constraints, RequirementConstraints),
                (requirement.assertion, Assertion),
            ):
                if child is not None and (
                    type(child) is not expected_kind
                    or set(child.__dict__) - set(expected_kind.model_fields)
                    or child.__pydantic_extra__ is not None
                ):
                    raise IntelligenceFailure(IntelligenceCode.INVALID_REQUIREMENT)
            checked = InterpretedRequirement.model_validate(requirement)
            if (
                checked.workspace_id != checked_source.workspace_id
                or checked.classification != "synthetic"
                or checked.job_id != checked_source.id
                or checked.job_revision != checked_source.revision
                or checked.job_digest != checked_source.content_digest
                or checked.source_end > len(checked_source.text)
                or checked_source.text[checked.source_start : checked.source_end]
                != checked.source_quote
            ):
                raise IntelligenceFailure(IntelligenceCode.INVALID_REQUIREMENT)
            derived = normalize_requirement(
                checked_source,
                quote=checked.source_quote,
                term=checked.term,
                priority=checked.priority,
                method=checked.extraction_method,
            )
            if checked != derived:
                raise IntelligenceFailure(IntelligenceCode.INVALID_REQUIREMENT)
            span = (checked.concept_start, checked.concept_end)
            if (
                checked.id.root in ids
                or span in spans
                or (checked.canonical_concept is not None and checked.canonical_concept in concepts)
            ):
                raise IntelligenceFailure(IntelligenceCode.DUPLICATE_REQUIREMENT)
            ids.add(checked.id.root)
            spans.add(span)
            if checked.canonical_concept is not None:
                concepts.add(checked.canonical_concept)
            checked_requirements.append(checked)
        ordered = sorted(checked_requirements, key=lambda item: (item.concept_start, item.id.root))
        rows = tuple(_match(checked_candidate, requirement) for requirement in ordered)
        payload: dict[str, object] = {
            "schema_version": "actual-core-v1",
            "workspace_id": checked_source.workspace_id.root,
            "classification": "synthetic",
            "job_id": checked_source.id.root,
            "job_revision": checked_source.revision,
            "job_digest": checked_source.content_digest,
            "profile_id": checked_candidate.id.root,
            "profile_revision": checked_candidate.revision,
            "profile_digest": checked_candidate.content_digest,
            "rows": [row.model_dump(mode="json") for row in rows],
            "proposal_only": True,
        }
        return JobFitAssessment.model_validate_json(
            json.dumps({**payload, "id": assessment_identity(payload).root})
        )
    except IntelligenceFailure:
        raise
    except Exception:
        raise IntelligenceFailure(IntelligenceCode.INVALID_ASSESSMENT) from None


def validate_assessment(
    job: Job, profile: Profile, assessment: JobFitAssessment
) -> JobFitAssessment:
    """An assessment's references/schema alone cannot establish current support."""
    try:
        if (
            type(assessment) is not JobFitAssessment
            or set(assessment.__dict__) - set(JobFitAssessment.model_fields)
            or assessment.__pydantic_extra__ is not None
        ):
            raise IntelligenceFailure(IntelligenceCode.INVALID_ASSESSMENT)
        checked = JobFitAssessment.model_validate(assessment)
        current = match_requirements(job, profile, tuple(row.requirement for row in checked.rows))
        if checked != current:
            raise IntelligenceFailure(IntelligenceCode.INVALID_ASSESSMENT)
        return checked
    except IntelligenceFailure:
        raise
    except Exception:
        raise IntelligenceFailure(IntelligenceCode.INVALID_ASSESSMENT) from None
