"""Closed observation contracts, reference snapshots and pure source redelivery checks."""

import json

import pytest
from pydantic import ValidationError

from actual.career.events import (
    ApplicationStatusRecorded,
    AssessmentCounts,
    CVRecommended,
    DraftReviewed,
    EventPayload,
    FitAssessmentRecorded,
    JobAdded,
    RequirementsReviewed,
    WorkEvent,
    delivery_relation,
    validate_references,
)
from actual.core.events import EventHeader
from actual.core.primitives import (
    ActorId,
    ApplicationId,
    AssessmentId,
    Classification,
    CorrelationId,
    CVId,
    DraftId,
    EventId,
    EvidenceId,
    Identifier,
    JobId,
    ProfileId,
    RequirementId,
    SourceEventId,
    WorkspaceId,
    canonical_bytes,
    canonical_data,
    load_contract,
)
from actual.core.references import BusinessObjectRef, EvidenceRef, ObjectKind

WORKSPACE = WorkspaceId("workspace_" + "1" * 32)
OTHER_WORKSPACE = WorkspaceId("workspace_" + "2" * 32)
ACTOR = ActorId("actor_" + "1" * 32)
OCCURRED = "2026-10-01T12:00:00Z"
RECORDED = "2026-10-01T13:00:00Z"
REVIEWED = "2026-10-01T11:00:00Z"
IDENTIFIERS: dict[str, type[Identifier]] = {
    "job": JobId,
    "profile": ProfileId,
    "requirement": RequirementId,
    "assessment": AssessmentId,
    "cv": CVId,
    "draft": DraftId,
    "application": ApplicationId,
}


def object_ref(
    kind: ObjectKind,
    number: int = 1,
    workspace: WorkspaceId = WORKSPACE,
    classification: Classification = "synthetic",
) -> BusinessObjectRef:
    return BusinessObjectRef(
        workspace_id=workspace,
        classification=classification,
        kind=kind,
        object_id=IDENTIFIERS[kind](f"{kind}_{number:032x}"),
        revision=1,
        content_digest="a" * 64,
    )


def evidence_ref(
    number: int = 1,
    workspace: WorkspaceId = WORKSPACE,
    classification: Classification = "synthetic",
) -> EvidenceRef:
    return EvidenceRef(
        workspace_id=workspace,
        classification=classification,
        profile_id=ProfileId("profile_" + f"{1:032x}"),
        evidence_id=EvidenceId("evidence_" + f"{number:032x}"),
        revision=1,
        content_digest="b" * 64,
    )


def work_event(
    payload: EventPayload | None = None,
    refs: tuple[BusinessObjectRef, ...] | None = None,
    evidence: tuple[EvidenceRef, ...] = (),
) -> WorkEvent:
    if payload is None:
        payload = JobAdded(job=object_ref("job"))
    if refs is None:
        refs = (object_ref("job"),)
    return WorkEvent(
        event_id=EventId("event_" + "1" * 32),
        workspace_id=WORKSPACE,
        actor_id=ACTOR,
        occurred_at=OCCURRED,
        recorded_at=RECORDED,
        activity=payload.activity,
        source="manual",
        business_objects=refs,
        payload=payload,
        privacy_classification="synthetic",
        source_event_id=SourceEventId("source_event_" + "1" * 32),
        correlation_id=CorrelationId("correlation_" + "1" * 32),
        evidence_refs=evidence,
    )


