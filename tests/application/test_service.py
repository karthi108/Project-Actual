"""Intent semantics and port calls; real database rollback is tested at the API."""

from datetime import timedelta

import pytest
from actual_application_fixtures import (
    ACTOR,
    NOW,
    POSTED,
    PROFILE,
    WORKSPACE,
    MemoryRepository,
    RepositoryFailure,
    initialization,
    manual_job,
    python_assertion,
)

from actual.application import CareerService, CareerState, UseCaseCode, UseCaseError
from actual.application.commands import (
    AddJob,
    AttachEvidence,
    CreateApplication,
    CreateClaim,
    TransitionApplication,
)
from actual.career.events import ApplicationStatusRecorded, JobAdded
from actual.career.materials import CVVariant, Draft, DraftAssertion
from actual.core.primitives import (
    ApplicationId,
    ClaimId,
    CompanyId,
    CVId,
    DraftId,
    EvidenceId,
    JobId,
    WorkspaceId,
    canonical_bytes,
    content_digest,
)
from actual.core.workflow import ContentReview
from actual.profile.contracts import claim_ref, evidence_ref

CLAIM_ID = ClaimId("claim_" + "5" * 32)
EVIDENCE_ID = EvidenceId("evidence_" + "6" * 32)
APPLICATION_ID = ApplicationId("application_" + "7" * 32)
OCCURRED = NOW - timedelta(hours=1)


@pytest.fixture
def repository() -> MemoryRepository:
    return MemoryRepository()


@pytest.fixture
def service(repository: MemoryRepository) -> CareerService:
    return CareerService(repository, WORKSPACE, ACTOR, clock=lambda: NOW)


@pytest.fixture
def initialized(service: CareerService) -> CareerState:
    return service.initialize(initialization())


def claim_command(generation: int = 1, **updates: object) -> CreateClaim:
    return CreateClaim(
        expected_generation=generation,
        id=CLAIM_ID,
        assertion=python_assertion(),
        text="Synthetic user reports Python skill.",
    ).model_copy(update=updates)


def evidence_command(generation: int = 2, **updates: object) -> AttachEvidence:
    return AttachEvidence(
        expected_generation=generation,
        id=EVIDENCE_ID,
        claim_id=CLAIM_ID,
        assertion=python_assertion(),
        relation="supports",
        source_kind="project_artifact",
        source_reference="synthetic:artifact-declared-by-user",
        excerpt="Fabricated project artifact excerpt.",
        collected_at=NOW,
    ).model_copy(update=updates)


def application_command(generation: int = 1, **updates: object) -> CreateApplication:
    return CreateApplication(
        expected_generation=generation,
        id=APPLICATION_ID,
        job_id=manual_job().id,
        occurred_at=OCCURRED,
    ).model_copy(update=updates)


def transition_command(generation: int = 2, **updates: object) -> TransitionApplication:
    return TransitionApplication(
        expected_generation=generation,
        state="ready_for_review",
        occurred_at=OCCURRED + timedelta(minutes=1),
    ).model_copy(update=updates)


def assert_error(code: UseCaseCode, action: object) -> None:
    with pytest.raises(UseCaseError) as captured:
        action()
    assert captured.value.code == code
    assert str(captured.value) == code.value


def test_bootstrap_is_one_atomic_job_observation_and_empty_profile(
    service: CareerService, repository: MemoryRepository
) -> None:
    state = service.initialize(initialization())
    assert state.generation == 1
    assert state.snapshot.workspace_id == WORKSPACE
    assert state.snapshot.classification == "synthetic"
    assert state.snapshot.profile.id == PROFILE
    assert state.snapshot.profile.claims == state.snapshot.profile.evidence == ()
    assert state.snapshot.requirements == state.snapshot.cvs == state.snapshot.drafts == ()
    assert state.snapshot.jobs[0].decision == "new"
    assert len(repository.calls) == 1
    saved, expected, observations = repository.calls[0]
    assert saved == state.snapshot and expected == 0
    assert len(observations) == 1
    event = observations[0]
    assert isinstance(event.payload, JobAdded)
    assert event.actor_id == ACTOR and event.workspace_id == WORKSPACE
    assert event.source == "manual" and event.source_event_id is None
    assert event.occurred_at == event.recorded_at == NOW
    assert event.payload.job.content_digest == content_digest(saved.jobs[0].model_dump(mode="json"))
    assert service.get_state() == state
    assert service.job(saved.jobs[0].id) == (state, saved.jobs[0])
    assert service.events() == observations


