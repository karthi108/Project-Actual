"""Current scoped support, honest declarations, deterministic candidate projections."""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from actual.careerlab_bridge import ImportContext, load_observable
from actual.core.primitives import (
    ActorId,
    ClaimId,
    EvidenceId,
    ProfileId,
    WorkspaceId,
    canonical_bytes,
    load_contract,
)
from actual.core.workflow import ContentReview
from actual.profile.contracts import (
    Assertion,
    Claim,
    EvidenceRecord,
    EvidenceReview,
    Profile,
    evidence_ref,
)
from actual.profile.experience import ExperienceContext
from actual.profile.projection import (
    EvidenceBackedProfileView,
    admit_profile,
    evidence_backed_profile,
    project_evidence,
    validate_profile_view,
)

WORKSPACE = WorkspaceId("workspace_" + "1" * 32)
PROFILE = ProfileId("profile_" + "2" * 32)
ACTOR = ActorId("actor_" + "3" * 32)


def at(day: int) -> datetime:
    return datetime(2026, 1, day, 12, tzinfo=UTC)


def fact(
    value: int = 2, subject: str = "python", kind: str = "skill", unit: str = "skill_level"
) -> Assertion:
    return Assertion.model_validate(
        {"kind": kind, "subject": subject, "unit": unit, "value": value}
    )


def source(
    number: int = 1, assertion: Assertion | None = None, **changes: object
) -> EvidenceRecord:
    return EvidenceRecord.model_validate(
        {
            "id": EvidenceId(f"evidence_{number:032x}"),
            "workspace_id": WORKSPACE,
            "profile_id": PROFILE,
            "revision": 1,
            "classification": "synthetic",
            "assertion": assertion or fact(),
            "relation": "supports",
            "excerpt": "Fabricated structured candidate source.",
            "source_kind": "project_artifact",
            "source_reference": f"synthetic:source:{number}",
            "collected_at": at(10),
            **changes,
        }
    )


def review_source(record: EvidenceRecord, *, kind: str = "synthetic_review") -> EvidenceRecord:
    return record.model_copy(
        update={
            "review": EvidenceReview.model_validate(
                {
                    "reviewer_id": ACTOR,
                    "kind": kind,
                    "method": "Fabricated structured source review",
                    "reviewed_at": at(11),
                    "content_digest": record.content_digest,
                }
            )
        }
    )


def claim(number: int = 1, assertion: Assertion | None = None, **changes: object) -> Claim:
    return Claim.model_validate(
        {
            "id": ClaimId(f"claim_{number:032x}"),
            "workspace_id": WORKSPACE,
            "profile_id": PROFILE,
            "revision": 1,
            "classification": "synthetic",
            "assertion": assertion or fact(),
            "text": "Fabricated structured declaration.",
            "origin": "user_report",
            "asserted_at": at(10),
            "status": "self_reported",
            **changes,
        }
    )


def reviewed_claim(record: EvidenceRecord, number: int = 1) -> Claim:
    declared = claim(number, assertion=record.assertion, evidence_refs=(evidence_ref(record),))
    return declared.model_copy(
        update={
            "status": "reviewed_supported",
            "review": ContentReview(
                revision=1,
                content_digest=declared.content_digest,
                reviewer_id=ACTOR,
                reviewed_at=at(12),
                method="Fabricated assertion scope review",
                decision="accepted",
            ),
        }
    )


def profile(claims: tuple[Claim, ...] = (), evidence: tuple[EvidenceRecord, ...] = ()) -> Profile:
    return Profile(
        id=PROFILE,
        workspace_id=WORKSPACE,
        revision=1,
        classification="synthetic",
        name="Fabricated profile",
        claims=claims,
        evidence=evidence,
    )


