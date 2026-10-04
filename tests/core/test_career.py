"""Career boundaries: lifecycle, owner scope and immutable review bindings."""

from itertools import product

import pytest
from pydantic import ValidationError

from actual.career.applications import Application, StatusObservation, allowed_transition
from actual.career.jobs import Company, Job, Requirement
from actual.career.materials import CVVariant, Draft, DraftAssertion
from actual.core.primitives import (
    ActorId,
    ApplicationId,
    ClaimId,
    CompanyId,
    CVId,
    DraftId,
    JobId,
    OpportunityId,
    ProfileId,
    RequirementId,
    WorkspaceId,
    canonical_bytes,
    load_contract,
)
from actual.core.references import ClaimRef
from actual.core.workflow import ContentReview
from actual.profile.contracts import Assertion

WORKSPACE = WorkspaceId("workspace_" + "1" * 32)
PROFILE = ProfileId("profile_" + "2" * 32)
ACTOR = ActorId("actor_" + "3" * 32)
JOB_ID = JobId("job_" + "4" * 32)
COMPANY_ID = CompanyId("company_" + "5" * 32)


@pytest.fixture
def job() -> Job:
    return Job(
        id=JOB_ID,
        workspace_id=WORKSPACE,
        revision=1,
        classification="synthetic",
        company_id=COMPANY_ID,
        opportunity_id=OpportunityId("opportunity_" + "6" * 32),
        title="Synthetic backend role",
        text="Python at working level is essential.",
        source_reference="synthetic-manual-source-01",
        posted_at="2026-09-01T12:00:00Z",
        decision="new",
    )


@pytest.fixture
def assertion() -> Assertion:
    return Assertion(kind="skill", subject="python", unit="skill_level", value=2)


@pytest.fixture
def requirement(job: Job, assertion: Assertion) -> Requirement:
    return Requirement(
        id=RequirementId("requirement_" + "7" * 32),
        workspace_id=WORKSPACE,
        revision=1,
        classification="synthetic",
        job_id=job.id,
        job_revision=job.revision,
        job_digest=job.content_digest,
        assertion=assertion,
        priority="essential",
        source_start=0,
        source_end=len(job.text),
        source_quote=job.text,
        origin="user_report",
    )


@pytest.fixture
def claim_ref() -> ClaimRef:
    return ClaimRef(
        workspace_id=WORKSPACE,
        profile_id=PROFILE,
        classification="synthetic",
        claim_id=ClaimId("claim_" + "8" * 32),
        revision=1,
        content_digest="a" * 64,
    )


@pytest.fixture
def cv(claim_ref: ClaimRef) -> CVVariant:
    return CVVariant(
        id=CVId("cv_" + "9" * 32),
        workspace_id=WORKSPACE,
        profile_id=PROFILE,
        revision=1,
        classification="synthetic",
        name="Synthetic backend CV",
        summary="Synthetic project work with Python.",
        claim_refs=(claim_ref,),
    )


@pytest.fixture
def draft(assertion: Assertion, claim_ref: ClaimRef) -> Draft:
    proposal = DraftAssertion(
        assertion=assertion,
        text="Synthetic proposal: Python at working level.",
        source_claim_refs=(claim_ref,),
    )
    return Draft(
        id=DraftId("draft_" + "a" * 32),
        workspace_id=WORKSPACE,
        profile_id=PROFILE,
        revision=1,
        classification="synthetic",
        name="Synthetic application draft",
        summary="Synthetic application summary.",
        assertions=(proposal,),
    )


def observation(state: str, day: int, **changes: object) -> StatusObservation:
    return StatusObservation.model_validate(
        {
            "actor_id": ACTOR,
            "occurred_at": f"2026-09-{day:02d}T12:00:00Z",
            "recorded_at": f"2026-09-{day:02d}T13:00:00Z",
            "state": state,
            "basis": "user_reported",
            **changes,
        }
    )


def application(history: tuple[StatusObservation, ...], **changes: object) -> Application:
    return Application.model_validate(
        {
            "id": ApplicationId("application_" + "b" * 32),
            "workspace_id": WORKSPACE,
            "revision": 1,
            "classification": "synthetic",
            "job_id": JOB_ID,
            "profile_id": PROFILE,
            "state": history[-1].state if history else "preparing",
            "history": history,
            **changes,
        }
    )


def review_for(value: Draft | Requirement, **changes: object) -> ContentReview:
    return ContentReview.model_validate(
        {
            "revision": value.revision,
            "content_digest": value.content_digest,
            "reviewer_id": ACTOR,
            "reviewed_at": "2026-10-01T12:00:00Z",
            "method": "Synthetic exact-content review",
            "decision": "accepted",
            **changes,
        }
    )


