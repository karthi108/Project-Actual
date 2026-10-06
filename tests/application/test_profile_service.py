"""Explicit synthetic reviews preserve separation, exact refs and one atomic save."""

from collections.abc import Callable
from datetime import timedelta

import pytest
from actual_application_fixtures import (
    ACTOR,
    NOW,
    WORKSPACE,
    MemoryRepository,
    RepositoryFailure,
    initialization,
    python_assertion,
)
from pydantic import ValidationError

from actual.application import CareerService, CareerState, UseCaseCode, UseCaseError
from actual.application.commands import AttachEvidence, CreateClaim
from actual.application.profile_commands import (
    ProfileRevisionCommand,
    ReviewSyntheticClaim,
    ReviewSyntheticEvidence,
    WithdrawEvidence,
)
from actual.career.materials import CVVariant
from actual.core.primitives import ClaimId, CVId, EvidenceId, canonical_bytes
from actual.profile.contracts import Claim, EvidenceRecord, claim_ref, evidence_ref
from actual.profile.experience import ExperienceContext

CLAIM_ID = ClaimId("claim_" + "5" * 32)
EVIDENCE_ID = EvidenceId("evidence_" + "6" * 32)


@pytest.fixture
def repository() -> MemoryRepository:
    return MemoryRepository()


@pytest.fixture
def service(repository: MemoryRepository) -> CareerService:
    service = CareerService(repository, WORKSPACE, ACTOR, clock=lambda: NOW)
    service.initialize(initialization())
    return service


def add_source(
    service: CareerService,
    *,
    source_kind: str = "synthetic_fixture",
    relation: str = "supports",
    value: int = 2,
) -> CareerState:
    state = service.create_claim(
        CreateClaim(
            expected_generation=service.get_state().generation,
            id=CLAIM_ID,
            assertion=python_assertion(),
            text="Synthetic Python declaration; this prose is not certified.",
        )
    )
    return service.attach_evidence(
        AttachEvidence(
            expected_generation=state.generation,
            id=EVIDENCE_ID,
            claim_id=CLAIM_ID,
            assertion=python_assertion(value),
            relation=relation,
            source_kind=source_kind,
            source_reference="synthetic:profile-review-source",
            excerpt="Synthetic source declares its structured Python level.",
            collected_at=NOW,
        )
    )


def command[T: ProfileRevisionCommand](
    kind: type[T], state: CareerState, record: Claim | EvidenceRecord, **updates: object
) -> T:
    return kind.model_validate(
        {
            "expected_generation": state.generation,
            "expected_revision": record.revision,
            "expected_digest": record.snapshot_digest,
            **updates,
        }
    )


def require_error(code: UseCaseCode, action: Callable[[], object]) -> None:
    with pytest.raises(UseCaseError) as captured:
        action()
    assert captured.value.code == code
    assert str(captured.value) == code.value


def review_source(service: CareerService) -> CareerState:
    state = service.get_state()
    source = state.snapshot.profile.evidence[0]
    return service.review_synthetic_evidence(
        source.id, command(ReviewSyntheticEvidence, state, source)
    )


def review_claim(service: CareerService) -> CareerState:
    state = service.get_state()
    claim = state.snapshot.profile.claims[0]
    return service.review_synthetic_claim(claim.id, command(ReviewSyntheticClaim, state, claim))


def test_source_and_claim_reviews_are_distinct_explicit_atomic_operations(
    service: CareerService, repository: MemoryRepository
) -> None:
    original = add_source(service)
    before_calls = len(repository.calls)
    reviewed = review_source(service)
    source = reviewed.snapshot.profile.evidence[0]
    claim = reviewed.snapshot.profile.claims[0]
    assert len(repository.calls) == before_calls + 1
    assert reviewed.generation == original.generation + 1
    assert source.revision == original.snapshot.profile.evidence[0].revision + 1
    assert source.review is not None
    assert source.review.kind == "synthetic_review"
    assert source.review.reviewer_id == ACTOR and source.review.reviewed_at == NOW
    assert source.review.content_digest == source.content_digest
    assert source.qualifies_support
    assert claim.status == "self_reported" and claim.review is None
    assert claim.evidence_refs == (evidence_ref(source),)
    assert claim.revision == original.snapshot.profile.claims[0].revision + 1
    accepted = review_claim(service)
    accepted_claim = accepted.snapshot.profile.claims[0]
    assert accepted_claim.status == "reviewed_supported"
    assert accepted_claim.review is not None
    assert accepted_claim.review.revision == accepted_claim.revision
    assert accepted_claim.review.content_digest == accepted_claim.content_digest
    assert accepted_claim.review.reviewer_id == ACTOR
    assert accepted_claim.origin == "user_report"
    assert accepted_claim.asserted_by == ACTOR and accepted_claim.asserted_at == NOW
    assert repository.calls[-1][2] == ()
    state, projection = service.evidence_profile()
    assert state == accepted
    assert canonical_bytes(projection) == canonical_bytes(service.evidence_profile()[1])