def test_current_support_keeps_declarations_and_sources_separate_and_roundtrips() -> None:
    record = review_source(source())
    declared = reviewed_claim(record)
    candidate = profile((declared,), (record,))
    internal = project_evidence(candidate)
    assert internal.profile_digest == candidate.content_digest
    assert internal.groups[0].reviewed_claims == (declared,)
    view = evidence_backed_profile(candidate, as_of=at(20))
    row = view.rows[0]
    assert row.state == "supported" and row.supported_value == 2
    assert row.eligible_evidence_refs == (evidence_ref(record),)
    assert row.declarations[0].origin == "user_report"
    assert row.declarations[0].status == "reviewed_supported"
    assert load_contract(EvidenceBackedProfileView, canonical_bytes(view)) == view
    assert validate_profile_view(candidate, view) == view


@pytest.mark.parametrize("origin", ["user_report", "ai_proposal"])
def test_unverified_declarations_cannot_become_eligible_support(origin: str) -> None:
    record = source(source_kind=origin)
    declared = claim(origin=origin, evidence_refs=(evidence_ref(record),))
    candidate = profile((declared,), (record,))
    row = evidence_backed_profile(candidate, as_of=at(20)).rows[0]
    assert row.state == "unverified" and row.supported_value is None
    assert not row.eligible_claim_refs and not row.eligible_evidence_refs
    assert row.unreviewed_evidence_refs == (evidence_ref(record),)


def test_human_confirmation_and_evidence_without_claim_review_stay_distinct() -> None:
    confirmed = review_source(source(), kind="human_confirmation")
    row = evidence_backed_profile(profile((claim(),), (confirmed,)), as_of=at(20)).rows[0]
    assert row.supported_value is None and row.reviewed_source_value is None
    reviewed = review_source(source())
    row = evidence_backed_profile(profile((claim(),), (reviewed,)), as_of=at(20)).rows[0]
    assert row.supported_value is None and row.reviewed_source_value == 2
    assert row.reviewed_source_refs == (evidence_ref(reviewed),)
    assert not row.eligible_evidence_refs


def test_language_declaration_above_reviewed_support_is_reviewable_not_verified() -> None:
    a2 = fact(2, "french", "language", "cefr_level")
    b2 = fact(4, "french", "language", "cefr_level")
    record = review_source(source(assertion=a2, source_kind="imported_document"))
    candidate = profile((claim(assertion=b2, evidence_refs=(evidence_ref(record),)),), (record,))
    row = evidence_backed_profile(candidate, as_of=at(20)).rows[0]
    assert row.state == "unverified" and row.supported_value is None
    assert row.reviewed_source_value == 2 and row.declaration_exceeds_support
    assert row.declarations[0].assertion.value == 4
    assert not row.contrary_evidence_refs
    assert not row.eligible_claim_refs


def test_explicit_contrary_source_cannot_be_hidden_by_favorable_selection() -> None:
    positive = review_source(source())
    negative = review_source(source(2, relation="contradicts", assertion=fact(1)))
    declared = claim(status="contradicted", evidence_refs=(evidence_ref(positive),))
    candidate = profile((declared,), (positive, negative))
    row = evidence_backed_profile(candidate, as_of=at(20)).rows[0]
    assert row.state == "conflict" and row.supported_value is None
    assert row.contrary_evidence_refs == (evidence_ref(negative),)
    assert not row.eligible_evidence_refs


def test_duplicate_facts_and_reordered_records_do_not_inflate_values() -> None:
    first, second = review_source(source(1)), review_source(source(2))
    claims = (reviewed_claim(first, 1), reviewed_claim(second, 2))
    before = evidence_backed_profile(profile(claims, (first, second)), as_of=at(20))
    after = evidence_backed_profile(profile(claims[::-1], (second, first)), as_of=at(20))
    assert before.rows == after.rows
    assert before.rows[0].supported_value == 2  # No averaging, summation or expertise inflation.
    assert len(before.rows[0].eligible_evidence_refs) == 2
    assert before.profile_digest != after.profile_digest  # Existing exact source ordering remains.
    with pytest.raises(ValidationError):
        profile((claims[0], claims[0]), (first,))
    with pytest.raises(ValidationError):
        profile((claims[0],), (first, first))


