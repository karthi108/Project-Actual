"""Current reviewed evidence, not vocabulary or model confidence, decides coverage."""

import json
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from actual.career.assessments import JobFitAssessment, assessment_identity
from actual.career.jobs import Job
from actual.core.primitives import (
    ActorId,
    ClaimId,
    CompanyId,
    EvidenceId,
    JobId,
    OpportunityId,
    ProfileId,
    WorkspaceId,
    canonical_bytes,
    load_contract,
)
from actual.core.workflow import ContentReview
from actual.job_intelligence.errors import IntelligenceFailure
from actual.job_intelligence.matching import match_requirements, validate_assessment
from actual.job_intelligence.normalize import normalize_requirement
from actual.profile.contracts import (
    Assertion,
    Claim,
    EvidenceRecord,
    EvidenceReview,
    Profile,
    claim_ref,
    evidence_ref,
)

WORKSPACE = WorkspaceId("workspace_" + "1" * 32)
PROFILE = ProfileId("profile_" + "2" * 32)
ACTOR = ActorId("actor_" + "3" * 32)


def at(day: int) -> datetime:
    return datetime(2026, 1, day, tzinfo=UTC)


def source_job(text: str = "Python at working level is essential.") -> Job:
    return Job(
        id=JobId("job_" + "4" * 32),
        workspace_id=WORKSPACE,
        revision=1,
        classification="synthetic",
        company_id=CompanyId("company_" + "5" * 32),
        opportunity_id=OpportunityId("opportunity_" + "6" * 32),
        title="Synthetic evidence comparison",
        text=text,
        source_reference="synthetic:evidence-comparison",
        posted_at=at(1),
        decision="new",
    )


def candidate(
    value: int = 2,
    *,
    subject: str = "python",
    kind: str = "skill",
    unit: str = "skill_level",
    reviewed: bool = True,
    withdrawn: bool = False,
    contrary: bool = False,
    source_kind: str = "project_artifact",
    review_kind: str = "synthetic_review",
    excerpt: str = "Fabricated structured source for deterministic comparison.",
) -> Profile:
    assertion = Assertion.model_validate(
        {"kind": kind, "subject": subject, "unit": unit, "value": value}
    )
    evidence = EvidenceRecord.model_validate(
        {
            "id": EvidenceId("evidence_" + "7" * 32),
            "workspace_id": WORKSPACE,
            "profile_id": PROFILE,
            "revision": 1,
            "classification": "synthetic",
            "assertion": assertion,
            "relation": "supports",
            "excerpt": excerpt,
            "source_kind": source_kind,
            "source_reference": "synthetic:source:positive",
            "collected_at": at(2),
            "status": "withdrawn" if withdrawn else "active",
        }
    )
    if reviewed:
        evidence = evidence.model_copy(
            update={
                "review": EvidenceReview.model_validate(
                    {
                        "reviewer_id": ACTOR,
                        "kind": review_kind,
                        "method": "Synthetic scoped source review",
                        "reviewed_at": at(3),
                        "content_digest": evidence.content_digest,
                    }
                )
            }
        )
    sources = [evidence]
    if contrary:
        negative = evidence.model_copy(
            update={
                "id": EvidenceId("evidence_" + "8" * 32),
                "relation": "contradicts",
                "review": None,
                "source_reference": "synthetic:source:contrary",
            }
        )
        negative = negative.model_copy(
            update={
                "review": EvidenceReview(
                    reviewer_id=ACTOR,
                    kind="synthetic_review",
                    method="Synthetic contrary source review",
                    reviewed_at=at(3),
                    content_digest=negative.content_digest,
                )
            }
        )
        sources.append(negative)
    claim = Claim.model_validate(
        {
            "id": ClaimId("claim_" + "9" * 32),
            "workspace_id": WORKSPACE,
            "profile_id": PROFILE,
            "revision": 1,
            "classification": "synthetic",
            "assertion": assertion,
            "text": "Fabricated candidate assertion.",
            "origin": "synthetic_fixture",
            "status": "contradicted"
            if contrary
            else "withdrawn"
            if withdrawn
            else "candidate_support",
            "evidence_refs": tuple(evidence_ref(record) for record in sources),
        }
    )
    if reviewed and not contrary and not withdrawn and evidence.qualifies_support:
        review = ContentReview(
            revision=1,
            content_digest=claim.content_digest,
            reviewer_id=ACTOR,
            reviewed_at=at(4),
            method="Synthetic claim scope review",
            decision="accepted",
        )
        claim = claim.model_copy(update={"status": "reviewed_supported", "review": review})
    return Profile(
        id=PROFILE,
        workspace_id=WORKSPACE,
        revision=1,
        classification="synthetic",
        name="Fabricated candidate",
        claims=(claim,),
        evidence=tuple(sources),
    )


