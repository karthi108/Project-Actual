"""Experience metadata retains category/time without manufacturing duration."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from actual.core.primitives import (
    ActorId,
    EvidenceId,
    ProfileId,
    WorkspaceId,
    canonical_bytes,
    load_contract,
)
from actual.profile.contracts import Assertion, EvidenceRecord, EvidenceReview, evidence_ref
from actual.profile.experience import ExperienceContext


def at(day: int) -> datetime:
    return datetime(2026, 1, day, 12, tzinfo=UTC)


def context(**changes: object) -> ExperienceContext:
    return ExperienceContext.model_validate(
        {
            "context_version": "actual-experience-context-v1",
            "category": "internship",
            **changes,
        }
    )


def record(**changes: object) -> EvidenceRecord:
    return EvidenceRecord.model_validate(
        {
            "id": EvidenceId("evidence_" + "1" * 32),
            "workspace_id": WorkspaceId("workspace_" + "2" * 32),
            "profile_id": ProfileId("profile_" + "3" * 32),
            "revision": 1,
            "classification": "synthetic",
            "assertion": Assertion(kind="experience", subject="experience", unit="months", value=6),
            "relation": "supports",
            "excerpt": "Fabricated source records a six-month internship.",
            "source_kind": "imported_document",
            "source_reference": "synthetic:internship:01",
            "collected_at": at(20),
            **changes,
        }
    )


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
def test_categories_and_unknown_activity_dates_survive_roundtrip(category: str) -> None:
    source = record(experience_context=context(category=category))
    loaded = load_contract(EvidenceRecord, canonical_bytes(source))
    assert loaded == source
    assert loaded.experience_context is not None
    assert loaded.experience_context.category == category
    assert loaded.experience_context.started_at is None
    assert loaded.experience_context.ended_at is None
    assert loaded.experience_context.ongoing is None
    assert loaded.assertion.value == 6


@pytest.mark.parametrize(
    "field,value", [("ongoing", 1), ("ongoing", "true"), ("category", "employment")]
)
def test_context_rejects_coercion_and_unregistered_categories(field: str, value: object) -> None:
    with pytest.raises(ValidationError):
        context(**{field: value})


@pytest.mark.parametrize("version", [None, "actual-experience-context-v2", 1])
def test_extension_version_is_explicit_and_closed(version: object) -> None:
    with pytest.raises(ValidationError):
        context(context_version=version)
    with pytest.raises(ValidationError):
        ExperienceContext(category="unknown")  # type: ignore[call-arg]


def test_activity_period_order_ongoing_and_aware_time_boundaries() -> None:
    with pytest.raises(ValidationError):
        context(started_at=at(10), ended_at=at(9))
    with pytest.raises(ValidationError):
        context(started_at=at(1), ended_at=at(9), ongoing=True)
    with pytest.raises(ValidationError):
        context(started_at=datetime(2026, 1, 1))
    ongoing = context(started_at=at(1), ongoing=True)
    assert ongoing.ended_at is None
    assert context(started_at=at(1), ended_at=at(1), ongoing=False).ended_at == at(1)
    normalized = context(started_at="2026-01-01T14:00:00+02:00")
    assert normalized.started_at == at(1)


@pytest.mark.parametrize("field", ["started_at", "ended_at"])
def test_source_cannot_claim_future_activity_dates(field: str) -> None:
    with pytest.raises(ValidationError, match="source collection"):
        record(experience_context=context(**{field: at(21)}))
    assert record(experience_context=context(**{field: at(20)})).experience_context is not None


def test_context_is_only_for_experience_and_does_not_recalculate_scalar_months() -> None:
    metadata = context(started_at=at(1), ended_at=at(2), ongoing=False)
    source = record(experience_context=metadata)
    assert (
        source.assertion.value == 6
    )  # Source statement, never inferred from this one-day interval.
    with pytest.raises(ValidationError, match="experience assertion"):
        record(
            assertion=Assertion(kind="skill", subject="python", unit="skill_level", value=2),
            experience_context=metadata,
        )


def test_metadata_changes_invalidate_source_review_and_dependency_identity() -> None:
    original = record()
    review = EvidenceReview(
        reviewer_id=ActorId("actor_" + "4" * 32),
        kind="synthetic_review",
        method="Fabricated source scope review",
        reviewed_at=at(21),
        content_digest=original.content_digest,
    )
    original = original.model_copy(update={"review": review})
    with pytest.raises(ValidationError, match="current source content"):
        original.model_copy(update={"experience_context": context()})
    proposed = original.model_copy(update={"experience_context": context(), "review": None})
    assert proposed.content_digest != original.content_digest
    assert evidence_ref(proposed) != evidence_ref(original)
    assert not proposed.qualifies_support
    renewed = proposed.model_copy(
        update={"review": review.model_copy(update={"content_digest": proposed.content_digest})}
    )
    assert renewed._qualifies_review
    assert not renewed.qualifies_support
    for changes in (
        {"category": "professional_employment"},
        {"started_at": at(1)},
        {"ongoing": True},
    ):
        with pytest.raises(ValidationError):
            renewed.model_copy(update={"experience_context": context(**changes)})


def test_absent_extension_preserves_legacy_wire_and_source_review_binding() -> None:
    source = record()
    assert "experience_context" not in source.model_dump(mode="json")
    assert b"experience_context" not in canonical_bytes(source)
    assert source.model_copy(update={"experience_context": None}) == source
    assert load_contract(EvidenceRecord, canonical_bytes(source)) == source