def six_events() -> tuple[WorkEvent, ...]:
    job, profile = object_ref("job"), object_ref("profile")
    requirement, assessment = object_ref("requirement"), object_ref("assessment")
    cv, draft, application = object_ref("cv"), object_ref("draft"), object_ref("application")
    evidence = (evidence_ref(),)
    return (
        work_event(),
        work_event(
            RequirementsReviewed(
                job=job,
                requirements=(requirement,),
                reviewer_id=ACTOR,
                reviewed_at=REVIEWED,
            ),
            (job, requirement),
        ),
        work_event(
            FitAssessmentRecorded(
                job=job,
                profile=profile,
                assessment=assessment,
                counts=AssessmentCounts(supported=2, partial=1, gap=1, unknown=1, conflict=1),
            ),
            (job, profile, assessment),
            evidence,
        ),
        work_event(CVRecommended(job=job, profile=profile, cvs=(cv,)), (job, profile, cv)),
        work_event(
            DraftReviewed(
                draft=draft, decision="accepted", reviewer_id=ACTOR, reviewed_at=REVIEWED
            ),
            (draft,),
            evidence,
        ),
        work_event(
            ApplicationStatusRecorded(
                application=application,
                previous_state="reviewed",
                state="applied",
                basis="user_reported",
            ),
            (application,),
        ),
    )


@pytest.mark.parametrize("event", six_events())
def test_six_observation_activities_roundtrip_as_closed_metadata(event: WorkEvent) -> None:
    encoded = canonical_bytes(event)
    assert load_contract(WorkEvent, encoded) == event
    assert event.activity == event.payload.activity
    assert encoded.endswith(b"\n")
    assert all(text not in encoded for text in (b'"prompt"', b'"cv_text"', b'"authority"'))
    validate_references(event, event.business_objects, event.evidence_refs)


def test_shared_header_is_metadata_and_cannot_substitute_for_a_career_event() -> None:
    metadata = work_event().model_dump(mode="python", exclude={"activity", "payload"})
    header = EventHeader.model_validate(metadata)
    assert "activity" not in EventHeader.model_fields
    assert "payload" not in EventHeader.model_fields
    assert load_contract(EventHeader, canonical_bytes(header)) == header
    with pytest.raises(ValidationError):
        load_contract(WorkEvent, canonical_bytes(header))


def test_shared_header_rejects_domain_payload_fields() -> None:
    with pytest.raises(ValidationError):
        EventHeader.model_validate(work_event().model_dump(mode="python"))


@pytest.mark.parametrize("extra", ["authority", "approved", "properties", "prompt", "cv_text"])
@pytest.mark.parametrize("nested", [False, True])
def test_event_and_payload_reject_unregistered_or_content_fields(extra: str, nested: bool) -> None:
    data = work_event().model_dump(mode="json")
    target = data["payload"] if nested else data
    target[extra] = "untrusted data cannot grant authority"
    with pytest.raises(ValidationError):
        load_contract(WorkEvent, canonical_data(data))


@pytest.mark.parametrize("nested", [False, True])
def test_event_and_payload_schema_versions_are_closed(nested: bool) -> None:
    data = work_event().model_dump(mode="json")
    target = data["payload"] if nested else data
    target["schema_version"] = "actual-core-v99"
    with pytest.raises(ValueError):
        load_contract(WorkEvent, canonical_data(data))


def test_payload_activity_discriminator_rejects_unregistered_activity() -> None:
    data = work_event().model_dump(mode="json")
    data["payload"]["activity"] = "send_application"
    with pytest.raises(ValidationError):
        load_contract(WorkEvent, canonical_data(data))


def test_envelope_activity_cannot_override_payload() -> None:
    with pytest.raises(ValidationError, match="activity differs"):
        work_event().model_copy(update={"activity": "draft_reviewed"})


@pytest.mark.parametrize("field", ["source", "privacy_classification"])
def test_event_source_and_classification_are_registered(field: str) -> None:
    value = "secret" if field == "privacy_classification" else "browser_admin"
    with pytest.raises(ValidationError):
        work_event().model_copy(update={field: value})


def test_recording_before_occurrence_is_rejected() -> None:
    with pytest.raises(ValidationError, match="Recording"):
        work_event().model_copy(update={"recorded_at": "2026-09-30T12:00:00Z"})


def test_delayed_recording_is_valid_without_changing_occurrence() -> None:
    original = work_event()
    delayed = original.model_copy(update={"recorded_at": "2026-10-03T12:00:00Z"})
    assert delayed.occurred_at == original.occurred_at
    assert delayed.recorded_at > original.recorded_at