def assessed(job: Job, profile: Profile, term: str = "Python") -> JobFitAssessment:
    requirement = normalize_requirement(job, quote=job.text, term=term, priority="essential")
    return match_requirements(job, profile, (requirement,))


def test_supported_decision_resolves_exact_current_provenance() -> None:
    job, profile = source_job(), candidate()
    result = assessed(job, profile)
    row = result.rows[0]
    assert row.status == "supported" and row.observed_value == 2
    assert row.claim_refs == (claim_ref(profile.claims[0]),)
    assert row.evidence_refs == (evidence_ref(profile.evidence[0]),)
    assert result.job_digest == job.content_digest
    assert result.profile_digest == profile.content_digest
    assert result.counts.supported == 1 and result.proposal_only is True
    assert validate_assessment(job, profile, result) == result
    assert load_contract(JobFitAssessment, canonical_bytes(result)) == result
    assert result.id == assessed(job, profile).id


def test_skill_threshold_invariant_over_all_fixture_levels() -> None:
    for minimum, word in ((1, "introductory"), (2, "working"), (3, "strong")):
        job = source_job(f"Python at {word} level is essential.")
        for supported in range(4):
            row = assessed(job, candidate(supported)).rows[0]
            expected = (
                "supported" if supported >= minimum else "gap" if supported == 0 else "partial"
            )
            assert row.status == expected
            assert row.observed_value == supported
            assert row.claim_refs and row.evidence_refs


@pytest.mark.parametrize(
    ("text", "term", "value", "kind", "subject", "unit"),
    [
        ("French B2 is essential.", "French", 2, "language", "french", "cefr_level"),
        (
            "Five years of experience are essential.",
            "experience",
            12,
            "experience",
            "experience",
            "months",
        ),
    ],
)
def test_reviewed_language_and_duration_shortfalls_are_gaps(
    text: str, term: str, value: int, kind: str, subject: str, unit: str
) -> None:
    row = assessed(
        source_job(text), candidate(value, kind=kind, subject=subject, unit=unit), term
    ).rows[0]
    assert row.status == "gap" and row.reason == "reviewed_threshold_shortfall"
    assert not row.declared_shortfall


@pytest.mark.parametrize(
    "changes",
    [
        {"reviewed": False},
        {"withdrawn": True},
        {"review_kind": "human_confirmation"},
        {"source_kind": "user_report", "review_kind": "source_review"},
        {"source_kind": "ai_proposal", "review_kind": "source_review"},
    ],
)
def test_unreviewed_withdrawn_and_nonqualifying_sources_never_satisfy(
    changes: dict[str, object],
) -> None:
    row = assessed(source_job(), candidate(**changes)).rows[0]  # type: ignore[arg-type]
    assert row.status == "unknown" and row.observed_value is None


def test_declared_shortfall_never_becomes_reviewed_language_fact() -> None:
    profile = candidate(2, kind="language", subject="french", unit="cefr_level", reviewed=False)
    row = assessed(source_job("French B2 is essential."), profile, "French").rows[0]
    assert row.status == "unknown" and row.declared_shortfall
    assert row.observed_value is None
    assert "unverified" in row.explanation


def test_withdrawn_shortfall_remains_an_unverified_declaration() -> None:
    row = assessed(source_job(), candidate(1, withdrawn=True)).rows[0]
    assert row.status == "unknown" and row.declared_shortfall
    assert row.observed_value is None


def test_current_contrary_evidence_takes_precedence() -> None:
    row = assessed(source_job(), candidate(3, contrary=True)).rows[0]
    assert row.status == "conflict" and row.observed_value is None
    assert {ref.evidence_id for ref in row.evidence_refs} == {
        EvidenceId("evidence_" + "7" * 32),
        EvidenceId("evidence_" + "8" * 32),
    }