def test_bootstrap_cannot_overwrite_existing_state(
    service: CareerService, repository: MemoryRepository, initialized: CareerState
) -> None:
    assert_error(UseCaseCode.STATE_CONFLICT, lambda: service.initialize(initialization()))
    assert repository.state == initialized and len(repository.calls) == 1


def test_missing_workspace_and_resources_are_explicit(service: CareerService) -> None:
    assert_error(UseCaseCode.RESOURCE_NOT_FOUND, service.get_state)
    service.initialize(initialization())
    assert_error(UseCaseCode.RESOURCE_NOT_FOUND, lambda: service.job(JobId("job_" + "9" * 32)))
    assert_error(UseCaseCode.RESOURCE_NOT_FOUND, lambda: service.application(APPLICATION_ID))


@pytest.mark.parametrize("privacy", ["personal", "sensitive"])
def test_real_data_read_and_mutation_fail_closed(
    privacy: str, service: CareerService, repository: MemoryRepository, initialized: CareerState
) -> None:
    snapshot = initialized.snapshot
    snapshot = snapshot.model_copy(
        update={
            "classification": privacy,
            "companies": tuple(
                record.model_copy(update={"classification": privacy})
                for record in snapshot.companies
            ),
            "jobs": tuple(
                record.model_copy(update={"classification": privacy}) for record in snapshot.jobs
            ),
            "profile": snapshot.profile.model_copy(update={"classification": privacy}),
        }
    )
    repository.state = CareerState(snapshot, 1)
    assert_error(UseCaseCode.SYNTHETIC_ONLY, service.get_state)
    assert_error(UseCaseCode.SYNTHETIC_ONLY, lambda: service.create_claim(claim_command()))
    assert_error(UseCaseCode.SYNTHETIC_ONLY, service.events)
    assert len(repository.calls) == 1


def test_foreign_workspace_read_is_rejected(
    service: CareerService, repository: MemoryRepository, initialized: CareerState
) -> None:
    foreign = WorkspaceId("workspace_" + "a" * 32)
    snapshot = initialized.snapshot
    snapshot = snapshot.model_copy(
        update={
            "workspace_id": foreign,
            "companies": tuple(
                record.model_copy(update={"workspace_id": foreign}) for record in snapshot.companies
            ),
            "jobs": tuple(
                record.model_copy(update={"workspace_id": foreign}) for record in snapshot.jobs
            ),
            "profile": snapshot.profile.model_copy(update={"workspace_id": foreign}),
        }
    )
    repository.state = CareerState(snapshot, 1)
    assert_error(UseCaseCode.STATE_CONFLICT, service.get_state)


def test_stale_generation_never_calls_save(
    service: CareerService, repository: MemoryRepository, initialized: CareerState
) -> None:
    assert_error(UseCaseCode.STALE_GENERATION, lambda: service.create_claim(claim_command(2)))
    assert repository.state == initialized and len(repository.calls) == 1


@pytest.mark.parametrize("generation", [True, "1", 0, 9223372036854775807])
def test_service_revalidates_copied_command_before_any_port_mutation(
    generation: object,
    service: CareerService,
    repository: MemoryRepository,
    initialized: CareerState,
) -> None:
    command = claim_command().model_copy(update={"expected_generation": generation})
    assert_error(UseCaseCode.INVALID_DOMAIN_INPUT, lambda: service.create_claim(command))
    assert repository.state == initialized and len(repository.calls) == 1