@pytest.mark.parametrize("timestamp", ["2026-10-01T12:00:00", 12345, True])
def test_event_instants_require_explicit_timezone(timestamp: object) -> None:
    with pytest.raises(ValidationError):
        work_event().model_copy(update={"occurred_at": timestamp})


@pytest.mark.parametrize(
    "payload",
    [
        {"activity": "job_added", "job": object_ref("cv")},
        {
            "activity": "requirements_reviewed",
            "job": object_ref("job"),
            "requirements": (object_ref("cv"),),
            "reviewer_id": ACTOR,
            "reviewed_at": REVIEWED,
        },
        {
            "activity": "fit_assessment_recorded",
            "job": object_ref("job"),
            "profile": object_ref("profile"),
            "assessment": object_ref("requirement"),
            "counts": AssessmentCounts(supported=1, partial=0, gap=0, unknown=0, conflict=0),
        },
        {
            "activity": "cv_recommended",
            "job": object_ref("job"),
            "profile": object_ref("job"),
            "cvs": (object_ref("cv"),),
        },
        {
            "activity": "draft_reviewed",
            "draft": object_ref("cv"),
            "decision": "rejected",
            "reviewer_id": ACTOR,
            "reviewed_at": REVIEWED,
        },
        {
            "activity": "application_status_recorded",
            "application": object_ref("job"),
            "previous_state": None,
            "state": "preparing",
            "basis": "user_reported",
        },
    ],
)
def test_every_payload_rejects_wrong_reference_kind(payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError, match="wrong business-object kind"):
        work_event().model_copy(update={"activity": payload["activity"], "payload": payload})


@pytest.mark.parametrize("kind", ["requirements", "cvs"])
def test_payload_reference_collections_reject_duplicate_identities(kind: str) -> None:
    if kind == "requirements":
        repeated = object_ref("requirement")
        with pytest.raises(ValidationError, match="repeat"):
            RequirementsReviewed(
                job=object_ref("job"),
                requirements=(repeated, repeated),
                reviewer_id=ACTOR,
                reviewed_at=REVIEWED,
            )
    else:
        repeated = object_ref("cv")
        with pytest.raises(ValidationError, match="repeat"):
            CVRecommended(job=object_ref("job"), profile=object_ref("profile"), cvs=(repeated,) * 2)


@pytest.mark.parametrize(
    ("kind", "size"), [("requirements", 0), ("requirements", 257), ("cvs", 0), ("cvs", 33)]
)
def test_payload_reference_collections_are_bounded(kind: str, size: int) -> None:
    if kind == "requirements":
        with pytest.raises(ValidationError):
            RequirementsReviewed(
                job=object_ref("job"),
                requirements=tuple(object_ref("requirement", index + 1) for index in range(size)),
                reviewer_id=ACTOR,
                reviewed_at=REVIEWED,
            )
    else:
        with pytest.raises(ValidationError):
            CVRecommended(
                job=object_ref("job"),
                profile=object_ref("profile"),
                cvs=tuple(object_ref("cv", index + 1) for index in range(size)),
            )


def test_evidence_reference_collection_is_bounded() -> None:
    with pytest.raises(ValidationError):
        work_event(evidence=tuple(evidence_ref(index + 1) for index in range(257)))


@pytest.mark.parametrize("value", [True, "1", 1.0, -1, 1001])
def test_counts_are_bounded_exact_integers(value: object) -> None:
    with pytest.raises(ValidationError):
        AssessmentCounts(supported=value, partial=0, gap=0, unknown=0, conflict=0)


@pytest.mark.parametrize("refs", [(), (object_ref("cv"),), (object_ref("job"), object_ref("cv"))])
def test_envelope_references_are_exactly_the_payload_objects(
    refs: tuple[BusinessObjectRef, ...],
) -> None:
    with pytest.raises(ValidationError):
        work_event(refs=refs)


