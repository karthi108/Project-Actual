"""Transient CV coverage of explicitly selected source units, never a hiring score."""

from typing import Annotated

from pydantic import Field

from actual.application.preparation_commands import CompareCVs
from actual.career.assessments import JobFitAssessment
from actual.career.snapshot import CareerSnapshot
from actual.core.primitives import Contract, CVId
from actual.job_intelligence.matching import match_requirements
from actual.job_intelligence.normalize import normalize_requirement
from actual.profile.contracts import Claim, claim_ref, supports_assertion
from actual.profile.projection import project_evidence


class CVOption(Contract):
    cv_id: CVId
    covered_requirements: tuple[str, ...]
    covered_essential: int
    covered_preferred: int


class CVComparison(Contract):
    generation: Annotated[int, Field(strict=True, ge=1)]
    selection_basis: str = "Human-selected source quotations; deterministic normalization."
    assessment: JobFitAssessment
    options: tuple[CVOption, ...]
    suggested_cv_ids: tuple[CVId, ...]
    unresolved_claims: tuple[Claim, ...]
    limitation: str = (
        "Coverage counts only supported selected units; no overall fit score. "
        "Unverified user claims are excluded from prepared factual materials. "
        "Synthetic reviews do not verify a real person."
    )


def compare(snapshot: CareerSnapshot, generation: int, command: CompareCVs) -> CVComparison:
    job = next(item for item in snapshot.jobs if item.id == command.job_id)
    requirements = tuple(
        normalize_requirement(
            job, quote=item.quote, term=item.term, priority=item.priority, method="deterministic"
        )
        for item in command.selections
    )
    if len({item.id for item in requirements}) != len(requirements):
        raise ValueError("Repeated source selections")
    assessment = match_requirements(job, snapshot.profile, requirements)
    conflicts = {
        group.scope
        for group in project_evidence(snapshot.profile).groups
        if group.contrary_evidence
    }
    options: list[CVOption] = []
    for cv in snapshot.cvs:
        covered = tuple(
            row
            for row in assessment.rows
            if row.status == "supported"
            and row.requirement.assertion is not None
            and supports_assertion(snapshot.profile, row.requirement.assertion, cv.claim_refs)
        )
        options.append(
            CVOption(
                cv_id=cv.id,
                covered_requirements=tuple(item.requirement.id.root for item in covered),
                covered_essential=sum(item.requirement.priority == "essential" for item in covered),
                covered_preferred=sum(item.requirement.priority == "preferred" for item in covered),
            )
        )
    options.sort(
        key=lambda item: (-item.covered_essential, -item.covered_preferred, item.cv_id.root)
    )
    best = options[0] if options else None
    suggested = tuple(
        item.cv_id
        for item in options
        if best is not None
        and best.covered_requirements
        and (item.covered_essential, item.covered_preferred)
        == (best.covered_essential, best.covered_preferred)
    )
    return CVComparison(
        generation=generation,
        assessment=assessment,
        options=tuple(options),
        suggested_cv_ids=suggested,
        unresolved_claims=tuple(
            claim
            for claim in snapshot.profile.claims
            if (claim.assertion.kind, claim.assertion.subject, claim.assertion.unit) in conflicts
            or not supports_assertion(snapshot.profile, claim.assertion, (claim_ref(claim),))
        ),
    )