def test_new_job_reuses_identical_company_and_records_one_exact_event(
    service: CareerService, repository: MemoryRepository, initialized: CareerState
) -> None:
    command = AddJob(expected_generation=1, job=manual_job(2))
    state = service.add_job(command)
    assert state.generation == 2
    assert len(state.snapshot.companies) == 1
    assert len(state.snapshot.jobs) == 2
    assert len(repository.observations) == 2
    event = repository.observations[-1]
    assert event.payload.job.object_id == command.job.id
    assert event.payload.job.content_digest == content_digest(
        state.snapshot.jobs[-1].model_dump(mode="json")
    )


def test_new_company_exists_only_as_part_of_new_job_intake(
    service: CareerService, repository: MemoryRepository, initialized: CareerState
) -> None:
    job = manual_job(2)
    company = job.company.model_copy(
        update={"id": CompanyId("company_" + "a" * 32), "name": "Second synthetic company"}
    )
    state = service.add_job(
        AddJob(expected_generation=1, job=job.model_copy(update={"company": company}))
    )
    assert len(state.snapshot.companies) == 2
    assert state.snapshot.companies[0] == initialized.snapshot.companies[0]
    created = state.snapshot.companies[-1]
    assert created.id == state.snapshot.jobs[-1].company_id == company.id
    assert created.workspace_id == WORKSPACE and created.classification == "synthetic"
    assert created.revision == 1 and len(repository.calls[-1][2]) == 1


def test_job_duplicate_and_incidental_company_change_are_rejected(
    service: CareerService, repository: MemoryRepository, initialized: CareerState
) -> None:
    assert_error(
        UseCaseCode.DUPLICATE_RESOURCE,
        lambda: service.add_job(AddJob(expected_generation=1, job=manual_job())),
    )
    changed = manual_job(2)
    changed = changed.model_copy(
        update={"company": changed.company.model_copy(update={"context": "Changed context"})}
    )
    assert_error(
        UseCaseCode.STATE_CONFLICT,
        lambda: service.add_job(AddJob(expected_generation=1, job=changed)),
    )
    assert repository.state == initialized and len(repository.calls) == 1


def test_opportunity_alias_conflicting_source_and_future_posting_fail_domain_validation(
    service: CareerService, repository: MemoryRepository, initialized: CareerState
) -> None:
    for job in (
        manual_job(2, opportunity_id=manual_job().opportunity_id, text="Different source text"),
        manual_job(2, posted_at=NOW + timedelta(microseconds=1)),
    ):
        assert_error(
            UseCaseCode.INVALID_DOMAIN_INPUT,
            lambda job=job: service.add_job(AddJob(expected_generation=1, job=job)),
        )
    assert repository.state == initialized and len(repository.calls) == 1


def test_claim_remains_attributed_user_report_without_review(
    service: CareerService, repository: MemoryRepository, initialized: CareerState
) -> None:
    state = service.create_claim(claim_command())
    profile = state.snapshot.profile
    claim = profile.claims[0]
    assert profile.revision == 2 and claim.revision == 1
    assert claim.origin == "user_report" and claim.status == "self_reported"
    assert claim.asserted_by == ACTOR and claim.asserted_at == NOW
    assert claim.review is None and claim.evidence_refs == ()
    assert claim.workspace_id == WORKSPACE and claim.profile_id == PROFILE
    assert claim.classification == "synthetic"
    assert repository.calls[-1][2] == ()
    assert_error(UseCaseCode.DUPLICATE_RESOURCE, lambda: service.create_claim(claim_command(2)))