def test_related_technology_and_missing_evidence_remain_unknown() -> None:
    job = source_job("Strong Azure is essential.")
    assert assessed(job, candidate(3, subject="aws"), "Azure").rows[0].status == "unknown"
    empty = Profile(
        id=PROFILE,
        workspace_id=WORKSPACE,
        revision=1,
        classification="synthetic",
        name="Fabricated empty candidate",
    )
    row = assessed(job, empty, "Azure").rows[0]
    assert row.status == "unknown" and not row.claim_refs and not row.evidence_refs


def test_unresolved_requirement_cannot_consume_matching_evidence() -> None:
    row = assessed(source_job("Python development is essential."), candidate()).rows[0]
    assert row.status == "unknown" and row.reason == "unresolved_requirement"
    assert not row.claim_refs and not row.evidence_refs


def test_empty_matrix_has_no_positive_fit_claim() -> None:
    result = match_requirements(source_job(), candidate(), ())
    assert (
        not result.rows and sum(result.counts.model_dump(exclude={"schema_version"}).values()) == 0
    )


def test_reordered_inputs_produce_same_canonical_assessment() -> None:
    text = "Python at working level is essential. Strong Azure is preferred."
    job = source_job(text)
    python = normalize_requirement(
        job, quote="Python at working level is essential.", term="Python", priority="essential"
    )
    azure = normalize_requirement(
        job, quote="Strong Azure is preferred.", term="Azure", priority="preferred"
    )
    first = match_requirements(job, candidate(), (python, azure))
    second = match_requirements(job, candidate(), (azure, python))
    assert canonical_bytes(first) == canonical_bytes(second)
    assert first.id == second.id
    assert first.rows[0].requirement == python


def test_duplicate_normalized_units_fail_instead_of_adding_weight() -> None:
    job = source_job()
    requirement = normalize_requirement(job, quote=job.text, term="Python", priority="essential")
    with pytest.raises(IntelligenceFailure, match="duplicate_requirement"):
        match_requirements(job, candidate(), (requirement, requirement))


def test_distinct_atomic_concepts_can_share_source_context() -> None:
    job = source_job("Python and FastAPI at working level are essential.")
    python = normalize_requirement(job, quote=job.text, term="Python", priority="essential")
    fastapi = normalize_requirement(job, quote=job.text, term="FastAPI", priority="essential")
    result = match_requirements(job, candidate(), (python, fastapi))
    assert [row.requirement.canonical_concept for row in result.rows] == ["python", "fastapi"]
    assert [row.status for row in result.rows] == ["supported", "unknown"]
    assert python.concept_end <= fastapi.concept_start


def test_stale_job_and_profile_references_fail_context_revalidation() -> None:
    job, profile = source_job(), candidate()
    result = assessed(job, profile)
    with pytest.raises(IntelligenceFailure):
        validate_assessment(job.model_copy(update={"revision": 2}), profile, result)
    with pytest.raises(IntelligenceFailure, match="invalid_assessment"):
        validate_assessment(job, candidate(1), result)
    assert assessed(job, candidate(1)).id != result.id


def test_schema_valid_but_stale_reference_is_rejected_by_current_context() -> None:
    job, profile = source_job(), candidate()
    result = assessed(job, profile)
    payload = result.model_dump(mode="json", exclude={"id"})
    payload["rows"][0]["evidence_refs"][0]["revision"] = 2
    forged = JobFitAssessment.model_validate_json(
        json.dumps({**payload, "id": assessment_identity(payload).root})
    )
    with pytest.raises(IntelligenceFailure, match="invalid_assessment"):
        validate_assessment(job, profile, forged)


def test_positive_state_without_provenance_and_identity_edit_fail() -> None:
    result = assessed(source_job(), candidate())
    with pytest.raises(ValidationError):
        result.rows[0].model_copy(update={"evidence_refs": ()})
    with pytest.raises(ValidationError):
        result.model_copy(update={"profile_revision": 2})
    with pytest.raises(ValidationError):
        result.model_copy(update={"proposal_only": 1})


