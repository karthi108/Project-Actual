"""Support, provenance, revision and owner isolation for synthetic profile contracts."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

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
    claim_ref,
    evidence_ref,
    supports_assertion,
)

WORKSPACE = WorkspaceId("workspace_" + "1" * 32)
PROFILE = ProfileId("profile_" + "2" * 32)
ACTOR = ActorId("actor_" + "3" * 32)


def at(day: int) -> datetime:
    return datetime(2026, 1, day, 12, tzinfo=UTC)


def skill(value: int = 2, subject: str = "python") -> Assertion:
    return Assertion(kind="skill", subject=subject, unit="skill_level", value=value)


def source(**changes: object) -> EvidenceRecord:
    values: dict[str, object] = {
        "id": EvidenceId("evidence_" + "4" * 32),
        "workspace_id": WORKSPACE,
        "profile_id": PROFILE,
        "revision": 1,
        "classification": "synthetic",
        "assertion": skill(),
        "relation": "supports",
        "excerpt": "Synthetic project source establishes working-level Python.",
        "source_kind": "project_artifact",
        "source_reference": "synthetic:project:01",
        "source_actor_id": ACTOR,
        "collected_at": at(1),
        **changes,
    }
    return EvidenceRecord.model_validate(values)


def reviewed_source(
    *, review_kind: str = "source_review", independent: str | None = None, **changes: object
) -> EvidenceRecord:
    record = source(**changes)
    review = EvidenceReview.model_validate(
        {
            "reviewer_id": ACTOR,
            "kind": review_kind,
            "method": "Synthetic source scope review",
            "reviewed_at": at(3),
            "content_digest": record.content_digest,
            "independent_source_reference": independent,
        }
    )
    return record.model_copy(update={"review": review})


def assertion_claim(record: EvidenceRecord, *, reviewed: bool = True, **changes: object) -> Claim:
    claim = Claim.model_validate(
        {
            "id": ClaimId("claim_" + "5" * 32),
            "workspace_id": WORKSPACE,
            "profile_id": PROFILE,
            "revision": 1,
            "classification": "synthetic",
            "assertion": skill(),
            "text": "Synthetic claim: Python at working level.",
            "origin": "synthetic_fixture",
            "asserted_by": ACTOR,
            "asserted_at": at(2),
            "status": "candidate_support",
            "evidence_refs": (evidence_ref(record),),
            **changes,
        }
    )
    if not reviewed:
        return claim
    review = ContentReview(
        revision=claim.revision,
        content_digest=claim.content_digest,
        reviewer_id=ACTOR,
        reviewed_at=at(4),
        method="Synthetic assertion scope review",
        decision="accepted",
    )
    return claim.model_copy(update={"status": "reviewed_supported", "review": review})


def profile(claim: Claim, *records: EvidenceRecord, **changes: object) -> Profile:
    return Profile.model_validate(
        {
            "id": PROFILE,
            "workspace_id": WORKSPACE,
            "revision": 1,
            "classification": "synthetic",
            "name": "Synthetic candidate",
            "claims": (claim,),
            "evidence": records,
            **changes,
        }
    )


def test_roundtrip_keeps_provenance_and_exact_scoped_support() -> None:
    record = reviewed_source()
    claim = assertion_claim(record)
    snapshot = profile(claim, record)
    loaded = load_contract(Profile, canonical_bytes(snapshot))
    assert loaded == snapshot
    assert loaded.content_digest == snapshot.content_digest
    assert record.qualifies_support
    assert supports_assertion(loaded, skill(), (claim_ref(claim),))
    assert not supports_assertion(loaded, skill(3), (claim_ref(claim),))
    assert not supports_assertion(loaded, skill(subject="fastapi"), (claim_ref(claim),))
    assert not supports_assertion(loaded, skill(), ())


@pytest.mark.parametrize("value", [True, False, "2", 2.0, -1, 4])
def test_skill_values_are_strict_and_bounded(value: object) -> None:
    with pytest.raises(ValidationError):
        Assertion.model_validate(
            {"kind": "skill", "subject": "python", "unit": "skill_level", "value": value}
        )


@pytest.mark.parametrize(
    "kind,subject,unit,value",
    [
        ("skill", "python", "months", 12),
        ("language", "french", "skill_level", 2),
        ("language", "french", "cefr_level", 7),
        ("experience", "python", "months", 12),
        ("skill", "experience", "skill_level", 2),
        ("experience", "experience", "months", 601),
    ],
)
def test_assertion_kind_unit_and_subject_relationships(
    kind: str, subject: str, unit: str, value: int
) -> None:
    with pytest.raises(ValidationError):
        Assertion.model_validate({"kind": kind, "subject": subject, "unit": unit, "value": value})


def test_language_and_duration_use_distinct_supported_thresholds() -> None:
    assert Assertion(kind="language", subject="french", unit="cefr_level", value=4).value == 4
    assert Assertion(kind="experience", subject="experience", unit="months", value=12).value == 12


@pytest.mark.parametrize("origin", ["user_report", "ai_proposal"])
@pytest.mark.parametrize("kind", ["human_confirmation", "source_review", "synthetic_review"])
def test_self_report_or_ai_output_cannot_be_promoted_by_confirmation(
    origin: str, kind: str
) -> None:
    record = reviewed_source(source_kind=origin, review_kind=kind)
    assert not record.qualifies_support
    claim = assertion_claim(record)
    with pytest.raises(ValidationError):
        profile(claim, record)


def test_human_confirmation_alone_never_certifies_project_support() -> None:
    record = reviewed_source(review_kind="human_confirmation")
    assert not record.qualifies_support
    with pytest.raises(ValidationError):
        profile(assertion_claim(record), record)


def test_independent_source_must_exist_and_be_distinct() -> None:
    with pytest.raises(ValidationError):
        reviewed_source(source_kind="user_report", review_kind="independent_verification")
    with pytest.raises(ValidationError):
        reviewed_source(
            source_kind="user_report",
            review_kind="independent_verification",
            independent=" synthetic:project:01 ",
        )
    record = reviewed_source(
        source_kind="user_report",
        review_kind="independent_verification",
        independent="synthetic:separate:02",
    )
    assert record.qualifies_support
    assert supports_assertion(
        profile(assertion_claim(record), record), skill(), (claim_ref(assertion_claim(record)),)
    )


@pytest.mark.parametrize("classification", ["personal", "sensitive"])
def test_synthetic_sources_and_reviews_cannot_certify_real_data(classification: str) -> None:
    with pytest.raises(ValidationError):
        reviewed_source(source_kind="synthetic_fixture", classification=classification)
    with pytest.raises(ValidationError):
        reviewed_source(review_kind="synthetic_review", classification=classification)


def test_evidence_digest_binds_content_and_preserves_withdrawal_history() -> None:
    record = reviewed_source()
    withdrawn = record.model_copy(update={"status": "withdrawn"})
    assert withdrawn.content_digest == record.content_digest
    assert withdrawn.review == record.review
    assert not withdrawn.qualifies_support
    with pytest.raises(ValidationError):
        record.model_copy(update={"excerpt": "Synthetic changed source content."})
    with pytest.raises(ValidationError):
        record.model_copy(update={"source_reference": "synthetic:changed:02"})
    with pytest.raises(ValidationError):
        record.model_copy(update={"collected_at": at(5)})


@pytest.mark.parametrize("relation", ["supports", "contradicts"])
def test_changing_reviewed_evidence_relation_requires_a_new_source_review(relation: str) -> None:
    record = reviewed_source(relation=relation)
    changed_relation = "contradicts" if relation == "supports" else "supports"
    with pytest.raises(ValidationError):
        record.model_copy(update={"relation": changed_relation})
    proposed = record.model_copy(update={"relation": changed_relation, "review": None})
    assert proposed.content_digest != record.content_digest
    assert evidence_ref(proposed) != evidence_ref(record)
    assert not proposed.qualifies_support
    assert record.review is not None
    renewed = proposed.model_copy(
        update={
            "review": record.review.model_copy(
                update={"content_digest": proposed.content_digest, "reviewed_at": at(4)}
            )
        }
    )
    assert renewed.qualifies_support == (changed_relation == "supports")


@pytest.mark.parametrize(
    "field,value",
    [
        ("source_kind", "imported_document"),
        ("source_actor_id", ActorId("actor_" + "8" * 32)),
        ("classification", "personal"),
    ],
)
def test_changing_reviewed_source_provenance_cannot_retain_its_review(
    field: str, value: object
) -> None:
    record = reviewed_source()
    with pytest.raises(ValidationError):
        record.model_copy(update={field: value})


def test_review_cannot_precede_collection_even_with_current_digest() -> None:
    record = source(collected_at=at(4))
    review = EvidenceReview(
        reviewer_id=ACTOR,
        kind="source_review",
        method="Synthetic review",
        reviewed_at=at(3),
        content_digest=record.content_digest,
    )
    with pytest.raises(ValidationError):
        record.model_copy(update={"review": review})


@pytest.mark.parametrize(
    "field,value",
    [
        ("revision", 2),
        ("text", "Synthetic changed assertion text."),
        ("assertion", skill(3)),
    ],
)
def test_claim_changes_invalidate_exact_review(field: str, value: object) -> None:
    claim = assertion_claim(reviewed_source())
    with pytest.raises(ValidationError):
        claim.model_copy(update={field: value})


def test_self_report_status_needs_explicit_claim_review_before_promotion() -> None:
    record = reviewed_source()
    claim = assertion_claim(record, reviewed=False, origin="user_report", status="self_reported")
    snapshot = profile(claim, record)
    assert not supports_assertion(snapshot, skill(), (claim_ref(claim),))
    with pytest.raises(ValidationError):
        claim.model_copy(update={"status": "reviewed_supported"})


def test_unknown_assertion_creation_provenance_stays_unknown() -> None:
    record = reviewed_source()
    claim = assertion_claim(record, asserted_at=None, asserted_by=None)
    snapshot = profile(claim, record)
    assert snapshot.claims[0].asserted_at is None
    assert snapshot.claims[0].asserted_by is None
    assert supports_assertion(snapshot, skill(), (claim_ref(claim),))


def test_claim_review_cannot_predate_assertion_or_source_review() -> None:
    record = reviewed_source()
    claim = assertion_claim(record)
    assert claim.review is not None
    with pytest.raises(ValidationError):
        claim.model_copy(update={"review": claim.review.model_copy(update={"reviewed_at": at(1)})})
    before_source = claim.model_copy(
        update={"review": claim.review.model_copy(update={"reviewed_at": at(2)})}
    )
    with pytest.raises(ValidationError):
        profile(before_source, record)


@pytest.mark.parametrize(
    "field,value",
    [
        ("workspace_id", WorkspaceId("workspace_" + "6" * 32)),
        ("classification", "personal"),
        ("profile_id", ProfileId("profile_" + "6" * 32)),
        ("revision", 2),
        ("content_digest", "0" * 64),
    ],
)
def test_reference_owner_revision_and_digest_must_resolve(field: str, value: object) -> None:
    record = reviewed_source()
    claim = assertion_claim(record, reviewed=False)
    with pytest.raises(ValidationError):
        bad = claim.model_copy(
            update={"evidence_refs": (evidence_ref(record).model_copy(update={field: value}),)}
        )
        profile(bad, record)


def test_missing_or_wrong_subject_source_is_rejected() -> None:
    record = reviewed_source()
    claim = assertion_claim(record)
    with pytest.raises(ValidationError):
        profile(claim)
    wrong = reviewed_source(assertion=skill(subject="fastapi"))
    with pytest.raises(ValidationError):
        profile(assertion_claim(wrong), wrong)


def test_reviewed_support_requires_source_value_to_cover_exact_assertion() -> None:
    weak = reviewed_source(assertion=skill(1))
    with pytest.raises(ValidationError):
        profile(assertion_claim(weak), weak)


def test_withdrawn_evidence_changes_dependency_identity_and_invalidates_the_claim() -> None:
    record = reviewed_source()
    claim = assertion_claim(record)
    withdrawn = record.model_copy(update={"status": "withdrawn"})
    assert record.content_digest == withdrawn.content_digest
    assert evidence_ref(record) != evidence_ref(withdrawn)
    with pytest.raises(ValidationError):
        profile(claim, withdrawn)


def test_active_reviewed_contrary_source_requires_explicit_conflict() -> None:
    positive = reviewed_source()
    negative = reviewed_source(
        id=EvidenceId("evidence_" + "7" * 32), relation="contradicts", assertion=skill(1)
    )
    claim = assertion_claim(
        positive, reviewed=False, evidence_refs=(evidence_ref(positive), evidence_ref(negative))
    )
    with pytest.raises(ValidationError):
        profile(claim, positive, negative)
    contradicted = claim.model_copy(update={"status": "contradicted"})
    snapshot = profile(contradicted, positive, negative)
    assert not supports_assertion(snapshot, skill(), (claim_ref(contradicted),))
    with pytest.raises(ValidationError):
        profile(contradicted, positive)


def test_duplicate_evidence_references_and_profile_records_are_rejected() -> None:
    record = reviewed_source()
    with pytest.raises(ValidationError):
        assertion_claim(
            record, reviewed=False, evidence_refs=(evidence_ref(record), evidence_ref(record))
        )
    claim = assertion_claim(record)
    with pytest.raises(ValidationError):
        profile(claim, record, record)
    with pytest.raises(ValidationError):
        profile(claim, record, claims=(claim, claim))


def test_support_predicate_rejects_stale_foreign_and_duplicate_claim_refs() -> None:
    record = reviewed_source()
    claim = assertion_claim(record)
    snapshot = profile(claim, record)
    ref = claim_ref(claim)
    assert not supports_assertion(snapshot, skill(), (ref.model_copy(update={"revision": 2}),))
    assert not supports_assertion(
        snapshot, skill(), (ref.model_copy(update={"content_digest": "0" * 64}),)
    )
    assert not supports_assertion(
        snapshot,
        skill(),
        (ref.model_copy(update={"workspace_id": WorkspaceId("workspace_" + "8" * 32)}),),
    )
    assert not supports_assertion(snapshot, skill(), (ref, ref))


def test_profile_cannot_mix_synthetic_and_real_records_or_downgrade_classification() -> None:
    record = reviewed_source()
    claim = assertion_claim(record)
    with pytest.raises(ValidationError):
        profile(claim, record, classification="personal")
    with pytest.raises(ValidationError):
        profile(claim, record, classification="sensitive")
    real = reviewed_source(classification="sensitive")
    real_claim = assertion_claim(real, origin="imported_document", classification="sensitive")
    with pytest.raises(ValidationError):
        profile(real_claim, real, classification="personal")
    assert profile(real_claim, real, classification="sensitive").classification == "sensitive"


def test_reference_helpers_preserve_record_privacy_classification() -> None:
    record = reviewed_source(classification="sensitive")
    claim = assertion_claim(record, origin="imported_document", classification="sensitive")
    assert evidence_ref(record).classification == "sensitive"
    assert claim_ref(claim).classification == "sensitive"
    snapshot = profile(claim, record, classification="sensitive")
    assert not supports_assertion(
        snapshot,
        skill(),
        (claim_ref(claim).model_copy(update={"classification": "personal"}),),
    )


@pytest.mark.parametrize("reviewed", [False, True])
def test_personal_claim_cannot_downgrade_sensitive_linked_evidence(reviewed: bool) -> None:
    record = reviewed_source(classification="sensitive")
    with pytest.raises(ValidationError, match="downgrade linked evidence privacy"):
        claim = assertion_claim(
            record, reviewed=reviewed, origin="imported_document", classification="personal"
        )
        profile(claim, record, classification="sensitive")


def test_sensitive_claim_can_use_personal_sources_without_downgrading_privacy() -> None:
    record = reviewed_source(classification="personal")
    claim = assertion_claim(record, origin="imported_document", classification="sensitive")
    snapshot = profile(claim, record, classification="sensitive")
    assert supports_assertion(snapshot, skill(), (claim_ref(claim),))


def test_frozen_models_and_validated_copy_block_silent_state_upgrade() -> None:
    record = source()
    with pytest.raises(ValidationError):
        record.status = "withdrawn"  # type: ignore[misc]
    with pytest.raises(TypeError):
        EvidenceRecord.model_construct(**record.model_dump(mode="python"))
    with pytest.raises(ValidationError):
        record.model_copy(update={"status": "approved"})


def test_contrary_reviewed_evidence_cannot_be_hidden_by_unlinking() -> None:
    positive = reviewed_source()
    negative = reviewed_source(
        id=EvidenceId("evidence_" + "7" * 32), relation="contradicts", assertion=skill(1)
    )
    reviewed = assertion_claim(positive)
    assert len(reviewed.evidence_refs) == 1
    with pytest.raises(ValidationError):
        profile(reviewed, positive, negative)
    contradicted = reviewed.model_copy(update={"status": "contradicted", "review": None})
    assert not supports_assertion(
        profile(contradicted, positive, negative), skill(), (claim_ref(contradicted),)
    )


def test_withdrawn_or_unreviewed_contrary_source_does_not_create_verified_conflict() -> None:
    positive = reviewed_source()
    reviewed = assertion_claim(positive)
    negative = source(
        id=EvidenceId("evidence_" + "7" * 32), relation="contradicts", assertion=skill(1)
    )
    assert supports_assertion(
        profile(reviewed, positive, negative), skill(), (claim_ref(reviewed),)
    )
    withdrawn = reviewed_source(
        id=EvidenceId("evidence_" + "7" * 32),
        relation="contradicts",
        assertion=skill(1),
        status="withdrawn",
    )
    assert supports_assertion(
        profile(reviewed, positive, withdrawn), skill(), (claim_ref(reviewed),)
    )


def test_public_support_predicate_rejects_forged_nested_records() -> None:
    record = reviewed_source()
    claim = assertion_claim(record)
    snapshot = profile(claim, record)
    object.__setattr__(snapshot.evidence[0].assertion, "value", 3)
    assert not supports_assertion(snapshot, skill(), (claim_ref(claim),))


def test_public_support_predicate_requires_bounded_tuple_refs() -> None:
    record = reviewed_source()
    claim = assertion_claim(record)
    snapshot = profile(claim, record)
    assert not supports_assertion(snapshot, skill(), [claim_ref(claim)])  # type: ignore[arg-type]
    assert not supports_assertion(snapshot, skill(), (claim_ref(claim),) * 129)


def test_replacing_selected_evidence_invalidates_the_existing_claim_review() -> None:
    first = reviewed_source()
    second = reviewed_source(
        id=EvidenceId("evidence_" + "7" * 32), source_reference="synthetic:second:02"
    )
    claim = assertion_claim(first)
    with pytest.raises(ValidationError):
        claim.model_copy(update={"evidence_refs": (evidence_ref(second),)})


def test_reordering_selected_evidence_requires_exact_provenance_review_again() -> None:
    first = reviewed_source()
    second = reviewed_source(
        id=EvidenceId("evidence_" + "7" * 32), source_reference="synthetic:second:02"
    )
    claim = assertion_claim(first, evidence_refs=(evidence_ref(first), evidence_ref(second)))
    profile(claim, first, second)
    with pytest.raises(ValidationError):
        claim.model_copy(update={"evidence_refs": tuple(reversed(claim.evidence_refs))})


def test_renewed_claim_review_does_not_revalidate_old_downstream_references() -> None:
    first = reviewed_source()
    second = reviewed_source(
        id=EvidenceId("evidence_" + "7" * 32), source_reference="synthetic:second:02"
    )
    original = assertion_claim(first)
    old_ref = claim_ref(original)
    proposed = original.model_copy(
        update={
            "evidence_refs": (evidence_ref(second),),
            "status": "candidate_support",
            "review": None,
        }
    )
    assert proposed.content_digest != original.content_digest
    assert not supports_assertion(profile(proposed, first, second), skill(), (claim_ref(proposed),))
    review = ContentReview(
        revision=proposed.revision,
        content_digest=proposed.content_digest,
        reviewer_id=ACTOR,
        reviewed_at=at(5),
        method="Synthetic renewed provenance review",
        decision="accepted",
    )
    renewed = proposed.model_copy(update={"status": "reviewed_supported", "review": review})
    snapshot = profile(renewed, first, second)
    assert not supports_assertion(snapshot, skill(), (old_ref,))
    assert supports_assertion(snapshot, skill(), (claim_ref(renewed),))


def test_evidence_revision_change_cannot_reuse_existing_claim_review() -> None:
    first = reviewed_source()
    claim = assertion_claim(first)
    changed = first.model_copy(update={"revision": 2})
    assert first.content_digest == changed.content_digest
    assert evidence_ref(first) != evidence_ref(changed)
    with pytest.raises(ValidationError):
        claim.model_copy(update={"evidence_refs": (evidence_ref(changed),)})


def test_claim_digest_still_excludes_status_and_review_metadata() -> None:
    record = reviewed_source()
    claim = assertion_claim(record)
    withdrawn = claim.model_copy(update={"status": "withdrawn", "review": None})
    assert withdrawn.content_digest == claim.content_digest
    assert claim_ref(withdrawn) != claim_ref(claim)
    assert not supports_assertion(profile(withdrawn, record), skill(), (claim_ref(claim),))


def test_revoking_one_of_two_selected_qualifying_sources_invalidates_the_review() -> None:
    first = reviewed_source()
    second = reviewed_source(
        id=EvidenceId("evidence_" + "7" * 32), source_reference="synthetic:second:02"
    )
    claim = assertion_claim(first, evidence_refs=(evidence_ref(first), evidence_ref(second)))
    assert supports_assertion(profile(claim, first, second), skill(), (claim_ref(claim),))
    withdrawn = second.model_copy(update={"status": "withdrawn"})
    assert first.qualifies_support and not withdrawn.qualifies_support
    with pytest.raises(ValidationError, match="absent, stale, edited"):
        profile(claim, first, withdrawn)
    with pytest.raises(ValidationError, match="exact revision/content"):
        claim.model_copy(update={"evidence_refs": (evidence_ref(first), evidence_ref(withdrawn))})
    proposed = claim.model_copy(
        update={
            "evidence_refs": (evidence_ref(first),),
            "status": "candidate_support",
            "review": None,
        }
    )
    assert not supports_assertion(
        profile(proposed, first, withdrawn), skill(), (claim_ref(proposed),)
    )


@pytest.mark.parametrize("change", [{"review": None}, {"status": "withdrawn"}])
def test_source_review_and_state_changes_are_part_of_dependency_snapshot(
    change: dict[str, object],
) -> None:
    record = reviewed_source()
    changed = record.model_copy(update=change)
    assert changed.content_digest == record.content_digest
    assert changed.snapshot_digest != record.snapshot_digest
    assert evidence_ref(changed) != evidence_ref(record)


def test_changing_evidence_review_metadata_invalidates_selected_source_references() -> None:
    record = reviewed_source()
    assert record.review is not None
    edited_review = record.review.model_copy(update={"method": "Synthetic revised review method"})
    changed = record.model_copy(update={"review": edited_review})
    assert changed.qualifies_support
    assert changed.content_digest == record.content_digest
    assert evidence_ref(changed) != evidence_ref(record)
    claim = assertion_claim(record)
    with pytest.raises(ValidationError):
        profile(claim, changed)
    with pytest.raises(ValidationError):
        claim.model_copy(update={"evidence_refs": (evidence_ref(changed),)})


def test_changing_claim_review_metadata_changes_downstream_snapshot_identity() -> None:
    record = reviewed_source()
    claim = assertion_claim(record)
    assert claim.review is not None
    changed = claim.model_copy(
        update={"review": claim.review.model_copy(update={"method": "Synthetic renewed review"})}
    )
    assert claim.content_digest == changed.content_digest
    assert claim.snapshot_digest != changed.snapshot_digest
    snapshot = profile(changed, record)
    assert not supports_assertion(snapshot, skill(), (claim_ref(claim),))
    assert supports_assertion(snapshot, skill(), (claim_ref(changed),))