@pytest.mark.parametrize(
    "source_kind", ["user_report", "ai_proposal", "imported_document", "project_artifact"]
)
def test_review_route_cannot_certify_arbitrary_declared_provenance(
    source_kind: str, service: CareerService, repository: MemoryRepository
) -> None:
    state = add_source(service, source_kind=source_kind)
    calls = len(repository.calls)
    require_error(UseCaseCode.STATE_CONFLICT, lambda: review_source(service))
    require_error(UseCaseCode.STATE_CONFLICT, lambda: review_claim(service))
    assert repository.state == state and len(repository.calls) == calls


@pytest.mark.parametrize("kind", [ReviewSyntheticEvidence, ReviewSyntheticClaim, WithdrawEvidence])
def test_pinned_intents_are_closed_strict_and_round_trip(
    kind: type[ProfileRevisionCommand],
) -> None:
    intent = kind(expected_generation=1, expected_revision=1, expected_digest="a" * 64)
    assert kind.model_validate_json(intent.model_dump_json()) == intent
    for field in (
        "review_kind",
        "method",
        "reviewed_at",
        "reviewer_id",
        "status",
        "classification",
        "actor_id",
        "independent_source_reference",
    ):
        with pytest.raises(ValidationError):
            kind.model_validate({**intent.model_dump(), field: "caller-authority"})
    for field, value in (
        ("expected_revision", True),
        ("expected_generation", 0),
        ("expected_digest", "wrong"),
    ):
        with pytest.raises(ValidationError):
            kind.model_validate({**intent.model_dump(), field: value})


@pytest.mark.parametrize(
    "updates, code",
    [
        ({"expected_generation": 1}, UseCaseCode.STALE_GENERATION),
        ({"expected_revision": 2}, UseCaseCode.STATE_CONFLICT),
        ({"expected_digest": "a" * 64}, UseCaseCode.STATE_CONFLICT),
    ],
)
def test_source_review_requires_exact_current_pin(
    updates: dict[str, object],
    code: UseCaseCode,
    service: CareerService,
    repository: MemoryRepository,
) -> None:
    state = add_source(service)
    source = state.snapshot.profile.evidence[0]
    calls = len(repository.calls)
    intent = command(ReviewSyntheticEvidence, state, source, **updates)
    require_error(code, lambda: service.review_synthetic_evidence(source.id, intent))
    assert repository.state == state and len(repository.calls) == calls


def test_unreviewed_or_lower_source_cannot_accept_higher_claim(
    service: CareerService, repository: MemoryRepository
) -> None:
    original = add_source(service, value=1)
    require_error(UseCaseCode.STATE_CONFLICT, lambda: review_claim(service))
    reviewed = review_source(service)
    require_error(UseCaseCode.STATE_CONFLICT, lambda: review_claim(service))
    assert repository.state == reviewed
    assert reviewed.snapshot.profile.claims[0].status == "self_reported"
    assert (
        reviewed.snapshot.profile.claims[0].assertion.value
        == original.snapshot.profile.claims[0].assertion.value
    )


def test_reviewed_contrary_source_marks_conflict_without_accepting_claim(
    service: CareerService,
) -> None:
    add_source(service, relation="contradicts")
    reviewed = review_source(service)
    claim = reviewed.snapshot.profile.claims[0]
    assert claim.status == "contradicted" and claim.review is None
    require_error(UseCaseCode.STATE_CONFLICT, lambda: review_claim(service))
    source = reviewed.snapshot.profile.evidence[0]
    withdrawn = service.withdraw_evidence(source.id, command(WithdrawEvidence, reviewed, source))
    assert withdrawn.snapshot.profile.claims[0].status == "candidate_support"
    require_error(UseCaseCode.STATE_CONFLICT, lambda: review_claim(service))


def test_source_withdrawal_rebinds_all_claims_and_invalidates_previous_acceptance(
    service: CareerService,
) -> None:
    add_source(service)
    review_source(service)
    accepted = review_claim(service)
    source = accepted.snapshot.profile.evidence[0]
    withdrawn = service.withdraw_evidence(source.id, command(WithdrawEvidence, accepted, source))
    claim = withdrawn.snapshot.profile.claims[0]
    current = withdrawn.snapshot.profile.evidence[0]
    assert current.status == "withdrawn" and not current.qualifies_support
    assert current.review == source.review
    assert claim.status == "candidate_support" and claim.review is None
    assert claim.evidence_refs == (evidence_ref(current),)
    assert claim.origin == accepted.snapshot.profile.claims[0].origin
    require_error(UseCaseCode.STATE_CONFLICT, lambda: review_claim(service))
    require_error(
        UseCaseCode.STATE_CONFLICT,
        lambda: service.withdraw_evidence(
            current.id, command(WithdrawEvidence, withdrawn, current)
        ),
    )


