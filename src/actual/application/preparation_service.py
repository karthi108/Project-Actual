"""Preparation use cases reuse the accepted aggregate/concurrency boundary."""

from uuid import uuid4

from actual.career.events import DraftReviewed, WorkEvent
from actual.career.materials import CVVariant, Draft
from actual.career.preparation_context import PreparationContext
from actual.core.primitives import DraftId, EventId, content_digest
from actual.core.references import BusinessObjectRef
from actual.core.workflow import ContentReview
from actual.job_intelligence.errors import IntelligenceFailure
from actual.preparation.comparison import CVComparison, compare
from actual.preparation.render import heading, units
from actual.profile.contracts import claim_ref

from .errors import UseCaseCode, UseCaseError
from .ports import CareerState
from .preparation_commands import CompareCVs, CreateCV, PrepareDraft, ReviewDraft, ReviseDraft
from .service import CareerService, _command, _domain_input


class PreparationService(CareerService):
    def create_cv(self, command: CreateCV) -> CareerState:
        command = _command(CreateCV, command)
        state = self._mutation(command.expected_generation)
        snapshot = state.snapshot
        if any(item.id == command.id for item in snapshot.cvs):
            raise UseCaseError(UseCaseCode.DUPLICATE_RESOURCE)
        if len(set(command.claim_ids)) != len(command.claim_ids):
            raise UseCaseError(UseCaseCode.INVALID_DOMAIN_INPUT)
        claims = {claim.id: claim for claim in snapshot.profile.claims}
        if any(identifier not in claims for identifier in command.claim_ids):
            raise UseCaseError(UseCaseCode.RESOURCE_NOT_FOUND)
        with _domain_input():
            cv = CVVariant(
                id=command.id,
                workspace_id=self.workspace_id,
                profile_id=snapshot.profile.id,
                revision=1,
                classification="synthetic",
                name=command.name,
                summary="Synthetic claim selection; free prose is not certified for preparation.",
                claim_refs=tuple(claim_ref(claims[identifier]) for identifier in command.claim_ids),
            )
            changed = snapshot.model_copy(
                update={"as_of": self._now(snapshot), "cvs": (*snapshot.cvs, cv)}
            )
        return self._save(changed, state.generation)

    def compare_cvs(self, command: CompareCVs) -> CVComparison:
        command = _command(CompareCVs, command)
        state = self._mutation(command.expected_generation)
        if not any(job.id == command.job_id for job in state.snapshot.jobs):
            raise UseCaseError(UseCaseCode.RESOURCE_NOT_FOUND)
        try:
            with _domain_input():
                return compare(state.snapshot, state.generation, command)
        except IntelligenceFailure:
            raise UseCaseError(UseCaseCode.INVALID_DOMAIN_INPUT) from None

    def _prepared(
        self,
        state: CareerState,
        identifier: DraftId,
        revision: int,
        command: PrepareDraft | ReviseDraft,
    ) -> Draft:
        snapshot = state.snapshot
        job = next((item for item in snapshot.jobs if item.id == command.job_id), None)
        cv = next((item for item in snapshot.cvs if item.id == command.cv_id), None)
        if job is None or cv is None:
            raise UseCaseError(UseCaseCode.RESOURCE_NOT_FOUND)
        with _domain_input():
            job_ref = self._reference(job, "job")
            cv_ref = BusinessObjectRef(
                workspace_id=self.workspace_id,
                classification="synthetic",
                kind="cv",
                object_id=cv.id,
                revision=cv.revision,
                content_digest=cv.content_digest,
            )
            return Draft(
                id=identifier,
                workspace_id=self.workspace_id,
                profile_id=snapshot.profile.id,
                revision=revision,
                classification="synthetic",
                name="Synthetic prepared material",
                summary=heading(command.material_kind, job),
                assertions=units(snapshot.profile, cv),
                preparation=PreparationContext(
                    material_kind=command.material_kind, job=job_ref, cv=cv_ref
                ),
            )
        raise AssertionError("Preparation returns or raises")

    def prepare(self, command: PrepareDraft) -> CareerState:
        command = _command(PrepareDraft, command)
        state = self._mutation(command.expected_generation)
        if any(item.id == command.id for item in state.snapshot.drafts):
            raise UseCaseError(UseCaseCode.DUPLICATE_RESOURCE)
        draft = self._prepared(state, command.id, 1, command)
        with _domain_input():
            changed = state.snapshot.model_copy(
                update={
                    "as_of": self._now(state.snapshot),
                    "drafts": (*state.snapshot.drafts, draft),
                }
            )
        return self._save(changed, state.generation)

    def _draft_pin(
        self, state: CareerState, identifier: DraftId, command: ReviseDraft | ReviewDraft
    ) -> Draft:
        with _domain_input():
            identifier = DraftId.model_validate(identifier, strict=True)
        draft = next((item for item in state.snapshot.drafts if item.id == identifier), None)
        if draft is None:
            raise UseCaseError(UseCaseCode.RESOURCE_NOT_FOUND)
        if draft.preparation is None:
            raise UseCaseError(UseCaseCode.DEPENDENCY_RECONCILIATION_REQUIRED)
        if (draft.revision, draft.content_digest) != (
            command.expected_revision,
            command.expected_digest,
        ):
            raise UseCaseError(UseCaseCode.STATE_CONFLICT)
        return draft

    def revise(self, identifier: DraftId, command: ReviseDraft) -> CareerState:
        command = _command(ReviseDraft, command)
        state = self._mutation(command.expected_generation)
        old = self._draft_pin(state, identifier, command)
        draft = self._prepared(state, old.id, old.revision + 1, command)
        with _domain_input():
            changed = state.snapshot.model_copy(
                update={
                    "as_of": self._now(state.snapshot),
                    "drafts": tuple(
                        draft if item.id == old.id else item for item in state.snapshot.drafts
                    ),
                }
            )
        return self._save(changed, state.generation)

    def review(self, identifier: DraftId, command: ReviewDraft) -> CareerState:
        command = _command(ReviewDraft, command)
        state = self._mutation(command.expected_generation)
        draft = self._draft_pin(state, identifier, command)
        if draft.review is not None:
            raise UseCaseError(UseCaseCode.STATE_CONFLICT)
        if command.decision == "accepted" and not draft.assertions:
            raise UseCaseError(UseCaseCode.INVALID_DOMAIN_INPUT)
        now = self._now(state.snapshot)
        with _domain_input():
            # The accepted store versions every changed record, including review metadata.
            review_revision = draft.model_copy(update={"revision": draft.revision + 1})
            reviewed = review_revision.model_copy(
                update={
                    "review": ContentReview(
                        revision=review_revision.revision,
                        content_digest=review_revision.content_digest,
                        reviewer_id=self.actor_id,
                        reviewed_at=now,
                        method="synthetic-preparation-content-review-v1",
                        decision=command.decision,
                    )
                }
            )
            changed = state.snapshot.model_copy(
                update={
                    "as_of": now,
                    "drafts": tuple(
                        reviewed if item.id == draft.id else item for item in state.snapshot.drafts
                    ),
                }
            )
            reference = BusinessObjectRef(
                workspace_id=self.workspace_id,
                classification="synthetic",
                kind="draft",
                object_id=reviewed.id,
                revision=reviewed.revision,
                content_digest=content_digest(reviewed.model_dump(mode="json")),
            )
            event = WorkEvent(
                event_id=EventId("event_" + uuid4().hex),
                workspace_id=self.workspace_id,
                actor_id=self.actor_id,
                occurred_at=now,
                recorded_at=now,
                source="manual",
                business_objects=(reference,),
                evidence_refs=tuple(
                    sorted(
                        {
                            ref
                            for unit in draft.assertions
                            for claim_ref in unit.source_claim_refs
                            for claim in state.snapshot.profile.claims
                            if claim.id == claim_ref.claim_id
                            for ref in claim.evidence_refs
                        },
                        key=lambda ref: ref.evidence_id.root,
                    )
                ),
                privacy_classification="synthetic",
                activity="draft_reviewed",
                payload=DraftReviewed(
                    draft=reference,
                    decision=command.decision,
                    reviewer_id=self.actor_id,
                    reviewed_at=now,
                ),
            )
        return self._save(changed, state.generation, (event,))