@pytest.mark.parametrize(
    "source",
    ["user_report", "project_artifact", "imported_document", "ai_proposal", "synthetic_fixture"],
)
@pytest.mark.parametrize("relation", ["supports", "contradicts"])
def test_source_attachment_preserves_claim_status_and_unreviewed_provenance(
    source: str,
    relation: str,
    service: CareerService,
    repository: MemoryRepository,
    initialized: CareerState,
) -> None:
    prior = service.create_claim(claim_command())
    state = service.attach_evidence(evidence_command(source_kind=source, relation=relation))
    profile = state.snapshot.profile
    evidence = profile.evidence[0]
    claim = profile.claims[0]
    assert state.generation == 3 and profile.revision == prior.snapshot.profile.revision + 1
    assert claim.revision == prior.snapshot.profile.claims[0].revision + 1
    assert claim.status == "self_reported" and claim.review is None
    assert claim.origin == "user_report" and claim.asserted_by == ACTOR
    assert claim.evidence_refs == (evidence_ref(evidence),)
    assert evidence.review is None and not evidence.qualifies_support
    assert evidence.source_kind == source and evidence.relation == relation
    assert evidence.source_actor_id == (ACTOR if source == "user_report" else None)
    assert evidence.workspace_id == WORKSPACE and evidence.profile_id == PROFILE
    assert evidence.collected_at == NOW and evidence.classification == "synthetic"


def test_evidence_scope_future_collection_missing_claim_and_duplicate_are_rejected(
    service: CareerService, repository: MemoryRepository, initialized: CareerState
) -> None:
    service.create_claim(claim_command())
    prior = repository.state
    for updates in (
        {"assertion": python_assertion().model_copy(update={"subject": "rust"})},
        {"collected_at": NOW + timedelta(microseconds=1)},
    ):
        assert_error(
            UseCaseCode.INVALID_DOMAIN_INPUT,
            lambda updates=updates: service.attach_evidence(evidence_command(**updates)),
        )
    assert_error(
        UseCaseCode.RESOURCE_NOT_FOUND,
        lambda: service.attach_evidence(evidence_command(claim_id=ClaimId("claim_" + "9" * 32))),
    )
    assert repository.state == prior and len(repository.calls) == 2
    service.attach_evidence(evidence_command())
    assert_error(
        UseCaseCode.DUPLICATE_RESOURCE, lambda: service.attach_evidence(evidence_command(3))
    )


def test_existing_candidate_support_status_is_not_automatically_promoted(
    service: CareerService, repository: MemoryRepository, initialized: CareerState
) -> None:
    state = service.create_claim(claim_command())
    profile = state.snapshot.profile
    candidate = profile.claims[0].model_copy(update={"status": "candidate_support"})
    repository.state = CareerState(
        state.snapshot.model_copy(
            update={"profile": profile.model_copy(update={"claims": (candidate,)})}
        ),
        state.generation,
    )
    state = service.attach_evidence(evidence_command())
    claim = state.snapshot.profile.claims[0]
    assert claim.status == "candidate_support" and claim.review is None
    assert not state.snapshot.profile.evidence[0].qualifies_support


def test_foreign_and_real_historical_events_fail_closed_even_for_synthetic_current_state(
    service: CareerService, repository: MemoryRepository, initialized: CareerState
) -> None:
    original = repository.observations[0]
    foreign = WorkspaceId("workspace_" + "f" * 32)
    repository.observations = (
        original.model_copy(
            update={
                "workspace_id": foreign,
                "business_objects": (
                    original.payload.job.model_copy(update={"workspace_id": foreign}),
                ),
                "payload": original.payload.model_copy(
                    update={
                        "job": original.payload.job.model_copy(update={"workspace_id": foreign})
                    }
                ),
            }
        ),
    )
    assert_error(UseCaseCode.STATE_CONFLICT, service.events)
    reference = original.payload.job.model_copy(update={"classification": "personal"})
    repository.observations = (
        original.model_copy(
            update={
                "privacy_classification": "personal",
                "business_objects": (reference,),
                "payload": original.payload.model_copy(update={"job": reference}),
            }
        ),
    )
    assert_error(UseCaseCode.SYNTHETIC_ONLY, service.events)