def test_lifecycle_cartesian_space_preserves_manual_submission_exception() -> None:
    states = (
        "preparing",
        "ready_for_review",
        "reviewed",
        "applied",
        "interview",
        "offer",
        "closed",
    )
    ordinary = {
        ("preparing", "ready_for_review"),
        ("preparing", "closed"),
        ("ready_for_review", "preparing"),
        ("ready_for_review", "reviewed"),
        ("ready_for_review", "closed"),
        ("reviewed", "preparing"),
        ("reviewed", "applied"),
        ("reviewed", "closed"),
        ("applied", "interview"),
        ("applied", "closed"),
        ("interview", "offer"),
        ("interview", "closed"),
        ("offer", "closed"),
    }
    for previous, target, basis, manual in product(
        states, states, ("user_reported", "synthetic_observation"), (False, True)
    ):
        expected = (
            basis == "user_reported"
            and previous in ("preparing", "ready_for_review")
            and target == "applied"
            if manual
            else (previous, target) in ordinary
        )
        assert allowed_transition(previous, target, basis, manual) == expected


@pytest.mark.parametrize("previous", ["preparing", "ready_for_review"])
def test_external_manual_application_tracking_does_not_invent_review(previous: str) -> None:
    prefix = (observation("preparing", 2),)
    if previous == "ready_for_review":
        prefix += (observation(previous, 3),)
    app = application(prefix + (observation("applied", 4, external_manual=True),))
    assert app.state == "applied"
    assert "reviewed" not in {entry.state for entry in app.history}
    assert "review" not in app.model_dump()


def test_ordinary_internal_path_preserves_all_recorded_states() -> None:
    states = ("preparing", "ready_for_review", "reviewed", "applied", "interview", "offer")
    app = application(tuple(observation(state, day) for day, state in enumerate(states, 2)))
    assert tuple(entry.state for entry in app.history) == states


@pytest.mark.parametrize("target", ["reviewed", "applied", "interview", "offer"])
def test_preparing_cannot_skip_internal_states_without_the_manual_exception(target: str) -> None:
    with pytest.raises(ValidationError):
        application((observation("preparing", 2), observation(target, 3)))


def test_reviewed_application_state_is_an_observation_without_content_approval() -> None:
    app = application(
        (
            observation("preparing", 2),
            observation("ready_for_review", 3),
            observation("reviewed", 4),
        )
    )
    assert app.state == "reviewed"
    assert set(app.model_dump()) == {
        "schema_version",
        "id",
        "workspace_id",
        "revision",
        "classification",
        "job_id",
        "profile_id",
        "state",
        "history",
    }


@pytest.mark.parametrize(
    "target",
    ["preparing", "ready_for_review", "reviewed", "applied", "interview", "offer", "closed"],
)
def test_closed_application_is_terminal(target: str) -> None:
    history = (observation("preparing", 2), observation("closed", 3), observation(target, 4))
    with pytest.raises(ValidationError):
        application(history)


@pytest.mark.parametrize("basis", ["synthetic_observation", "independently_verified"])
def test_external_manual_flag_cannot_create_verified_or_synthetic_delivery(basis: str) -> None:
    with pytest.raises(ValidationError):
        observation("applied", 2, basis=basis, external_manual=True)


@pytest.mark.parametrize("state", ["preparing", "reviewed", "interview", "closed"])
def test_external_manual_flag_has_no_other_state_meaning(state: str) -> None:
    with pytest.raises(ValidationError):
        observation(state, 2, external_manual=True)


@pytest.mark.parametrize("flag", [1, 0, "true", None])
def test_manual_tracking_flag_rejects_coercion(flag: object) -> None:
    with pytest.raises(ValidationError):
        observation("applied", 2, external_manual=flag)


def test_status_observation_cannot_be_recorded_before_it_occurred() -> None:
    with pytest.raises(ValidationError):
        observation("preparing", 2, recorded_at="2026-09-02T11:00:00Z")


def test_late_recording_does_not_reorder_causal_history() -> None:
    history = tuple(
        observation(state, day, recorded_at="2026-09-20T12:00:00Z")
        for day, state in enumerate(("preparing", "ready_for_review", "reviewed"), 2)
    )
    assert application(history).state == "reviewed"


def test_history_requires_strict_occurrence_order() -> None:
    first = observation("preparing", 2)
    repeated_time = observation("ready_for_review", 2)
    with pytest.raises(ValidationError):
        application((first, repeated_time))


def test_history_requires_first_preparing_and_current_last_state() -> None:
    with pytest.raises(ValidationError):
        application((observation("reviewed", 2),))
    with pytest.raises(ValidationError):
        application((observation("preparing", 2),), state="applied")