def test_envelope_references_cannot_repeat_an_identity() -> None:
    with pytest.raises(ValidationError, match="repeat"):
        work_event(refs=(object_ref("job"),) * 2)


def test_reference_revision_mismatch_between_payload_and_envelope_is_rejected() -> None:
    old = object_ref("job")
    new = old.model_copy(update={"revision": 2})
    with pytest.raises(ValidationError, match="exactly match"):
        work_event(JobAdded(job=new), (old,))


def test_business_object_cannot_cross_workspace() -> None:
    foreign = object_ref("job", workspace=OTHER_WORKSPACE)
    with pytest.raises(ValidationError, match="crosses event workspace"):
        work_event(JobAdded(job=foreign), (foreign,))


def test_evidence_cannot_cross_workspace() -> None:
    with pytest.raises(ValidationError, match="crosses event workspace"):
        work_event(evidence=(evidence_ref(workspace=OTHER_WORKSPACE),))


@pytest.mark.parametrize("catalog", ["objects", "evidence"])
def test_personal_event_cannot_understate_a_sensitive_reference(catalog: str) -> None:
    job = object_ref("job", classification="personal")
    evidence = ()
    if catalog == "objects":
        job = object_ref("job", classification="sensitive")
    else:
        evidence = (evidence_ref(classification="sensitive"),)
    with pytest.raises(ValidationError, match="classification cannot understate"):
        WorkEvent(
            event_id=EventId("event_" + "1" * 32),
            workspace_id=WORKSPACE,
            actor_id=ACTOR,
            occurred_at=OCCURRED,
            recorded_at=RECORDED,
            activity="job_added",
            source="manual",
            business_objects=(job,),
            payload=JobAdded(job=job),
            privacy_classification="personal",
            evidence_refs=evidence,
        )


@pytest.mark.parametrize("envelope", ["synthetic", "personal", "sensitive"])
def test_synthetic_and_real_reference_classifications_cannot_mix(envelope: str) -> None:
    child = "personal" if envelope == "synthetic" else "synthetic"
    job = object_ref("job", classification=child)
    with pytest.raises(ValidationError, match="mix referenced data"):
        WorkEvent(
            event_id=EventId("event_" + "1" * 32),
            workspace_id=WORKSPACE,
            actor_id=ACTOR,
            occurred_at=OCCURRED,
            recorded_at=RECORDED,
            activity="job_added",
            source="manual",
            business_objects=(job,),
            payload=JobAdded(job=job),
            privacy_classification=envelope,
        )


def test_sensitive_real_event_can_reference_personal_and_sensitive_data() -> None:
    job = object_ref("job", classification="personal")
    evidence = evidence_ref(classification="sensitive")
    event = WorkEvent(
        event_id=EventId("event_" + "1" * 32),
        workspace_id=WORKSPACE,
        actor_id=ACTOR,
        occurred_at=OCCURRED,
        recorded_at=RECORDED,
        activity="job_added",
        source="manual",
        business_objects=(job,),
        payload=JobAdded(job=job),
        privacy_classification="sensitive",
        evidence_refs=(evidence,),
    )
    assert load_contract(WorkEvent, canonical_bytes(event)) == event
    validate_references(event, (job,), (evidence,))


def test_catalog_rejects_a_forged_lower_reference_classification() -> None:
    job = object_ref("job", classification="personal")
    event = WorkEvent(
        event_id=EventId("event_" + "1" * 32),
        workspace_id=WORKSPACE,
        actor_id=ACTOR,
        occurred_at=OCCURRED,
        recorded_at=RECORDED,
        activity="job_added",
        source="manual",
        business_objects=(job,),
        payload=JobAdded(job=job),
        privacy_classification="personal",
    )
    actual = job.model_copy(update={"classification": "sensitive"})
    with pytest.raises(ValueError, match="content-mismatched"):
        validate_references(event, (actual,), ())


