"""Career intents become immutable synthetic records and one atomic save.

The repository owns its transaction and final optimistic-concurrency check.
These use cases never retry a conflicting mutation or manufacture review state.
"""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from pydantic import TypeAdapter, ValidationError

from actual.career.applications import Application, StatusObservation, allowed_transition
from actual.career.events import ApplicationStatusRecorded, JobAdded, WorkEvent
from actual.career.jobs import Company, Job
from actual.career.snapshot import CareerSnapshot
from actual.core.primitives import (
    ActorId,
    ApplicationId,
    ClaimId,
    EventId,
    EvidenceId,
    Instant,
    JobId,
    WorkspaceId,
    canonical_bytes,
    content_digest,
)
from actual.core.references import BusinessObjectRef
from actual.core.workflow import ContentReview
from actual.profile.contracts import Claim, EvidenceRecord, EvidenceReview, Profile, evidence_ref
from actual.profile.projection import EvidenceBackedProfileView, evidence_backed_profile

from .commands import (
    AddJob,
    AttachEvidence,
    Command,
    CreateApplication,
    CreateClaim,
    InitializeCareer,
    ManualJob,
    TransitionApplication,
)
from .errors import UseCaseCode, UseCaseError
from .ports import CareerRepository, CareerState
from .profile_commands import (
    ProfileRevisionCommand,
    ReviewSyntheticClaim,
    ReviewSyntheticEvidence,
    WithdrawEvidence,
)

_INSTANT: TypeAdapter[datetime] = TypeAdapter(Instant)


@contextmanager
def _domain_input() -> Iterator[None]:
    """Translate validation failures without retaining unsafe validation messages."""
    try:
        yield
    except (ValidationError, ValueError, TypeError, OverflowError):
        raise UseCaseError(UseCaseCode.INVALID_DOMAIN_INPUT) from None


def _command[T: Command](kind: type[T], value: T) -> T:
    with _domain_input():
        return kind.model_validate(value, strict=True, extra="forbid")
    raise AssertionError("Validation must return or raise")


def _current_time() -> datetime:
    return datetime.now(UTC)