def test_contextual_overlapping_experience_never_becomes_generic_tenure() -> None:
    duration = fact(6, "experience", "experience", "months")
    contexts = (
        ExperienceContext(
            context_version="actual-experience-context-v1",
            category="internship",
            started_at=at(1),
            ended_at=at(8),
            ongoing=False,
        ),
        ExperienceContext(
            context_version="actual-experience-context-v1",
            category="personal_project",
            started_at=at(4),
            ongoing=True,
        ),
    )
    records = tuple(
        review_source(source(index, duration, experience_context=metadata))
        for index, metadata in enumerate(contexts, start=1)
    )
    candidate = profile(
        tuple(
            claim(
                i,
                assertion=record.assertion,
                status="candidate_support",
                evidence_refs=(evidence_ref(record),),
            )
            for i, record in enumerate(records, 1)
        ),
        records,
    )
    view = evidence_backed_profile(candidate, as_of=at(20))
    row = view.rows[0]
    assert row.supported_value is None and row.reviewed_source_value is None
    assert not row.eligible_claim_refs and not row.eligible_evidence_refs
    assert len(row.contextual_evidence_refs) == 2
    assert tuple(item.context for item in view.experience) == contexts
    assert tuple(item.assertion.value for item in view.experience) == (6, 6)
    assert all(item.relation == "supports" for item in view.experience)
    assert all(
        item.qualifies_review and item.review_kind == "synthetic_review" for item in view.experience
    )
    assert tuple(item.assertion.value for item in candidate.claims) == (6, 6)


@pytest.mark.parametrize(
    "category",
    [
        "professional_employment",
        "internship",
        "academic",
        "personal_project",
        "open_source",
        "unknown",
    ],
)
def test_scoped_experience_source_cannot_verify_generic_claim_or_future_material(
    category: str,
) -> None:
    record = review_source(
        source(
            assertion=fact(24, "experience", "experience", "months"),
            experience_context=ExperienceContext(
                context_version="actual-experience-context-v1", category=category
            ),
        )
    )
    assert record._qualifies_review and not record.qualifies_support
    with pytest.raises(ValidationError, match="sufficient current reviewed support"):
        profile((reviewed_claim(record),), (record,))


def test_contextual_contrary_source_cannot_refute_generic_experience() -> None:
    duration = fact(12, "experience", "experience", "months")
    scoped = review_source(
        source(
            assertion=duration,
            relation="contradicts",
            experience_context=ExperienceContext(
                context_version="actual-experience-context-v1", category="internship"
            ),
        )
    )
    declared = claim(assertion=duration, evidence_refs=(evidence_ref(scoped),))
    candidate = profile((declared,), (scoped,))
    assert scoped._qualifies_review and not scoped.qualifies_contradiction
    view = evidence_backed_profile(candidate, as_of=at(20))
    assert view.rows[0].state == "unverified"
    assert not view.rows[0].contrary_evidence_refs
    assert view.experience[0].relation == "contradicts"
    assert view.experience[0].qualifies_review
    with pytest.raises(ValidationError, match="current reviewed contrary"):
        profile((declared.model_copy(update={"status": "contradicted"}),), (scoped,))


def test_withdrawn_records_keep_history_without_current_support() -> None:
    record = review_source(source()).model_copy(update={"status": "withdrawn"})
    declared = claim(status="withdrawn", evidence_refs=(evidence_ref(record),))
    row = evidence_backed_profile(profile((declared,), (record,)), as_of=at(20)).rows[0]
    assert row.state == "unknown" and row.supported_value is None
    assert row.withdrawn_evidence_refs == (evidence_ref(record),)
    assert len(row.withdrawn_claim_refs) == 1
    assert not row.reviewed_source_refs


def test_missing_capability_and_missing_level_do_not_create_structured_facts() -> None:
    view = evidence_backed_profile(profile(), as_of=at(20))
    assert view.rows == () and view.experience == ()
    with pytest.raises(ValidationError):
        Assertion.model_validate(
            {"kind": "language", "subject": "french", "unit": "cefr_level", "value": None}
        )


