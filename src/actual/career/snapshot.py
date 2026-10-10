"""Validate related career records against an explicit owner-scoped snapshot."""

from typing import Annotated, Self

from pydantic import Field, model_validator

from actual.core.primitives import (
    Classification,
    Contract,
    Instant,
    JobId,
    WorkspaceId,
    classification_allows,
)
from actual.core.references import ClaimRef
from actual.profile.contracts import Profile, supports_assertion

from .applications import Application
from .jobs import Company, Job, Requirement
from .materials import CVVariant, Draft


class CareerSnapshot(Contract):
    workspace_id: WorkspaceId
    classification: Classification
    as_of: Instant
    companies: Annotated[tuple[Company, ...], Field(min_length=1, max_length=128)]
    jobs: Annotated[tuple[Job, ...], Field(min_length=1, max_length=128)]
    profile: Profile
    cvs: Annotated[tuple[CVVariant, ...], Field(max_length=128)] = ()
    drafts: Annotated[tuple[Draft, ...], Field(max_length=128)] = ()
    applications: Annotated[tuple[Application, ...], Field(max_length=128)] = ()
    requirements: Annotated[tuple[Requirement, ...], Field(max_length=128)] = ()

    @model_validator(mode="after")
    def related_records(self) -> Self:
        records: tuple[
            Company | Job | Profile | CVVariant | Draft | Application | Requirement, ...
        ] = (
            *self.companies,
            *self.jobs,
            self.profile,
            *self.cvs,
            *self.drafts,
            *self.applications,
            *self.requirements,
        )
        identities = [record.id for record in records]
        if len(set(identities)) != len(identities):
            raise ValueError("Duplicate career object identity")
        if any(record.workspace_id != self.workspace_id for record in records):
            raise ValueError("Cross-workspace career object")
        if any(
            not classification_allows(self.classification, record.classification)
            for record in records
        ):
            raise ValueError("Snapshot classification cannot understate or mix synthetic data")
        companies = {company.id for company in self.companies}
        jobs = {job.id: job for job in self.jobs}
        for job in self.jobs:
            if job.company_id not in companies or job.posted_at > self.as_of:
                raise ValueError("Missing job company or future posting")
        opportunities: dict[object, tuple[object, str, str]] = {}
        for job in self.jobs:
            content = (job.company_id, job.title, job.text)
            if opportunities.setdefault(job.opportunity_id, content) != content:
                raise ValueError("Opportunity aliases contain conflicting source text")
        claims = {claim.id: claim for claim in self.profile.claims}

        def check_claim(reference: ClaimRef) -> None:
            claim = claims.get(reference.claim_id)
            if (
                claim is None
                or reference.workspace_id != self.workspace_id
                or reference.profile_id != self.profile.id
                or reference.revision != claim.revision
                or reference.content_digest != claim.snapshot_digest
                or reference.classification != claim.classification
            ):
                raise ValueError("Missing, foreign or stale claim reference")

        for cv in self.cvs:
            if cv.profile_id != self.profile.id:
                raise ValueError("CV belongs to another profile")
            for reference in cv.claim_refs:
                check_claim(reference)
                if not classification_allows(cv.classification, reference.classification):
                    raise ValueError("CV understates its source claim classification")
        for draft in self.drafts:
            if draft.profile_id != self.profile.id:
                raise ValueError("Draft belongs to another profile")
            if draft.preparation is not None:
                from actual.preparation.render import validate_material

                source_job = jobs.get(JobId(draft.preparation.job.object_id.root))
                source_cv = next(
                    (item for item in self.cvs if item.id == draft.preparation.cv.object_id), None
                )
                if source_job is None or source_cv is None:
                    raise ValueError("Missing preparation source")
                validate_material(draft, source_job, source_cv, self.profile)
            for proposal in draft.assertions:
                for reference in proposal.source_claim_refs:
                    check_claim(reference)
                    if not classification_allows(draft.classification, reference.classification):
                        raise ValueError("Draft understates its source claim classification")
            if draft.review is not None:
                if draft.review.reviewed_at > self.as_of:
                    raise ValueError("Future draft review")
                if draft.review.decision == "accepted" and any(
                    not supports_assertion(
                        self.profile, proposal.assertion, proposal.source_claim_refs
                    )
                    for proposal in draft.assertions
                ):
                    raise ValueError("Accepted structured draft contains unsupported units")
                if draft.review.decision == "accepted":
                    for proposal in draft.assertions:
                        available: list[ClaimRef] = []
                        for reference in proposal.source_claim_refs:
                            source_review = claims[reference.claim_id].review
                            if (
                                source_review is not None
                                and source_review.reviewed_at <= draft.review.reviewed_at
                            ):
                                available.append(reference)
                        if not supports_assertion(
                            self.profile, proposal.assertion, tuple(available)
                        ):
                            raise ValueError("Draft review precedes its scoped claim support")
        application_intents: set[tuple[object, object]] = set()
        for app in self.applications:
            if app.job_id not in jobs or app.profile_id != self.profile.id:
                raise ValueError("Application has missing job or foreign profile")
            intent = (app.profile_id, jobs[app.job_id].opportunity_id)
            if intent in application_intents:
                raise ValueError("Duplicate application for one profile/canonical opportunity")
            application_intents.add(intent)
            if app.history[0].occurred_at < jobs[app.job_id].posted_at or any(
                item.occurred_at > self.as_of or item.recorded_at > self.as_of
                for item in app.history
            ):
                raise ValueError("Application observation outside source/snapshot timeline")
        units: set[tuple[object, str]] = set()
        for requirement in self.requirements:
            source_job = jobs.get(requirement.job_id)
            if (
                source_job is None
                or source_job.revision != requirement.job_revision
                or source_job.content_digest != requirement.job_digest
            ):
                raise ValueError("Requirement cites missing or stale job revision")
            if not classification_allows(requirement.classification, source_job.classification):
                raise ValueError("Requirement understates its source job classification")
            if (
                requirement.source_end > len(source_job.text)
                or source_job.text[requirement.source_start : requirement.source_end]
                != requirement.source_quote
            ):
                raise ValueError("Requirement source span/quote differs from job")
            unit = (source_job.opportunity_id, requirement.assertion.subject)
            if unit in units:
                raise ValueError("Repeated normalized requirement for canonical opportunity")
            units.add(unit)
            if requirement.review is not None and requirement.review.reviewed_at > self.as_of:
                raise ValueError("Future requirement review")
            if (
                requirement.review is not None
                and requirement.review.reviewed_at < source_job.posted_at
            ):
                raise ValueError("Requirement review precedes posting")
        for evidence in self.profile.evidence:
            if evidence.collected_at > self.as_of or (
                evidence.review is not None and evidence.review.reviewed_at > self.as_of
            ):
                raise ValueError("Future evidence observation/review")
        for claim in self.profile.claims:
            if (claim.asserted_at is not None and claim.asserted_at > self.as_of) or (
                claim.review is not None and claim.review.reviewed_at > self.as_of
            ):
                raise ValueError("Future claim assertion/review")
        return self