def test_evidence_cannot_repeat_identity_with_another_revision() -> None:
    first = evidence_ref()
    second = first.model_copy(update={"revision": 2})
    with pytest.raises(ValidationError, match="repeat an evidence"):
        work_event(evidence=(first, second))


def test_fit_evidence_belongs_to_the_referenced_profile() -> None:
    event = six_events()[2]
    foreign_profile = evidence_ref().model_copy(
        update={"profile_id": ProfileId("profile_" + "2" * 32)}
    )
    with pytest.raises(ValidationError, match="different profile"):
        event.model_copy(update={"evidence_refs": (foreign_profile,)})


@pytest.mark.parametrize("index", [1, 4])
def test_review_attribution_matches_event_actor(index: int) -> None:
    event = six_events()[index]
    payload = event.payload.model_copy(update={"reviewer_id": ActorId("actor_" + "2" * 32)})
    with pytest.raises(ValidationError, match="attribution"):
        event.model_copy(update={"payload": payload})


@pytest.mark.parametrize("index", [1, 4])
def test_review_must_precede_reported_occurrence(index: int) -> None:
    event = six_events()[index]
    payload = event.payload.model_copy(update={"reviewed_at": "2026-10-01T12:01:00Z"})
    with pytest.raises(ValidationError, match="Review cannot follow"):
        event.model_copy(update={"payload": payload})


@pytest.mark.parametrize("index", [2, 4])
def test_fit_or_accepted_draft_requires_evidence_refs(index: int) -> None:
    with pytest.raises(ValidationError, match="requires evidence"):
        six_events()[index].model_copy(update={"evidence_refs": ()})


@pytest.mark.parametrize("unknown", [0, 3])
def test_unknown_only_or_empty_assessment_does_not_invent_required_evidence(unknown: int) -> None:
    counts = AssessmentCounts(supported=0, partial=0, gap=0, unknown=unknown, conflict=0)
    original = six_events()[2]
    payload = original.payload.model_copy(update={"counts": counts})
    event = original.model_copy(update={"payload": payload, "evidence_refs": ()})
    assert event.evidence_refs == ()
    assert load_contract(WorkEvent, canonical_bytes(event)) == event


@pytest.mark.parametrize("category", ["supported", "partial", "gap", "conflict"])
def test_each_nonunknown_assessment_category_requires_support_references(category: str) -> None:
    values = {"supported": 0, "partial": 0, "gap": 0, "unknown": 0, "conflict": 0}
    values[category] = 1
    counts = AssessmentCounts.model_validate(values)
    original = six_events()[2]
    payload = original.payload.model_copy(update={"counts": counts})
    with pytest.raises(ValidationError, match="requires evidence"):
        original.model_copy(update={"payload": payload, "evidence_refs": ()})


def test_rejected_draft_does_not_require_positive_support() -> None:
    draft = object_ref("draft")
    event = work_event(
        DraftReviewed(draft=draft, decision="rejected", reviewer_id=ACTOR, reviewed_at=REVIEWED),
        (draft,),
    )
    assert event.evidence_refs == ()


@pytest.mark.parametrize("state", ["reviewed", "applied", "interview", "offer", "closed"])
def test_initial_application_observation_cannot_invent_prior_state(state: str) -> None:
    with pytest.raises(ValidationError):
        ApplicationStatusRecorded(
            application=object_ref("application"),
            previous_state=None,
            state=state,
            basis="user_reported",
        )


def test_initial_preparing_observation_is_allowed() -> None:
    payload = ApplicationStatusRecorded(
        application=object_ref("application"),
        previous_state=None,
        state="preparing",
        basis="synthetic_observation",
    )
    event = work_event(payload, (payload.application,))
    assert event.payload == payload


def test_application_observation_cannot_skip_directly_to_interview() -> None:
    with pytest.raises(ValidationError, match="disallowed transition"):
        ApplicationStatusRecorded(
            application=object_ref("application"),
            previous_state="preparing",
            state="interview",
            basis="synthetic_observation",
        )