@pytest.mark.parametrize(
    ("text", "term", "kind", "subject", "unit", "value", "invalid"),
    [
        ("Python at working level is essential.", "Python", "skill", "python", "skill_level", 3, 4),
        ("French B2 is essential.", "French", "language", "french", "cefr_level", 6, 7),
        (
            "Five years of experience are essential.",
            "experience",
            "experience",
            "experience",
            "months",
            600,
            601,
        ),
    ],
)
def test_observed_value_cannot_exceed_its_scoped_unit(
    text: str, term: str, kind: str, subject: str, unit: str, value: int, invalid: int
) -> None:
    result = assessed(
        source_job(text), candidate(value, kind=kind, subject=subject, unit=unit), term
    )
    assert result.rows[0].status == "supported"
    with pytest.raises(ValidationError):
        result.rows[0].model_copy(update={"observed_value": invalid})


def test_forged_nested_input_and_cross_workspace_fail_closed() -> None:
    profile = candidate()
    profile.claims[0].assertion.__dict__["oracle"] = "hidden answer"
    with pytest.raises(IntelligenceFailure, match="input_rejected"):
        assessed(source_job(), profile)
    foreign = Profile(
        id=PROFILE,
        workspace_id=WorkspaceId("workspace_" + "a" * 32),
        revision=1,
        classification="synthetic",
        name="Fabricated foreign profile",
    )
    with pytest.raises(IntelligenceFailure, match="input_rejected"):
        assessed(source_job(), foreign)


def test_edited_explanation_cannot_add_an_unbacked_fact() -> None:
    job, profile = source_job(), candidate()
    result = assessed(job, profile)
    payload = result.model_dump(mode="json", exclude={"id"})
    payload["rows"][0]["explanation"] = "The candidate also knows Kubernetes."
    forged = JobFitAssessment.model_validate_json(
        json.dumps({**payload, "id": assessment_identity(payload).root})
    )
    with pytest.raises(IntelligenceFailure, match="invalid_assessment"):
        validate_assessment(job, profile, forged)


@pytest.mark.parametrize(
    ("value", "source_kind", "excerpt"),
    [
        (60, "imported_document", "Synthetic reviewed duration with unspecified work category."),
        (72, "project_artifact", "Synthetic source: six years of personal project work only."),
        (600, "imported_document", "Synthetic source: fifty years of internship work only."),
    ],
)
def test_generic_reviewed_months_never_establish_legacy_backend_support(
    value: int, source_kind: str, excerpt: str
) -> None:
    profile = candidate(
        value,
        kind="experience",
        subject="experience",
        unit="months",
        source_kind=source_kind,
        excerpt=excerpt,
    )
    before = canonical_bytes(profile)
    backend_job = source_job("Five years of backend experience are essential.")
    backend = assessed(backend_job, profile, "backend experience")
    row = backend.rows[0]
    assert row.requirement.constraints.experience_scope == "legacy_backend"
    assert row.status == "unknown" and row.reason == "unreviewed_or_missing"
    assert row.observed_value is None and not row.declared_shortfall
    assert not row.claim_refs and not row.evidence_refs
    assert validate_assessment(backend_job, profile, backend) == backend
    generic_job = source_job("Five years of experience are essential.")
    generic = assessed(generic_job, profile, "experience").rows[0]
    assert generic.requirement.constraints.experience_scope == "generic"
    assert generic.status == "supported" and generic.observed_value == value
    assert generic.claim_refs == (claim_ref(profile.claims[0]),)
    assert generic.evidence_refs == (evidence_ref(profile.evidence[0]),)
    with pytest.raises(ValidationError, match="positive backend scope"):
        row.model_copy(
            update={
                "status": "supported",
                "reason": "reviewed_support",
                "observed_value": value,
                "claim_refs": generic.claim_refs,
                "evidence_refs": generic.evidence_refs,
            }
        )
    assert canonical_bytes(profile) == before


def test_accepted_legacy_backend_lower_duration_retains_authored_gap() -> None:
    profile = candidate(
        12,
        kind="experience",
        subject="experience",
        unit="months",
        source_kind="imported_document",
        excerpt="Synthetic source: Twelve documented months of backend work.",
    )
    row = assessed(
        source_job("Five years of backend experience are essential."),
        profile,
        "backend experience",
    ).rows[0]
    assert row.status == "gap" and row.reason == "reviewed_threshold_shortfall"
    assert row.observed_value == 12
    assert row.claim_refs == (claim_ref(profile.claims[0]),)
    assert row.evidence_refs == (evidence_ref(profile.evidence[0]),)