def test_snapshot_instant_rejects_future_facts_without_using_a_system_clock() -> None:
    record = review_source(source())
    declared = reviewed_claim(record)
    candidate = profile((declared,), (record,))
    assert project_evidence(candidate).groups[0].reviewed_claims == (declared,)
    for day in (9, 10, 11):
        with pytest.raises(ValueError, match="future"):
            evidence_backed_profile(candidate, as_of=at(day))
    assert evidence_backed_profile(candidate, as_of=at(12)).rows[0].supported_value == 2


def test_forged_graph_hidden_fields_and_personal_data_fail_admission() -> None:
    candidate = profile((claim(),))
    candidate.claims[0].assertion.__dict__["oracle"] = "forged hidden label"
    with pytest.raises(ValueError, match="unsupported record"):
        admit_profile(candidate)
    real = profile().model_copy(update={"classification": "personal"})
    with pytest.raises(ValueError, match="synthetic"):
        project_evidence(real)


def test_structural_view_validation_does_not_replace_current_source_validation() -> None:
    record = review_source(source())
    candidate = profile((reviewed_claim(record),), (record,))
    view = evidence_backed_profile(candidate, as_of=at(20))
    edited = view.model_copy(update={"profile_digest": "0" * 64})
    with pytest.raises(ValueError, match="current source-bound support"):
        validate_profile_view(candidate, edited)
    stale = candidate.model_copy(update={"revision": 2})
    with pytest.raises(ValueError, match="current source-bound support"):
        validate_profile_view(stale, view)


def test_structural_view_cannot_relabel_unverified_claim_as_eligible_support() -> None:
    record = review_source(source())
    candidate = profile((reviewed_claim(record),), (record,))
    row = evidence_backed_profile(candidate, as_of=at(20)).rows[0]
    unverified = row.declarations[0].model_copy(update={"status": "self_reported"})
    with pytest.raises(ValidationError, match="exact reviewed claim"):
        row.model_copy(update={"declarations": (unverified,)})
    with pytest.raises(ValidationError, match="discrepancy"):
        row.model_copy(update={"declaration_exceeds_support": True})
    with pytest.raises(ValidationError, match="generic tenure"):
        row.model_copy(update={"contextual_evidence_refs": row.eligible_evidence_refs})


@pytest.mark.parametrize(
    "number,digest",
    [
        (1, "8098de6deb4c909a90840cca679011707d8beb44dce68a05bbf15f4cb465a4f5"),
        (2, "f28c80011a6463acffbd8198673cb77ee641e1e0bcee83ff3b4734589d07c22c"),
        (3, "3c8fd9f117967ec85cb46ec0ec53cd18e103b763b95a4d5dfd8a47f42a9df6a9"),
        (4, "c4931508ab2f1a3597baaf7933e49bb6b3aa808fc36aa6495415405d2019cc51"),
        (5, "bfb2a448c75b113568be13b6854c9faa19457ba9f214ea0c6006e281f1022872"),
        (6, "37c6e9407494d71019bf48a71d2dcfcd393ae7bdf9acdfa8e57822d761003302"),
        (7, "bd6d19d7da417d1fe1b45968ca1545a94f625098851d9d292e49cb75ac4dbb19"),
    ],
)
def test_accepted_observable_profiles_preserve_legacy_canonical_hashes(
    number: int, digest: str
) -> None:
    # Derived from accepted bdc988a profile code in memory, never evaluator material.
    path = Path("datasets/development/inputs") / f"CAREER-DEV-{number:03d}.json"
    context = ImportContext(workspace_id=WORKSPACE, actor_id=ActorId("actor_" + "2" * 32))
    snapshot = load_observable(path.read_bytes(), context)
    assert snapshot.profile.content_digest == digest
    assert "experience_context" not in canonical_bytes(snapshot.profile).decode("utf-8")
    view = evidence_backed_profile(snapshot.profile, as_of=snapshot.as_of)
    assert view.profile_digest == digest and view.experience == ()