def test_external_manual_submission_is_explicit_report_not_internal_review() -> None:
    application = object_ref("application")
    payload = ApplicationStatusRecorded(
        application=application,
        previous_state="preparing",
        state="applied",
        basis="user_reported",
        external_manual=True,
    )
    event = work_event(payload, (application,))
    assert event.payload == payload
    assert "reviewed" not in json.loads(canonical_bytes(event))["payload"].values()


@pytest.mark.parametrize("value", [1, "true", None])
def test_external_manual_is_a_strict_boolean(value: object) -> None:
    with pytest.raises(ValidationError):
        ApplicationStatusRecorded(
            application=object_ref("application"),
            previous_state="preparing",
            state="applied",
            basis="user_reported",
            external_manual=value,
        )


def test_synthetic_observation_cannot_claim_external_manual_submission() -> None:
    with pytest.raises(ValidationError):
        ApplicationStatusRecorded(
            application=object_ref("application"),
            previous_state="preparing",
            state="applied",
            basis="synthetic_observation",
            external_manual=True,
        )


@pytest.mark.parametrize("field", ["revision", "content_digest"])
def test_object_catalog_rejects_stale_or_changed_snapshot(field: str) -> None:
    event = work_event()
    value = 2 if field == "revision" else "c" * 64
    newer = event.business_objects[0].model_copy(update={field: value})
    with pytest.raises(ValueError, match="missing, stale or content-mismatched"):
        validate_references(event, (newer,), ())


def test_object_catalog_rejects_missing_reference() -> None:
    with pytest.raises(ValueError, match="missing"):
        validate_references(work_event(), (), ())


@pytest.mark.parametrize("field", ["revision", "content_digest"])
def test_evidence_catalog_rejects_stale_or_changed_snapshot(field: str) -> None:
    event = six_events()[2]
    value = 2 if field == "revision" else "c" * 64
    newer = event.evidence_refs[0].model_copy(update={field: value})
    with pytest.raises(ValueError, match="Evidence reference is missing"):
        validate_references(event, event.business_objects, (newer,))


def test_evidence_catalog_rejects_missing_reference() -> None:
    event = six_events()[2]
    with pytest.raises(ValueError, match="Evidence reference is missing"):
        validate_references(event, event.business_objects, ())


@pytest.mark.parametrize("catalog", ["objects", "evidence"])
def test_catalog_cannot_introduce_foreign_workspace(catalog: str) -> None:
    event = work_event()
    objects = event.business_objects
    evidence = ()
    if catalog == "objects":
        objects += (object_ref("cv", workspace=OTHER_WORKSPACE),)
    else:
        evidence = (evidence_ref(workspace=OTHER_WORKSPACE),)
    with pytest.raises(ValueError, match="foreign workspace"):
        validate_references(event, objects, evidence)


@pytest.mark.parametrize("catalog", ["objects", "evidence"])
def test_current_catalog_cannot_supply_conflicting_revisions(catalog: str) -> None:
    event = six_events()[2]
    objects, evidence = event.business_objects, event.evidence_refs
    if catalog == "objects":
        objects += (objects[0].model_copy(update={"revision": 2}),)
    else:
        evidence += (evidence[0].model_copy(update={"revision": 2}),)
    with pytest.raises(ValueError, match="duplicate object identities"):
        validate_references(event, objects, evidence)


def test_identical_source_redelivery_ignores_new_ingestion_identity_and_time() -> None:
    prior = work_event()
    current = prior.model_copy(
        update={
            "event_id": EventId("event_" + "2" * 32),
            "recorded_at": "2026-10-02T12:00:00Z",
        }
    )
    assert delivery_relation(prior, current) == "duplicate"
    assert delivery_relation(prior, prior) == "duplicate"