@pytest.mark.parametrize("dependency", ["cv", "draft", "review"])
def test_attaching_source_to_material_or_review_dependency_requires_reconciliation(
    dependency: str,
    service: CareerService,
    repository: MemoryRepository,
    initialized: CareerState,
) -> None:
    state = service.create_claim(claim_command())
    snapshot = state.snapshot
    claim = snapshot.profile.claims[0]
    ref = claim_ref(claim)
    if dependency == "cv":
        snapshot = snapshot.model_copy(
            update={
                "cvs": (
                    CVVariant(
                        id=CVId("cv_" + "8" * 32),
                        workspace_id=WORKSPACE,
                        profile_id=PROFILE,
                        revision=1,
                        classification="synthetic",
                        name="Synthetic CV",
                        summary="Fabricated metadata",
                        claim_refs=(ref,),
                    ),
                )
            }
        )
    elif dependency == "draft":
        snapshot = snapshot.model_copy(
            update={
                "drafts": (
                    Draft(
                        id=DraftId("draft_" + "8" * 32),
                        workspace_id=WORKSPACE,
                        profile_id=PROFILE,
                        revision=1,
                        classification="synthetic",
                        name="Synthetic draft",
                        summary="Fabricated metadata",
                        assertions=(
                            DraftAssertion(
                                assertion=claim.assertion,
                                text=claim.text,
                                source_claim_refs=(ref,),
                            ),
                        ),
                    ),
                )
            }
        )
    else:
        claim = claim.model_copy(
            update={
                "review": ContentReview(
                    revision=claim.revision,
                    content_digest=claim.content_digest,
                    reviewer_id=ACTOR,
                    reviewed_at=NOW,
                    method="Synthetic rejected review",
                    decision="rejected",
                )
            }
        )
        snapshot = snapshot.model_copy(
            update={"profile": snapshot.profile.model_copy(update={"claims": (claim,)})}
        )
    repository.state = CareerState(snapshot, 2)
    assert_error(
        UseCaseCode.DEPENDENCY_RECONCILIATION_REQUIRED,
        lambda: service.attach_evidence(evidence_command()),
    )
    assert repository.state.snapshot == snapshot and len(repository.calls) == 2


def test_application_creation_and_valid_transition_preserve_history_and_exact_events(
    service: CareerService, repository: MemoryRepository, initialized: CareerState
) -> None:
    state = service.create_application(application_command())
    original = state.snapshot.applications[0]
    assert original.state == "preparing" and len(original.history) == 1
    assert original.history[0].actor_id == ACTOR
    assert original.history[0].basis == "user_reported"
    assert original.history[0].recorded_at == NOW
    assert service.application(APPLICATION_ID) == (state, original)
    initial_event = repository.observations[-1]
    assert isinstance(initial_event.payload, ApplicationStatusRecorded)
    assert initial_event.payload.previous_state is None
    assert initial_event.occurred_at == OCCURRED
    state = service.transition_application(APPLICATION_ID, transition_command())
    changed = state.snapshot.applications[0]
    assert changed.state == "ready_for_review" and changed.revision == original.revision + 1
    assert changed.history[:-1] == original.history
    event = repository.observations[-1]
    assert event.payload.previous_state == "preparing"
    assert event.payload.state == changed.history[-1].state
    assert event.payload.application.content_digest == content_digest(
        changed.model_dump(mode="json")
    )
    assert event.occurred_at == changed.history[-1].occurred_at
    assert event.recorded_at == changed.history[-1].recorded_at


def test_application_canonical_opportunity_alias_cannot_duplicate_intent(
    service: CareerService, repository: MemoryRepository, initialized: CareerState
) -> None:
    alias = manual_job(2, opportunity_id=manual_job().opportunity_id)
    service.add_job(AddJob(expected_generation=1, job=alias))
    service.create_application(application_command(2))
    assert_error(
        UseCaseCode.DUPLICATE_RESOURCE,
        lambda: service.create_application(
            application_command(3, id=ApplicationId("application_" + "a" * 32), job_id=alias.id)
        ),
    )
    assert len(repository.state.snapshot.applications) == 1 and len(repository.calls) == 3