def test_history_is_nonempty_and_bounded() -> None:
    with pytest.raises(ValidationError):
        application(())
    with pytest.raises(ValidationError):
        application((observation("preparing", 2),) * 501)


def test_job_decision_is_distinct_from_application_state(job: Job) -> None:
    pursued = job.model_copy(update={"decision": "pursuing"})
    preparing = application((observation("preparing", 2),))
    assert pursued.decision == "pursuing"
    assert preparing.state == "preparing"
    with pytest.raises(ValidationError):
        job.model_copy(update={"decision": "applied"})
    with pytest.raises(ValidationError):
        preparing.model_copy(update={"state": "pursuing"})


@pytest.mark.parametrize("field", ["title", "text", "source_reference", "decision"])
def test_job_revision_digest_identifies_source_and_decision_changes(job: Job, field: str) -> None:
    changes = {
        "title": "Synthetic changed role",
        "text": "Python at introductory level is preferred.",
        "source_reference": "synthetic-manual-source-02",
        "decision": "pursuing",
    }
    assert job.model_copy(update={field: changes[field]}).content_digest != job.content_digest


def test_company_and_job_roundtrip_preserve_content_identity(job: Job) -> None:
    company = Company(
        id=COMPANY_ID,
        workspace_id=WORKSPACE,
        revision=1,
        classification="synthetic",
        name="Synthetic Company",
        context="Synthetic software company.",
    )
    assert load_contract(Company, canonical_bytes(company)) == company
    assert load_contract(Job, canonical_bytes(job)).content_digest == job.content_digest


@pytest.mark.parametrize(
    "change",
    [
        {"source_start": -1},
        {"source_end": 0},
        {"source_start": 4, "source_end": 4},
        {"source_start": True},
        {"source_end": "5"},
    ],
)
def test_requirement_source_span_rejects_invalid_state(
    requirement: Requirement, change: dict[str, object]
) -> None:
    with pytest.raises(ValidationError):
        requirement.model_copy(update=change)


def test_requirement_remains_a_proposal_without_a_review(requirement: Requirement) -> None:
    proposed = requirement.model_copy(update={"origin": "ai_proposal", "priority": "ambiguous"})
    assert proposed.review is None
    assert load_contract(Requirement, canonical_bytes(proposed)) == proposed


@pytest.mark.parametrize("decision", ["accepted", "rejected"])
def test_requirement_review_binds_content_but_never_changes_its_digest(
    requirement: Requirement, decision: str
) -> None:
    review = review_for(requirement, decision=decision)
    reviewed = requirement.model_copy(update={"review": review})
    assert reviewed.content_digest == requirement.content_digest
    assert reviewed.review == review


@pytest.mark.parametrize("change", [{"revision": 2}, {"content_digest": "f" * 64}])
def test_requirement_rejects_stale_revision_or_content_review(
    requirement: Requirement, change: dict[str, object]
) -> None:
    with pytest.raises(ValidationError):
        requirement.model_copy(update={"review": review_for(requirement, **change)})


@pytest.mark.parametrize("field", ["source_quote", "priority", "origin", "job_revision"])
def test_reviewed_requirement_change_requires_new_review(
    requirement: Requirement, field: str
) -> None:
    reviewed = requirement.model_copy(update={"review": review_for(requirement)})
    changes = {
        "source_quote": "Changed source quotation.",
        "priority": "preferred",
        "origin": "ai_proposal",
        "job_revision": 2,
    }
    with pytest.raises(ValidationError):
        reviewed.model_copy(update={field: changes[field]})


@pytest.mark.parametrize("field", ["workspace_id", "profile_id"])
def test_cv_cannot_attach_another_owners_claim(
    cv: CVVariant, claim_ref: ClaimRef, field: str
) -> None:
    other = (
        WorkspaceId("workspace_" + "c" * 32)
        if field == "workspace_id"
        else ProfileId("profile_" + "c" * 32)
    )
    wrong = claim_ref.model_copy(update={field: other})
    with pytest.raises(ValidationError):
        cv.model_copy(update={"claim_refs": (wrong,)})


def test_cv_rejects_repeated_claims_even_with_different_revisions(
    cv: CVVariant, claim_ref: ClaimRef
) -> None:
    newer = claim_ref.model_copy(update={"revision": 2, "content_digest": "b" * 64})
    with pytest.raises(ValidationError):
        cv.model_copy(update={"claim_refs": (claim_ref, newer)})


def test_material_reference_collections_are_bounded(cv: CVVariant, claim_ref: ClaimRef) -> None:
    with pytest.raises(ValidationError):
        cv.model_copy(update={"claim_refs": (claim_ref,) * 201})


