"""Controlled factual units. Free claim/CV prose is never certified or copied."""

from actual.career.jobs import Job
from actual.career.materials import CVVariant, Draft, DraftAssertion
from actual.career.preparation_context import MaterialKind
from actual.core.primitives import content_digest
from actual.profile.contracts import Assertion, Profile, supports_assertion
from actual.profile.projection import project_evidence


def fact_text(assertion: Assertion) -> str:
    if assertion.kind == "skill":
        return f"{assertion.subject}: supported skill unit {assertion.value}/3."
    if assertion.kind == "language":
        levels = ("unspecified", "A1", "A2", "B1", "B2", "C1", "C2")
        return f"{assertion.subject}: supported language unit {levels[assertion.value]}."
    return (
        f"Experience: {assertion.value} months in an unscoped legacy record; "
        "employment category and dates are unspecified."
    )


def units(profile: Profile, cv: CVVariant) -> tuple[DraftAssertion, ...]:
    claims = {claim.id: claim for claim in profile.claims}
    conflicted = {
        group.scope for group in project_evidence(profile).groups if group.contrary_evidence
    }
    selected: list[DraftAssertion] = []
    for reference in cv.claim_refs:
        claim = claims[reference.claim_id]
        scope = (claim.assertion.kind, claim.assertion.subject, claim.assertion.unit)
        if (
            claim.assertion.value > 0
            and scope not in conflicted
            and supports_assertion(profile, claim.assertion, (reference,))
        ):
            selected.append(
                DraftAssertion(
                    assertion=claim.assertion,
                    text=fact_text(claim.assertion),
                    source_claim_refs=(reference,),
                )
            )
    return tuple(selected)


def heading(kind: MaterialKind, job: Job) -> str:
    # Quoted posting metadata, never a candidate factual assertion.
    title = f'Advertised role (source title): "{job.title}".'
    if kind == "cv_adaptation":
        return f"CV adaptation suggestion. {title} Include only the source-linked units below."
    if kind == "application_message":
        return f"Please consider my application. {title} My source-linked units follow."
    return (
        f"Dear hiring team, please consider my application. {title} My source-linked units follow."
    )


def validate_material(draft: Draft, job: Job, cv: CVVariant, profile: Profile) -> None:
    context = draft.preparation
    if context is None:
        return
    if (
        context.job.object_id != job.id
        or context.job.revision != job.revision
        or context.job.content_digest != content_digest(job.model_dump(mode="json"))
        or context.cv.object_id != cv.id
        or context.cv.revision != cv.revision
        or context.cv.content_digest != cv.content_digest
    ):
        raise ValueError("Preparation source is missing or stale")
    # Validate every prepared revision, including unreviewed/rejected content.
    if draft.summary != heading(context.material_kind, job) or draft.assertions != units(
        profile, cv
    ):
        raise ValueError("Prepared prose/units differ from the supported controlled template")
