"""Preparation preserves provenance, uncertainty, pins and atomic review."""

import pytest
from actual_application_fixtures import (
    ACTOR,
    NOW,
    WORKSPACE,
    MemoryRepository,
    initialization,
    manual_job,
)
from pydantic import ValidationError
from test_profile_service import add_source, review_claim, review_source

from actual.application.errors import UseCaseCode, UseCaseError
from actual.application.preparation_commands import (
    CompareCVs,
    CreateCV,
    PrepareDraft,
    ReviewDraft,
    ReviseDraft,
    SourceSelection,
)
from actual.application.preparation_service import PreparationService
from actual.career.snapshot import CareerSnapshot
from actual.core.primitives import CVId, DraftId, canonical_bytes, canonical_data

CV = CVId("cv_" + "7" * 32)
DRAFT = DraftId("draft_" + "8" * 32)


def prepared_service(*, reviewed=True):
    repository = MemoryRepository()
    service = PreparationService(repository, WORKSPACE, ACTOR, clock=lambda: NOW)
    service.initialize(initialization(job=manual_job(text="Python at working level is essential.")))
    add_source(service)
    if reviewed:
        review_source(service)
        review_claim(service)
    state = service.get_state()
    service.create_cv(
        CreateCV(
            expected_generation=state.generation,
            id=CV,
            name="Synthetic Python CV",
            claim_ids=(state.snapshot.profile.claims[0].id,),
        )
    )
    return service, repository


def prepare(service, kind="application_message"):
    state = service.get_state()
    return service.prepare(
        PrepareDraft(
            expected_generation=state.generation,
            id=DRAFT,
            job_id=state.snapshot.jobs[0].id,
            cv_id=CV,
            material_kind=kind,
        )
    )


@pytest.mark.parametrize("kind", ["cv_adaptation", "application_message", "cover_letter"])
def test_supported_units_only_and_template_tampering_rejected(kind):
    service, _ = prepared_service()
    state = prepare(service, kind)
    draft = state.snapshot.drafts[0]
    assert draft.assertions[0].text == "python: supported skill unit 2/3."
    assert "not certified" not in draft.assertions[0].text
    assert draft.preparation.cv.content_digest == state.snapshot.cvs[0].content_digest
    payload = state.snapshot.model_dump(mode="json")
    payload["drafts"][0]["assertions"][0]["text"] = "Five years of Python employment"
    with pytest.raises(ValidationError):
        CareerSnapshot.model_validate_json(__import__("json").dumps(payload))
    assert "Five years" not in draft.model_dump_json()


def test_unverified_claim_excluded_and_comparison_is_transient():
    service, repository = prepared_service(reviewed=False)
    state = prepare(service)
    assert state.snapshot.drafts[0].assertions == ()
    calls = len(repository.calls)
    report = service.compare_cvs(
        CompareCVs(
            expected_generation=state.generation,
            job_id=state.snapshot.jobs[0].id,
        )
    )
    assert len(report.unresolved_claims) == 1
    assert report.suggested_cv_ids == ()
    assert len(repository.calls) == calls


def test_exact_review_atomic_event_and_revision_invalidates_review():
    service, repository = prepared_service()
    state = prepare(service)
    draft = state.snapshot.drafts[0]
    binding = dict(
        expected_generation=state.generation,
        expected_revision=1,
        expected_digest=draft.content_digest,
        decision="accepted",
    )
    with pytest.raises(UseCaseError) as captured:
        service.review(DRAFT, ReviewDraft(**{**binding, "expected_digest": "a" * 64}))
    assert captured.value.code == UseCaseCode.STATE_CONFLICT
    state = service.review(DRAFT, ReviewDraft(**binding))
    reviewed = state.snapshot.drafts[0]
    assert reviewed.review.reviewer_id == ACTOR
    assert reviewed.review.reviewed_at == NOW
    assert repository.calls[-1][2][0].activity == "draft_reviewed"
    assert repository.calls[-1][2][0].payload.decision == "accepted"
    state = service.revise(
        DRAFT,
        ReviseDraft(
            expected_generation=state.generation,
            expected_revision=reviewed.revision,
            expected_digest=reviewed.content_digest,
            job_id=state.snapshot.jobs[0].id,
            cv_id=CV,
            material_kind="cover_letter",
        ),
    )
    assert reviewed.revision == 2
    assert state.snapshot.drafts[0].revision == 3
    assert state.snapshot.drafts[0].review is None


def test_legacy_serialization_omits_extension():
    from actual.career.materials import Draft
    from actual.core.primitives import ProfileId

    old = dict(
        id=DRAFT,
        workspace_id=WORKSPACE,
        profile_id=ProfileId("profile_" + "3" * 32),
        classification="synthetic",
        revision=1,
        name="Legacy",
        summary="Legacy prose",
        assertions=(),
        review=None,
    )
    draft = Draft(**old)
    assert "preparation" not in draft.model_dump(mode="json")
    assert canonical_bytes(draft) == canonical_data(
        {
            "schema_version": "actual-core-v1",
            **{key: value.root if hasattr(value, "root") else value for key, value in old.items()},
        }
    )


def test_selection_requires_exact_unambiguous_source_quote():
    service, _ = prepared_service()
    state = service.get_state()
    with pytest.raises(UseCaseError) as captured:
        service.compare_cvs(
            CompareCVs(
                expected_generation=state.generation,
                job_id=state.snapshot.jobs[0].id,
                selections=(
                    SourceSelection(quote="Python required", term="Python", priority="essential"),
                ),
            )
        )
    assert captured.value.code == UseCaseCode.INVALID_DOMAIN_INPUT


def test_cv_selection_keeps_supported_source_matrix_and_no_overall_score():
    service, repository = prepared_service()
    state = service.get_state()
    before = len(repository.calls)
    report = service.compare_cvs(
        CompareCVs(
            expected_generation=state.generation,
            job_id=state.snapshot.jobs[0].id,
            selections=(
                SourceSelection(
                    quote="Python at working level is essential.",
                    term="Python",
                    priority="essential",
                ),
            ),
        )
    )
    assert report.assessment.rows[0].status == "supported"
    assert report.options[0].covered_essential == 1
    assert report.suggested_cv_ids == (CV,)
    assert report.unresolved_claims == ()
    assert len(repository.calls) == before
    assert "score" not in type(report).model_fields


def test_current_contrary_source_excludes_prepared_fact():
    from actual.core.primitives import EvidenceId
    from actual.preparation.render import units

    service, _ = prepared_service()
    state = service.get_state()
    profile = state.snapshot.profile
    source = profile.evidence[0]
    other = source.model_copy(
        update={
            "id": EvidenceId("evidence_" + "9" * 32),
            "relation": "contradicts",
            "review": None,
        }
    )
    other = other.model_copy(
        update={"review": source.review.model_copy(update={"content_digest": other.content_digest})}
    )
    # An accepted supported claim cannot silently coexist with contrary review.
    with pytest.raises(ValidationError, match="explicit conflict"):
        profile.model_copy(update={"evidence": (*profile.evidence, other)})
    claim = profile.claims[0].model_copy(update={"status": "contradicted", "review": None})
    profile = profile.model_copy(
        update={"evidence": (*profile.evidence, other), "claims": (claim,)}
    )
    from actual.profile.contracts import claim_ref

    cv = state.snapshot.cvs[0].model_copy(update={"claim_refs": (claim_ref(claim),)})
    assert units(profile, cv) == ()