def test_draft_can_preserve_an_unsupported_unreviewed_proposal(draft: Draft) -> None:
    unsupported = draft.assertions[0].model_copy(update={"source_claim_refs": ()})
    saved = draft.model_copy(update={"assertions": (unsupported,)})
    assert saved.review is None
    assert saved.assertions[0].source_claim_refs == ()


@pytest.mark.parametrize("field", ["workspace_id", "profile_id"])
def test_draft_cannot_attach_another_owners_claim(
    draft: Draft, claim_ref: ClaimRef, field: str
) -> None:
    other = (
        WorkspaceId("workspace_" + "d" * 32)
        if field == "workspace_id"
        else ProfileId("profile_" + "d" * 32)
    )
    wrong = claim_ref.model_copy(update={field: other})
    assertion = draft.assertions[0].model_copy(update={"source_claim_refs": (wrong,)})
    with pytest.raises(ValidationError):
        draft.model_copy(update={"assertions": (assertion,)})


def test_draft_assertion_rejects_repeated_source_claims(draft: Draft, claim_ref: ClaimRef) -> None:
    with pytest.raises(ValidationError):
        draft.assertions[0].model_copy(update={"source_claim_refs": (claim_ref, claim_ref)})


def test_draft_review_binds_digest_and_keeps_permission_out_of_the_schema(draft: Draft) -> None:
    reviewed = draft.model_copy(update={"review": review_for(draft)})
    assert reviewed.content_digest == draft.content_digest
    assert load_contract(Draft, canonical_bytes(reviewed)) == reviewed
    with pytest.raises(ValidationError):
        reviewed.model_copy(update={"send_approved": True})


@pytest.mark.parametrize("change", [{"revision": 2}, {"content_digest": "f" * 64}])
def test_draft_rejects_stale_review(draft: Draft, change: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        draft.model_copy(update={"review": review_for(draft, **change)})


@pytest.mark.parametrize("field", ["name", "summary", "revision"])
def test_reviewed_draft_edit_requires_new_review(draft: Draft, field: str) -> None:
    reviewed = draft.model_copy(update={"review": review_for(draft)})
    changes = {"name": "Changed synthetic name", "summary": "Changed summary", "revision": 2}
    with pytest.raises(ValidationError):
        reviewed.model_copy(update={field: changes[field]})


def test_reviewed_draft_factual_change_requires_new_review(draft: Draft) -> None:
    reviewed = draft.model_copy(update={"review": review_for(draft)})
    stronger = draft.assertions[0].assertion.model_copy(update={"value": 3})
    changed = draft.assertions[0].model_copy(update={"assertion": stronger})
    with pytest.raises(ValidationError):
        reviewed.model_copy(update={"assertions": (changed,)})


@pytest.mark.parametrize(
    "change",
    [
        {"title": " "},
        {"title": "x" * 201},
        {"text": "x" * 12001},
        {"revision": True},
        {"classification": "secret"},
        {"unknown_field": "data"},
    ],
)
def test_job_rejects_unbounded_coerced_or_unregistered_fields(
    job: Job, change: dict[str, object]
) -> None:
    with pytest.raises(ValidationError):
        job.model_copy(update=change)


def test_application_rejects_wrong_object_identifier_kind() -> None:
    with pytest.raises(ValidationError):
        application((observation("preparing", 2),), job_id=PROFILE)


@pytest.mark.parametrize("kind", ["cv", "draft"])
@pytest.mark.parametrize(
    ("material_class", "claim_class", "permitted"),
    [
        ("synthetic", "synthetic", True),
        ("synthetic", "personal", False),
        ("synthetic", "sensitive", False),
        ("personal", "synthetic", False),
        ("personal", "personal", True),
        ("personal", "sensitive", False),
        ("sensitive", "synthetic", False),
        ("sensitive", "personal", True),
        ("sensitive", "sensitive", True),
    ],
)
def test_standalone_material_preserves_source_privacy_without_a_catalog(
    cv: CVVariant,
    draft: Draft,
    claim_ref: ClaimRef,
    kind: str,
    material_class: str,
    claim_class: str,
    permitted: bool,
) -> None:
    source = claim_ref.model_copy(update={"classification": claim_class})
    if kind == "cv":
        value = cv
        changes = {"classification": material_class, "claim_refs": (source,)}
    else:
        value = draft
        proposal = draft.assertions[0].model_copy(update={"source_claim_refs": (source,)})
        changes = {"classification": material_class, "assertions": (proposal,)}
    if permitted:
        mapped = value.model_copy(update=changes)
        assert load_contract(type(mapped), canonical_bytes(mapped)) == mapped
    else:
        with pytest.raises(ValidationError):
            value.model_copy(update=changes)
