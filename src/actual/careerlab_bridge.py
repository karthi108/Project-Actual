"""Synthetic compatibility adapter. Takes observable facts, never evaluator data.

This is not a real-profile importer or an evidence-verification service.
"""

from datetime import datetime
from typing import Literal
from uuid import UUID, uuid5

from actual.career.applications import Application, StatusObservation
from actual.career.jobs import Company, Job
from actual.career.materials import CVVariant, Draft, DraftAssertion
from actual.career.snapshot import CareerSnapshot
from actual.careerlab.codec import load_record
from actual.careerlab.contracts import ScenarioInput
from actual.careerlab.validation import validate_input
from actual.core.primitives import (
    ActorId,
    ApplicationId,
    ClaimId,
    CompanyId,
    Contract,
    CVId,
    DraftId,
    EvidenceId,
    Identifier,
    JobId,
    OpportunityId,
    ProfileId,
    WorkspaceId,
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
)

_NAMESPACE = UUID("823f0b78-29ca-4b1f-81e7-cd9c8d904f98")


class ImportContext(Contract):
    workspace_id: WorkspaceId
    actor_id: ActorId


def map_observable(value: ScenarioInput, context: ImportContext) -> CareerSnapshot:
    if type(value) is not ScenarioInput:
        raise TypeError("Only a CareerLab observable input is accepted")
    checked = ImportContext.model_validate(context)
    violations = validate_input(value)
    if violations:
        raise ValueError(f"Invalid observable fixture: {[item.code for item in violations]}")

    def identity[T: Identifier](kind: type[T], source: str) -> T:
        key = f"{checked.workspace_id.root}/{value.id}/{kind.prefix}/{source}"
        return kind(f"{kind.prefix}_{uuid5(_NAMESPACE, key).hex}")

    def assertion(subject: str, unit: str, number: int) -> Assertion:
        return Assertion.model_validate(
            {
                "kind": {"skill_level": "skill", "cefr_level": "language", "months": "experience"}[
                    unit
                ],
                "subject": subject,
                "unit": unit,
                "value": number,
            }
        )

    profile_id = identity(ProfileId, value.candidate.id)
    evidence: list[EvidenceRecord] = []
    source_kinds: dict[str, Literal["user_report", "project_artifact", "imported_document"]] = {
        "self_report": "user_report",
        "project_review": "project_artifact",
        "document_review": "imported_document",
    }
    for item in value.candidate.evidence:
        record = EvidenceRecord(
            id=identity(EvidenceId, item.id),
            workspace_id=checked.workspace_id,
            profile_id=profile_id,
            revision=1,
            classification="synthetic",
            assertion=assertion(item.subject, item.unit, item.value),
            relation=item.relation,
            excerpt=item.excerpt,
            source_kind=source_kinds[item.source_kind],
            source_reference=f"careerlab:{value.id}:{item.id}:retained-excerpt",
            collected_at=datetime.fromisoformat(item.observed_at),
            review=None,
        )
        if item.source_kind != "self_report" and item.reviewer is not None:
            assert item.review_method is not None and item.reviewed_at is not None
            review = EvidenceReview(
                reviewer_id=identity(ActorId, item.reviewer),
                kind="synthetic_review",
                method=item.review_method,
                reviewed_at=datetime.fromisoformat(item.reviewed_at),
                content_digest=record.content_digest,
            )
            record = record.model_copy(update={"review": review})
        evidence.append(record)
    evidence_by_source = dict(
        zip((item.id for item in value.candidate.evidence), evidence, strict=True)
    )
    claims: list[Claim] = []
    for source_claim in value.candidate.claims:
        refs = tuple(
            evidence_ref(evidence_by_source[source]) for source in source_claim.evidence_ids
        )
        # Reconstruct only recorded synthetic support; no original assertion time/actor
        # or independent verification is invented where the fixture omits it.
        mapped_claim = Claim(
            id=identity(ClaimId, source_claim.id),
            workspace_id=checked.workspace_id,
            profile_id=profile_id,
            revision=1,
            classification="synthetic",
            assertion=assertion(source_claim.subject, source_claim.unit, source_claim.value),
            text=source_claim.text,
            origin="synthetic_fixture",
            asserted_by=None,
            asserted_at=None,
            status="candidate_support"
            if source_claim.status == "reviewed_supported"
            else source_claim.status,
            evidence_refs=refs,
            review=None,
        )
        if source_claim.status == "reviewed_supported":
            reviews = [
                evidence_by_source[source].review
                for source in source_claim.evidence_ids
                if evidence_by_source[source].qualifies_support
            ]
            scoped = [review for review in reviews if review is not None]
            if not scoped:
                raise ValueError("Recorded synthetic supported claim lacks reviewed source")
            latest = max(scoped, key=lambda review: review.reviewed_at)
            claim_review = ContentReview(
                revision=1,
                content_digest=mapped_claim.content_digest,
                reviewer_id=latest.reviewer_id,
                reviewed_at=latest.reviewed_at,
                method="synthetic_fixture_import",
                decision="accepted",
            )
            mapped_claim = mapped_claim.model_copy(
                update={"status": source_claim.status, "review": claim_review}
            )
        claims.append(mapped_claim)
    profile = Profile(
        id=profile_id,
        workspace_id=checked.workspace_id,
        revision=1,
        classification="synthetic",
        name=value.candidate.name,
        claims=tuple(claims),
        evidence=tuple(evidence),
    )
    claim_by_source = dict(zip((item.id for item in value.candidate.claims), claims, strict=True))
    companies = tuple(
        Company(
            id=identity(CompanyId, item.id),
            workspace_id=checked.workspace_id,
            revision=1,
            classification="synthetic",
            name=item.name,
            context=item.context,
        )
        for item in value.companies
    )
    jobs = tuple(
        Job(
            id=identity(JobId, item.id),
            workspace_id=checked.workspace_id,
            revision=1,
            classification="synthetic",
            company_id=identity(CompanyId, item.company_id),
            opportunity_id=identity(OpportunityId, item.canonical_opportunity),
            title=item.title,
            text=item.text,
            source_reference=item.source_reference,
            posted_at=datetime.fromisoformat(item.posted_at),
            decision="new",
        )
        for item in value.jobs
    )
    cvs = tuple(
        CVVariant(
            id=identity(CVId, item.id),
            workspace_id=checked.workspace_id,
            profile_id=profile_id,
            revision=1,
            classification="synthetic",
            name=item.name,
            summary=item.summary,
            claim_refs=tuple(claim_ref(claim_by_source[source]) for source in item.claim_ids),
        )
        for item in value.cvs
    )
    drafts = tuple(
        Draft(
            id=identity(DraftId, item.id),
            workspace_id=checked.workspace_id,
            profile_id=profile_id,
            revision=1,
            classification="synthetic",
            name="Imported synthetic proposal",
            summary=item.text,
            assertions=(
                DraftAssertion(
                    assertion=assertion(item.subject, item.unit, item.value),
                    text=item.text,
                    source_claim_refs=tuple(
                        claim_ref(claim_by_source[source]) for source in item.source_claim_ids
                    ),
                ),
            ),
            review=None,
        )
        for item in value.draft_assertions
    )
    applications = tuple(
        Application(
            id=identity(ApplicationId, item.id),
            workspace_id=checked.workspace_id,
            revision=1,
            classification="synthetic",
            job_id=identity(JobId, item.job_id),
            profile_id=profile_id,
            state=item.state,
            history=tuple(
                StatusObservation(
                    actor_id=checked.actor_id,
                    state=entry.state,
                    basis="synthetic_observation",
                    occurred_at=datetime.fromisoformat(entry.occurred_at),
                    recorded_at=datetime.fromisoformat(entry.recorded_at),
                )
                for entry in item.history
            ),
        )
        for item in value.applications
    )
    return CareerSnapshot(
        workspace_id=checked.workspace_id,
        classification="synthetic",
        as_of=datetime.fromisoformat(value.as_of),
        companies=companies,
        jobs=jobs,
        profile=profile,
        cvs=cvs,
        drafts=drafts,
        applications=applications,
        requirements=(),
    )


def load_observable(payload: bytes, context: ImportContext) -> CareerSnapshot:
    if type(payload) is not bytes or len(payload) > 2_000_000:
        raise ValueError("Bounded observable JSON bytes required")
    return map_observable(load_record(ScenarioInput, payload), context)