def test_review_and_withdraw_reject_material_dependents_instead_of_rewriting_them(
    service: CareerService, repository: MemoryRepository
) -> None:
    state = add_source(service)
    claim = state.snapshot.profile.claims[0]
    cv = CVVariant(
        id=CVId("cv_" + "7" * 32),
        workspace_id=WORKSPACE,
        profile_id=state.snapshot.profile.id,
        revision=1,
        classification="synthetic",
        name="Synthetic existing material dependency",
        summary="Synthetic material dependency; no generated CV wording.",
        claim_refs=(claim_ref(claim),),
    )
    repository.state = CareerState(
        state.snapshot.model_copy(update={"cvs": (cv,)}), state.generation
    )
    before = repository.state
    source = state.snapshot.profile.evidence[0]
    require_error(UseCaseCode.DEPENDENCY_RECONCILIATION_REQUIRED, lambda: review_source(service))
    require_error(
        UseCaseCode.DEPENDENCY_RECONCILIATION_REQUIRED,
        lambda: service.withdraw_evidence(source.id, command(WithdrawEvidence, state, source)),
    )
    assert repository.state == before


def test_review_reconciles_multiple_claims_referencing_the_same_current_source(
    service: CareerService, repository: MemoryRepository
) -> None:
    state = add_source(service)
    profile = state.snapshot.profile
    first = profile.claims[0]
    second = first.model_copy(
        update={"id": ClaimId("claim_" + "8" * 32), "text": "Another explicit synthetic assertion."}
    )
    repository.state = CareerState(
        state.snapshot.model_copy(
            update={"profile": profile.model_copy(update={"claims": (first, second)})}
        ),
        state.generation,
    )
    reviewed = review_source(service)
    current = reviewed.snapshot.profile.evidence[0]
    assert len(reviewed.snapshot.profile.claims) == 2
    for claim in reviewed.snapshot.profile.claims:
        assert claim.revision == first.revision + 1
        assert claim.evidence_refs == (evidence_ref(current),)
        assert claim.status == "self_reported" and claim.review is None


def test_reviewed_contrary_source_cannot_be_hidden_by_omitting_its_claim_link(
    service: CareerService, repository: MemoryRepository
) -> None:
    state = add_source(service)
    profile = state.snapshot.profile
    positive = profile.evidence[0]
    contrary = positive.model_copy(
        update={
            "id": EvidenceId("evidence_" + "8" * 32),
            "relation": "contradicts",
            "source_reference": "synthetic:separate-contrary-source",
        }
    )
    repository.state = CareerState(
        state.snapshot.model_copy(
            update={"profile": profile.model_copy(update={"evidence": (positive, contrary)})}
        ),
        state.generation,
    )
    reviewed = service.review_synthetic_evidence(
        contrary.id, command(ReviewSyntheticEvidence, repository.state, contrary)
    )
    claim = reviewed.snapshot.profile.claims[0]
    assert claim.evidence_refs == state.snapshot.profile.claims[0].evidence_refs
    assert claim.status == "contradicted" and claim.review is None
    assert claim.revision == state.snapshot.profile.claims[0].revision + 1
    require_error(UseCaseCode.STATE_CONFLICT, lambda: review_claim(service))


def test_repeated_review_cannot_rewrite_existing_source_or_claim_review(
    service: CareerService, repository: MemoryRepository
) -> None:
    add_source(service)
    reviewed = review_source(service)
    source = reviewed.snapshot.profile.evidence[0]
    require_error(
        UseCaseCode.STATE_CONFLICT,
        lambda: service.review_synthetic_evidence(
            source.id, command(ReviewSyntheticEvidence, reviewed, source)
        ),
    )
    accepted = review_claim(service)
    claim = accepted.snapshot.profile.claims[0]
    require_error(
        UseCaseCode.STATE_CONFLICT,
        lambda: service.review_synthetic_claim(
            claim.id, command(ReviewSyntheticClaim, accepted, claim)
        ),
    )
    assert repository.state == accepted


def test_source_review_port_failure_leaves_current_state_unchanged(
    service: CareerService, repository: MemoryRepository
) -> None:
    state = add_source(service)
    repository.fail_save = True
    with pytest.raises(RepositoryFailure):
        review_source(service)
    assert repository.state == state