def test_reordering_envelope_object_and_evidence_sets_is_same_delivery() -> None:
    original = six_events()[2].model_copy(
        update={"evidence_refs": (evidence_ref(1), evidence_ref(2))}
    )
    reordered = original.model_copy(
        update={
            "business_objects": tuple(reversed(original.business_objects)),
            "evidence_refs": tuple(reversed(original.evidence_refs)),
        }
    )
    assert original.payload == reordered.payload
    assert delivery_relation(original, reordered) == "duplicate"


def test_reordering_payload_cv_choices_retains_semantic_change() -> None:
    job, profile = object_ref("job"), object_ref("profile")
    first_cv, second_cv = object_ref("cv", 1), object_ref("cv", 2)
    payload = CVRecommended(job=job, profile=profile, cvs=(first_cv, second_cv))
    original = work_event(payload, (job, profile, first_cv, second_cv))
    changed = original.model_copy(
        update={"payload": payload.model_copy(update={"cvs": (second_cv, first_cv)})}
    )
    assert delivery_relation(original, changed) == "conflict"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("actor_id", ActorId("actor_" + "2" * 32)),
        ("occurred_at", "2026-10-01T12:01:00Z"),
        ("correlation_id", CorrelationId("correlation_" + "2" * 32)),
        ("evidence_refs", (evidence_ref(),)),
    ],
)
def test_same_source_identity_with_changed_attribution_or_content_is_conflict(
    field: str, value: object
) -> None:
    prior = work_event()
    changed = prior.model_copy(update={field: value})
    assert delivery_relation(prior, changed) == "conflict"


def test_same_source_identity_with_changed_payload_snapshot_is_conflict() -> None:
    prior = work_event()
    changed_ref = object_ref("job").model_copy(update={"revision": 2})
    current = prior.model_copy(
        update={"payload": JobAdded(job=changed_ref), "business_objects": (changed_ref,)}
    )
    assert delivery_relation(prior, current) == "conflict"


def test_changed_permitted_event_privacy_classification_is_conflict() -> None:
    job = object_ref("job", classification="personal")
    prior = WorkEvent(
        event_id=EventId("event_" + "1" * 32),
        workspace_id=WORKSPACE,
        actor_id=ACTOR,
        occurred_at=OCCURRED,
        recorded_at=RECORDED,
        activity="job_added",
        source="manual",
        business_objects=(job,),
        payload=JobAdded(job=job),
        privacy_classification="personal",
        source_event_id=SourceEventId("source_event_" + "1" * 32),
    )
    changed = prior.model_copy(update={"privacy_classification": "sensitive"})
    assert delivery_relation(prior, changed) == "conflict"


@pytest.mark.parametrize("field", ["workspace_id", "source", "source_event_id"])
def test_different_scoped_source_identity_is_unrelated(field: str) -> None:
    prior = work_event()
    if field == "workspace_id":
        new_ref = object_ref("job", workspace=OTHER_WORKSPACE)
        current = prior.model_copy(
            update={
                "workspace_id": OTHER_WORKSPACE,
                "payload": JobAdded(job=new_ref),
                "business_objects": (new_ref,),
            }
        )
    else:
        value = "careerlab" if field == "source" else SourceEventId("source_event_" + "2" * 32)
        current = prior.model_copy(update={field: value})
    assert delivery_relation(prior, current) == "unrelated"


def test_missing_source_identity_does_not_claim_deduplication() -> None:
    prior = work_event()
    missing = prior.model_copy(update={"source_event_id": None})
    assert delivery_relation(prior, missing) == "unrelated"
    assert delivery_relation(missing, prior) == "unrelated"
    assert delivery_relation(missing, missing) == "unrelated"


def test_observation_cannot_be_mutated_into_permission() -> None:
    event = work_event()
    with pytest.raises(ValidationError):
        event.source = "careerlab"
    with pytest.raises(ValidationError):
        event.model_copy(update={"authorized": True})
    with pytest.raises(TypeError):
        WorkEvent.model_construct(authorized=True)