@pytest.mark.parametrize(
    "updates", [{"state": "offer"}, {"state": "applied"}, {"external_manual": True}]
)
def test_invalid_application_transition_never_calls_save(
    updates: dict,
    service: CareerService,
    repository: MemoryRepository,
    initialized: CareerState,
) -> None:
    original = service.create_application(application_command())
    assert_error(
        UseCaseCode.INVALID_APPLICATION_TRANSITION,
        lambda: service.transition_application(APPLICATION_ID, transition_command(**updates)),
    )
    assert repository.state == original and len(repository.calls) == 2


def test_explicit_manual_submission_records_report_without_internal_review(
    service: CareerService, repository: MemoryRepository, initialized: CareerState
) -> None:
    service.create_application(application_command())
    changed = service.transition_application(
        APPLICATION_ID, transition_command(state="applied", external_manual=True)
    )
    application = changed.snapshot.applications[0]
    assert tuple(item.state for item in application.history) == ("preparing", "applied")
    assert application.history[-1].basis == "user_reported"
    assert application.history[-1].external_manual
    assert changed.snapshot.drafts == ()
    assert repository.observations[-1].payload.external_manual


@pytest.mark.parametrize(
    "occurrence", [POSTED - timedelta(microseconds=1), NOW + timedelta(microseconds=1)]
)
def test_application_observation_must_fit_job_and_recording_timeline(
    occurrence: object,
    service: CareerService,
    repository: MemoryRepository,
    initialized: CareerState,
) -> None:
    assert_error(
        UseCaseCode.INVALID_DOMAIN_INPUT,
        lambda: service.create_application(application_command(occurred_at=occurrence)),
    )
    assert repository.state == initialized and len(repository.calls) == 1


@pytest.mark.parametrize(
    "occurrence", [OCCURRED, OCCURRED - timedelta(microseconds=1), NOW + timedelta(microseconds=1)]
)
def test_transition_occurrences_are_strictly_increasing_and_not_future(
    occurrence: object,
    service: CareerService,
    repository: MemoryRepository,
    initialized: CareerState,
) -> None:
    original = service.create_application(application_command())
    assert_error(
        UseCaseCode.INVALID_DOMAIN_INPUT,
        lambda: service.transition_application(
            APPLICATION_ID, transition_command(occurred_at=occurrence)
        ),
    )
    assert repository.state == original and len(repository.calls) == 2


def test_clock_regression_and_naive_clock_are_not_silently_coerced(
    repository: MemoryRepository, initialized: CareerState
) -> None:
    for now in (NOW - timedelta(microseconds=1), NOW.replace(tzinfo=None)):
        service = CareerService(repository, WORKSPACE, ACTOR, clock=lambda now=now: now)
        assert_error(
            UseCaseCode.INVALID_DOMAIN_INPUT,
            lambda service=service: service.create_claim(claim_command()),
        )
    assert repository.state == initialized and len(repository.calls) == 1


def test_repository_failure_is_propagated_without_retry_or_split_event_write(
    service: CareerService, repository: MemoryRepository, initialized: CareerState
) -> None:
    repository.fail_save = True
    before = canonical_bytes(initialized.snapshot)
    observations = repository.observations
    with pytest.raises(RepositoryFailure):
        service.create_application(application_command())
    assert len(repository.calls) == 2
    snapshot, expected, events = repository.calls[-1]
    assert expected == 1 and len(snapshot.applications) == len(events) == 1
    assert isinstance(events[0].payload, ApplicationStatusRecorded)
    assert canonical_bytes(repository.state.snapshot) == before
    assert repository.observations == observations
