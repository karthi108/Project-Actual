"""Source-derived classification and reference catalog checks use fabricated facts."""

import pytest
from pydantic import ValidationError
from test_compatibility import context, requirement, snapshot

from actual.career.snapshot import CareerSnapshot
from actual.profile.contracts import Profile


def test_requirement_cannot_copy_sensitive_source_into_personal_record() -> None:
    source = snapshot()
    # Fabricated source text is tagged real-classified solely to test privacy policy.
    profile = Profile(
        id=source.profile.id,
        workspace_id=source.workspace_id,
        revision=1,
        classification="personal",
        name="Fabricated privacy test profile",
    )
    job = source.jobs[0].model_copy(update={"classification": "sensitive"})
    value = CareerSnapshot(
        workspace_id=context().workspace_id,
        classification="sensitive",
        as_of=source.as_of,
        companies=tuple(
            c.model_copy(update={"classification": "personal"}) for c in source.companies
        ),
        jobs=(job,),
        profile=profile,
    )
    proposed = requirement(source).model_copy(
        update={"classification": "personal", "job_digest": job.content_digest}
    )
    with pytest.raises(ValidationError, match="understates"):
        value.model_copy(update={"requirements": (proposed,)})
    sensitive = proposed.model_copy(update={"classification": "sensitive"})
    value.model_copy(update={"requirements": (sensitive,)})