class CareerService:
    def __init__(
        self,
        repository: CareerRepository,
        workspace_id: WorkspaceId,
        actor_id: ActorId,
        clock: Callable[[], datetime] = _current_time,
    ) -> None:
        self._repository = repository
        self.workspace_id = WorkspaceId.model_validate(workspace_id, strict=True)
        self.actor_id = ActorId.model_validate(actor_id, strict=True)
        self._clock = clock

    def _checked_state(self, state: CareerState) -> CareerState:
        with _domain_input():
            snapshot = CareerSnapshot.model_validate(state.snapshot)
            canonical_bytes(snapshot)
        if snapshot.workspace_id != self.workspace_id:
            raise UseCaseError(UseCaseCode.STATE_CONFLICT)
        if snapshot.classification != "synthetic":
            raise UseCaseError(UseCaseCode.SYNTHETIC_ONLY)
        if type(state.generation) is not int or not 1 <= state.generation <= 9223372036854775807:
            raise UseCaseError(UseCaseCode.STATE_CONFLICT)
        return CareerState(snapshot=snapshot, generation=state.generation)

    def get_state(self) -> CareerState:
        state = self._repository.load()
        if state is None:
            raise UseCaseError(UseCaseCode.RESOURCE_NOT_FOUND)
        return self._checked_state(state)

    def evidence_profile(self) -> tuple[CareerState, EvidenceBackedProfileView]:
        state = self.get_state()
        with _domain_input():
            view = evidence_backed_profile(state.snapshot.profile, as_of=state.snapshot.as_of)
        return state, view

    def job(self, job_id: JobId) -> tuple[CareerState, Job]:
        with _domain_input():
            job_id = JobId.model_validate(job_id, strict=True)
        state = self.get_state()
        job = next((job for job in state.snapshot.jobs if job.id == job_id), None)
        if job is None:
            raise UseCaseError(UseCaseCode.RESOURCE_NOT_FOUND)
        return state, job

    def application(self, application_id: ApplicationId) -> tuple[CareerState, Application]:
        with _domain_input():
            application_id = ApplicationId.model_validate(application_id, strict=True)
        state = self.get_state()
        application = next(
            (item for item in state.snapshot.applications if item.id == application_id), None
        )
        if application is None:
            raise UseCaseError(UseCaseCode.RESOURCE_NOT_FOUND)
        return state, application

    def events(self) -> tuple[WorkEvent, ...]:
        self.get_state()
        events = self._repository.load_events()
        if type(events) is not tuple:
            raise UseCaseError(UseCaseCode.STATE_CONFLICT)
        with _domain_input():
            checked = tuple(WorkEvent.model_validate(event) for event in events)
        if any(event.workspace_id != self.workspace_id for event in checked):
            raise UseCaseError(UseCaseCode.STATE_CONFLICT)
        if any(event.privacy_classification != "synthetic" for event in checked):
            raise UseCaseError(UseCaseCode.SYNTHETIC_ONLY)
        return checked

    def _now(self, snapshot: CareerSnapshot | None = None) -> datetime:
        with _domain_input():
            now = _INSTANT.validate_python(self._clock())
        if snapshot is not None and now < snapshot.as_of:
            raise UseCaseError(UseCaseCode.INVALID_DOMAIN_INPUT)
        return now

    def _mutation(self, expected_generation: int) -> CareerState:
        state = self.get_state()
        if state.generation != expected_generation:
            raise UseCaseError(UseCaseCode.STALE_GENERATION)
        return state

    def _save(
        self,
        snapshot: CareerSnapshot,
        generation: int,
        events: tuple[WorkEvent, ...] = (),
    ) -> CareerState:
        with _domain_input():
            checked = CareerSnapshot.model_validate(snapshot)
            canonical_bytes(checked)
        # The port's save atomically commits the whole aggregate and observations.
        result = self._repository.save(checked, expected_generation=generation, events=events)
        return self._checked_state(result)

    def _company(self, job: ManualJob) -> Company:
        return Company(
            id=job.company.id,
            workspace_id=self.workspace_id,
            revision=1,
            classification="synthetic",
            name=job.company.name,
            context=job.company.context,
        )

    def _job(self, job: ManualJob) -> Job:
        return Job(
            id=job.id,
            workspace_id=self.workspace_id,
            revision=1,
            classification="synthetic",
            company_id=job.company.id,
            opportunity_id=job.opportunity_id,
            title=job.title,
            text=job.text,
            source_reference=job.source_reference,
            posted_at=job.posted_at,
            decision="new",
        )

    def _reference(
        self, record: Job | Application, kind: Literal["job", "application"]
    ) -> BusinessObjectRef:
        # Phase-3 catalogs bind the full canonical record, including status/history.
        return BusinessObjectRef(
            workspace_id=self.workspace_id,
            classification="synthetic",
            kind=kind,
            object_id=record.id,
            revision=record.revision,
            content_digest=content_digest(record.model_dump(mode="json")),
        )

    def _event(
        self,
        payload: JobAdded | ApplicationStatusRecorded,
        occurred_at: datetime,
        recorded_at: datetime,
    ) -> WorkEvent:
        reference = payload.job if isinstance(payload, JobAdded) else payload.application
        return WorkEvent(
            event_id=EventId("event_" + uuid4().hex),
            workspace_id=self.workspace_id,
            actor_id=self.actor_id,
            occurred_at=occurred_at,
            recorded_at=recorded_at,
            source="manual",
            business_objects=(reference,),
            privacy_classification="synthetic",
            activity=payload.activity,
            payload=payload,
        )

    def initialize(self, command: InitializeCareer) -> CareerState:
        command = _command(InitializeCareer, command)
        existing = self._repository.load()
        if existing is not None:
            self._checked_state(existing)
            raise UseCaseError(UseCaseCode.STATE_CONFLICT)
        now = self._now()
        with _domain_input():
            job = self._job(command.job)
            snapshot = CareerSnapshot(
                workspace_id=self.workspace_id,
                classification="synthetic",
                as_of=now,
                companies=(self._company(command.job),),
                jobs=(job,),
                profile=Profile(
                    id=command.profile.id,
                    workspace_id=self.workspace_id,
                    revision=1,
                    classification="synthetic",
                    name=command.profile.name,
                ),
            )
            event = self._event(JobAdded(job=self._reference(job, "job")), now, now)
        return self._save(snapshot, command.expected_generation, (event,))

    def add_job(self, command: AddJob) -> CareerState:
        command = _command(AddJob, command)
        state = self._mutation(command.expected_generation)
        snapshot = state.snapshot
        now = self._now(snapshot)
        if any(job.id == command.job.id for job in snapshot.jobs):
            raise UseCaseError(UseCaseCode.DUPLICATE_RESOURCE)
        company = next(
            (company for company in snapshot.companies if company.id == command.job.company.id),
            None,
        )
        if company is not None and (
            company.name != command.job.company.name
            or company.context != command.job.company.context
        ):
            raise UseCaseError(UseCaseCode.STATE_CONFLICT)
        with _domain_input():
            job = self._job(command.job)
            companies = snapshot.companies
            if company is None:
                companies = (*companies, self._company(command.job))
            changed = snapshot.model_copy(
                update={"as_of": now, "companies": companies, "jobs": (*snapshot.jobs, job)}
            )
            event = self._event(JobAdded(job=self._reference(job, "job")), now, now)
        return self._save(changed, state.generation, (event,))

    def create_claim(self, command: CreateClaim) -> CareerState:
        command = _command(CreateClaim, command)
        state = self._mutation(command.expected_generation)
        profile = state.snapshot.profile
        now = self._now(state.snapshot)
        if any(claim.id == command.id for claim in profile.claims):
            raise UseCaseError(UseCaseCode.DUPLICATE_RESOURCE)
        with _domain_input():
            claim = Claim(
                id=command.id,
                workspace_id=self.workspace_id,
                profile_id=profile.id,
                revision=1,
                classification="synthetic",
                assertion=command.assertion,
                text=command.text,
                origin="user_report",
                asserted_by=self.actor_id,
                asserted_at=now,
                status="self_reported",
            )
            changed_profile = profile.model_copy(
                update={"revision": profile.revision + 1, "claims": (*profile.claims, claim)}
            )
            changed = state.snapshot.model_copy(update={"as_of": now, "profile": changed_profile})
        return self._save(changed, state.generation)

    def attach_evidence(self, command: AttachEvidence) -> CareerState:
        command = _command(AttachEvidence, command)
        state = self._mutation(command.expected_generation)
        profile = state.snapshot.profile
        now = self._now(state.snapshot)
        if any(record.id == command.id for record in profile.evidence):
            raise UseCaseError(UseCaseCode.DUPLICATE_RESOURCE)
        claim = next((claim for claim in profile.claims if claim.id == command.claim_id), None)
        if claim is None:
            raise UseCaseError(UseCaseCode.RESOURCE_NOT_FOUND)
        material_dependency = any(
            ref.claim_id == claim.id for cv in state.snapshot.cvs for ref in cv.claim_refs
        ) or any(
            ref.claim_id == claim.id
            for draft in state.snapshot.drafts
            for assertion in draft.assertions
            for ref in assertion.source_claim_refs
        )
        if (
            claim.review is not None
            or claim.status not in ("self_reported", "candidate_support")
            or material_dependency
        ):
            raise UseCaseError(UseCaseCode.DEPENDENCY_RECONCILIATION_REQUIRED)
        with _domain_input():
            evidence = EvidenceRecord(
                id=command.id,
                workspace_id=self.workspace_id,
                profile_id=profile.id,
                revision=1,
                classification="synthetic",
                assertion=command.assertion,
                relation=command.relation,
                excerpt=command.excerpt,
                source_kind=command.source_kind,
                source_reference=command.source_reference,
                source_actor_id=self.actor_id if command.source_kind == "user_report" else None,
                collected_at=command.collected_at,
                experience_context=command.experience_context,
            )
            replacement = claim.model_copy(
                update={
                    "revision": claim.revision + 1,
                    "evidence_refs": (*claim.evidence_refs, evidence_ref(evidence)),
                }
            )
            changed_profile = profile.model_copy(
                update={
                    "revision": profile.revision + 1,
                    "claims": tuple(
                        replacement if item.id == claim.id else item for item in profile.claims
                    ),
                    "evidence": (*profile.evidence, evidence),
                }
            )
            changed = state.snapshot.model_copy(update={"as_of": now, "profile": changed_profile})
        return self._save(changed, state.generation)

    @staticmethod
    def _profile_pin(record: Claim | EvidenceRecord, command: ProfileRevisionCommand) -> None:
        if (
            record.revision != command.expected_revision
            or record.snapshot_digest != command.expected_digest
        ):
            raise UseCaseError(UseCaseCode.STATE_CONFLICT)

    @staticmethod
    def _claim_material_dependencies(snapshot: CareerSnapshot, identifiers: set[ClaimId]) -> None:
        if any(ref.claim_id in identifiers for cv in snapshot.cvs for ref in cv.claim_refs) or any(
            ref.claim_id in identifiers
            for draft in snapshot.drafts
            for assertion in draft.assertions
            for ref in assertion.source_claim_refs
        ):
            raise UseCaseError(UseCaseCode.DEPENDENCY_RECONCILIATION_REQUIRED)

    @staticmethod
    def _same_assertion_scope(left: Claim, right: EvidenceRecord) -> bool:
        return (
            left.assertion.kind,
            left.assertion.subject,
            left.assertion.unit,
        ) == (
            right.assertion.kind,
            right.assertion.subject,
            right.assertion.unit,
        )

    def _reconcile_profile_evidence(
        self, snapshot: CareerSnapshot, replacement: EvidenceRecord
    ) -> Profile:
        """Rebind all current claim refs without implicitly accepting any claim."""
        profile = snapshot.profile
        records = tuple(
            replacement if item.id == replacement.id else item for item in profile.evidence
        )
        claims: list[Claim] = []
        changed_ids: set[ClaimId] = set()
        for claim in profile.claims:
            refs = tuple(
                evidence_ref(replacement) if ref.evidence_id == replacement.id else ref
                for ref in claim.evidence_refs
            )
            refs_changed = refs != claim.evidence_refs
            contrary = any(
                record.qualifies_contradiction and self._same_assertion_scope(claim, record)
                for record in records
            )
            status = claim.status
            if status != "withdrawn":
                if contrary:
                    status = "contradicted"
                elif status == "contradicted" or (refs_changed and status == "reviewed_supported"):
                    status = "candidate_support" if refs else "self_reported"
            review = claim.review
            if refs_changed or status != claim.status:
                review = None
            if refs_changed or status != claim.status or review != claim.review:
                claim = claim.model_copy(
                    update={
                        "revision": claim.revision + 1,
                        "evidence_refs": refs,
                        "status": status,
                        "review": review,
                    }
                )
                changed_ids.add(claim.id)
            claims.append(claim)
        self._claim_material_dependencies(snapshot, changed_ids)
        return profile.model_copy(
            update={
                "revision": profile.revision + 1,
                "evidence": records,
                "claims": tuple(claims),
            }
        )

    def review_synthetic_evidence(
        self, evidence_id: EvidenceId, command: ReviewSyntheticEvidence
    ) -> CareerState:
        command = _command(ReviewSyntheticEvidence, command)
        with _domain_input():
            evidence_id = EvidenceId.model_validate(evidence_id, strict=True)
        state = self._mutation(command.expected_generation)
        source = next(
            (item for item in state.snapshot.profile.evidence if item.id == evidence_id), None
        )
        if source is None:
            raise UseCaseError(UseCaseCode.RESOURCE_NOT_FOUND)
        self._profile_pin(source, command)
        if (
            source.source_kind != "synthetic_fixture"
            or source.status != "active"
            or source.review is not None
        ):
            raise UseCaseError(UseCaseCode.STATE_CONFLICT)
        now = self._now(state.snapshot)
        with _domain_input():
            reviewed = source.model_copy(
                update={
                    "revision": source.revision + 1,
                    "review": EvidenceReview(
                        reviewer_id=self.actor_id,
                        kind="synthetic_review",
                        method="explicit_synthetic_source_review_v1",
                        reviewed_at=now,
                        content_digest=source.content_digest,
                    ),
                }
            )
            profile = self._reconcile_profile_evidence(state.snapshot, reviewed)
            changed = state.snapshot.model_copy(update={"as_of": now, "profile": profile})
        return self._save(changed, state.generation)

    def review_synthetic_claim(
        self, claim_id: ClaimId, command: ReviewSyntheticClaim
    ) -> CareerState:
        command = _command(ReviewSyntheticClaim, command)
        with _domain_input():
            claim_id = ClaimId.model_validate(claim_id, strict=True)
        state = self._mutation(command.expected_generation)
        profile = state.snapshot.profile
        claim = next((item for item in profile.claims if item.id == claim_id), None)
        if claim is None:
            raise UseCaseError(UseCaseCode.RESOURCE_NOT_FOUND)
        self._profile_pin(claim, command)
        if claim.status not in ("self_reported", "candidate_support") or claim.review is not None:
            raise UseCaseError(UseCaseCode.STATE_CONFLICT)
        evidence = {item.id: item for item in profile.evidence}
        sources = tuple(evidence[ref.evidence_id] for ref in claim.evidence_refs)
        if not any(
            source.qualifies_support
            and self._same_assertion_scope(claim, source)
            and source.assertion.value >= claim.assertion.value
            and (claim.assertion.kind != "experience" or source.experience_context is None)
            for source in sources
        ) or any(
            source.qualifies_contradiction and self._same_assertion_scope(claim, source)
            for source in profile.evidence
        ):
            raise UseCaseError(UseCaseCode.STATE_CONFLICT)
        self._claim_material_dependencies(state.snapshot, {claim.id})
        now = self._now(state.snapshot)
        with _domain_input():
            # Claim content excludes revision/review/status, so the new explicit
            # review binds the next revision and unchanged structured content.
            reviewed = claim.model_copy(
                update={
                    "revision": claim.revision + 1,
                    "status": "reviewed_supported",
                    "review": ContentReview(
                        revision=claim.revision + 1,
                        content_digest=claim.content_digest,
                        reviewer_id=self.actor_id,
                        reviewed_at=now,
                        method="explicit_synthetic_claim_review_v1",
                        decision="accepted",
                    ),
                }
            )
            changed_profile = profile.model_copy(
                update={
                    "revision": profile.revision + 1,
                    "claims": tuple(
                        reviewed if item.id == claim.id else item for item in profile.claims
                    ),
                }
            )
            changed = state.snapshot.model_copy(update={"as_of": now, "profile": changed_profile})
        return self._save(changed, state.generation)

    def withdraw_evidence(self, evidence_id: EvidenceId, command: WithdrawEvidence) -> CareerState:
        command = _command(WithdrawEvidence, command)
        with _domain_input():
            evidence_id = EvidenceId.model_validate(evidence_id, strict=True)
        state = self._mutation(command.expected_generation)
        source = next(
            (item for item in state.snapshot.profile.evidence if item.id == evidence_id), None
        )
        if source is None:
            raise UseCaseError(UseCaseCode.RESOURCE_NOT_FOUND)
        self._profile_pin(source, command)
        if source.status != "active":
            raise UseCaseError(UseCaseCode.STATE_CONFLICT)
        now = self._now(state.snapshot)
        with _domain_input():
            withdrawn = source.model_copy(
                update={"revision": source.revision + 1, "status": "withdrawn"}
            )
            profile = self._reconcile_profile_evidence(state.snapshot, withdrawn)
            changed = state.snapshot.model_copy(update={"as_of": now, "profile": profile})
        return self._save(changed, state.generation)

    def create_application(self, command: CreateApplication) -> CareerState:
        command = _command(CreateApplication, command)
        state = self._mutation(command.expected_generation)
        snapshot = state.snapshot
        now = self._now(snapshot)
        if any(item.id == command.id for item in snapshot.applications):
            raise UseCaseError(UseCaseCode.DUPLICATE_RESOURCE)
        job = next((job for job in snapshot.jobs if job.id == command.job_id), None)
        if job is None:
            raise UseCaseError(UseCaseCode.RESOURCE_NOT_FOUND)
        job_opportunities = {item.id: item.opportunity_id for item in snapshot.jobs}
        if any(
            job_opportunities[item.job_id] == job.opportunity_id for item in snapshot.applications
        ):
            raise UseCaseError(UseCaseCode.DUPLICATE_RESOURCE)
        with _domain_input():
            application = Application(
                id=command.id,
                workspace_id=self.workspace_id,
                profile_id=snapshot.profile.id,
                revision=1,
                classification="synthetic",
                job_id=job.id,
                state="preparing",
                history=(
                    StatusObservation(
                        actor_id=self.actor_id,
                        occurred_at=command.occurred_at,
                        recorded_at=now,
                        state="preparing",
                        basis="user_reported",
                    ),
                ),
            )
            changed = snapshot.model_copy(
                update={"as_of": now, "applications": (*snapshot.applications, application)}
            )
            event = self._event(
                ApplicationStatusRecorded(
                    application=self._reference(application, "application"),
                    previous_state=None,
                    state="preparing",
                    basis="user_reported",
                ),
                command.occurred_at,
                now,
            )
        return self._save(changed, state.generation, (event,))

    def transition_application(
        self, application_id: ApplicationId, command: TransitionApplication
    ) -> CareerState:
        command = _command(TransitionApplication, command)
        with _domain_input():
            application_id = ApplicationId.model_validate(application_id, strict=True)
        state = self._mutation(command.expected_generation)
        snapshot = state.snapshot
        now = self._now(snapshot)
        application = next(
            (item for item in snapshot.applications if item.id == application_id), None
        )
        if application is None:
            raise UseCaseError(UseCaseCode.RESOURCE_NOT_FOUND)
        if not allowed_transition(
            application.state, command.state, "user_reported", command.external_manual
        ):
            raise UseCaseError(UseCaseCode.INVALID_APPLICATION_TRANSITION)
        with _domain_input():
            observation = StatusObservation(
                actor_id=self.actor_id,
                occurred_at=command.occurred_at,
                recorded_at=now,
                state=command.state,
                basis="user_reported",
                external_manual=command.external_manual,
            )
            changed_application = application.model_copy(
                update={
                    "revision": application.revision + 1,
                    "state": command.state,
                    "history": (*application.history, observation),
                }
            )
            changed = snapshot.model_copy(
                update={
                    "as_of": now,
                    "applications": tuple(
                        changed_application if item.id == application_id else item
                        for item in snapshot.applications
                    ),
                }
            )
            event = self._event(
                ApplicationStatusRecorded(
                    application=self._reference(changed_application, "application"),
                    previous_state=application.state,
                    state=command.state,
                    basis="user_reported",
                    external_manual=command.external_manual,
                ),
                command.occurred_at,
                now,
            )
        return self._save(changed, state.generation, (event,))
