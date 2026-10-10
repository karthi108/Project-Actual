"""Job Intelligence uses admitted evidence groups, never optimistic tenure."""

from unittest.mock import patch

import pytest
from test_evidence_matching import ACTOR, assessed, at, candidate, source_job

from actual.profile.contracts import EvidenceReview, Profile, evidence_ref
from actual.profile.experience import ExperienceContext
from actual.profile.projection import project_evidence


def test_matcher_uses_one_validated_projection_for_current_candidate() -> None:
    profile = candidate()
    with patch(
        "actual.job_intelligence.matching.project_evidence", wraps=project_evidence
    ) as boundary:
        result = assessed(source_job(), profile)
    boundary.assert_called_once_with(profile)
    assert result.rows[0].status == "supported"
    assert result.profile_digest == project_evidence(profile).profile_digest


@pytest.mark.parametrize("category", ["internship", "personal_project", "professional_employment"])
def test_source_reviewed_duration_cannot_satisfy_unscoped_experience(category: str) -> None:
    original = candidate(60, kind="experience", subject="experience", unit="months", reviewed=False)
    source = original.evidence[0].model_copy(
        update={
            "experience_context": ExperienceContext.model_validate(
                {
                    "context_version": "actual-experience-context-v1",
                    "category": category,
                }
            )
        }
    )
    source = source.model_copy(
        update={
            "review": EvidenceReview(
                reviewer_id=ACTOR,
                kind="synthetic_review",
                method="Synthetic context source review",
                reviewed_at=at(3),
                content_digest=source.content_digest,
            )
        }
    )
    claim = original.claims[0].model_copy(update={"evidence_refs": (evidence_ref(source),)})
    profile = Profile.model_validate(
        original.model_copy(update={"claims": (claim,), "evidence": (source,)})
    )
    row = assessed(
        source_job("Five years of experience are essential."), profile, "experience"
    ).rows[0]
    assert source._qualifies_review and not source.qualifies_support
    assert row.status == "unknown" and row.observed_value is None