def test_backwards_server_clock_cannot_manufacture_review(
    service: CareerService, repository: MemoryRepository
) -> None:
    state = add_source(service)
    old_clock_service = CareerService(
        repository, WORKSPACE, ACTOR, clock=lambda: NOW - timedelta(microseconds=1)
    )
    require_error(UseCaseCode.INVALID_DOMAIN_INPUT, lambda: review_source(old_clock_service))
    assert repository.state == state


def test_experience_attachment_preserves_explicit_category_without_deriving_professional_months(
    service: CareerService,
) -> None:
    from actual.profile.contracts import Assertion

    assertion = Assertion(kind="experience", subject="experience", unit="months", value=24)
    claimed = service.create_claim(
        CreateClaim(
            expected_generation=1,
            id=CLAIM_ID,
            assertion=assertion,
            text="Synthetic personal project duration.",
        )
    )
    context = ExperienceContext(
        context_version="actual-experience-context-v1",
        category="personal_project",
        started_at=NOW - timedelta(days=730),
        ongoing=True,
    )
    attached = service.attach_evidence(
        AttachEvidence(
            expected_generation=claimed.generation,
            id=EVIDENCE_ID,
            claim_id=CLAIM_ID,
            assertion=assertion,
            relation="supports",
            source_kind="synthetic_fixture",
            source_reference="synthetic:personal-project",
            excerpt="Synthetic project activity duration, not employment.",
            collected_at=NOW,
            experience_context=context,
        )
    )
    assert attached.snapshot.profile.evidence[0].experience_context == context
    reviewed = review_source(service)
    assert reviewed.snapshot.profile.evidence[0].experience_context == context
    assert reviewed.snapshot.profile.claims[0].status == "self_reported"


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
def test_contextual_duration_cannot_be_promoted_into_a_generic_reviewed_claim(
    category: str, service: CareerService, repository: MemoryRepository
) -> None:
    from actual.profile.contracts import Assertion

    duration = Assertion(kind="experience", subject="experience", unit="months", value=24)
    claimed = service.create_claim(
        CreateClaim(
            expected_generation=1,
            id=CLAIM_ID,
            assertion=duration,
            text="Synthetic duration declaration.",
        )
    )
    service.attach_evidence(
        AttachEvidence(
            expected_generation=claimed.generation,
            id=EVIDENCE_ID,
            claim_id=CLAIM_ID,
            assertion=duration,
            relation="supports",
            source_kind="synthetic_fixture",
            source_reference="synthetic:typed-duration",
            excerpt="Synthetic source identifies a category; no generic equivalence is asserted.",
            collected_at=NOW,
            experience_context=ExperienceContext(
                context_version="actual-experience-context-v1", category=category
            ),
        )
    )
    reviewed = review_source(service)
    source = reviewed.snapshot.profile.evidence[0]
    assert source.review is not None and source._qualifies_review
    before_calls = len(repository.calls)
    require_error(UseCaseCode.STATE_CONFLICT, lambda: review_claim(service))
    assert repository.state == reviewed and len(repository.calls) == before_calls
    assert reviewed.snapshot.profile.claims[0].status == "self_reported"


def test_contextual_contrary_duration_cannot_refute_an_unscoped_claim(
    service: CareerService,
) -> None:
    from actual.profile.contracts import Assertion

    duration = Assertion(kind="experience", subject="experience", unit="months", value=24)
    claimed = service.create_claim(
        CreateClaim(
            expected_generation=1,
            id=CLAIM_ID,
            assertion=duration,
            text="Synthetic generic duration declaration remains unverified.",
        )
    )
    service.attach_evidence(
        AttachEvidence(
            expected_generation=claimed.generation,
            id=EVIDENCE_ID,
            claim_id=CLAIM_ID,
            assertion=duration,
            relation="contradicts",
            source_kind="synthetic_fixture",
            source_reference="synthetic:category-specific-contrary-duration",
            excerpt="Synthetic internship context does not refute generic experience.",
            collected_at=NOW,
            experience_context=ExperienceContext(
                context_version="actual-experience-context-v1", category="internship"
            ),
        )
    )
    reviewed = review_source(service)
    source = reviewed.snapshot.profile.evidence[0]
    claim = reviewed.snapshot.profile.claims[0]
    assert source.relation == "contradicts" and source._qualifies_review
    assert not source.qualifies_contradiction
    assert claim.status == "self_reported" and claim.review is None
    assert claim.evidence_refs == (evidence_ref(source),)
    _, view = service.evidence_profile()
    assert view.rows[0].state == "unverified"
    assert not view.rows[0].contrary_evidence_refs
    assert view.rows[0].contextual_evidence_refs == (evidence_ref(source),)
