"""Synthetic profile reviews and projections use real atomic PostgreSQL state."""

import json
import re
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import Engine

from actual.api.app import create_app
from actual.api.config import ApiSettings
from actual.api.wiring import StoreAdapter
from actual.career.materials import CVVariant
from actual.core.primitives import ActorId, CVId, WorkspaceId, canonical_bytes
from actual.job_intelligence.matching import match_requirements
from actual.job_intelligence.normalize import normalize_requirement
from actual.persistence.repository import CareerStore
from actual.profile.contracts import Claim, EvidenceRecord, Profile, claim_ref, evidence_ref
from actual.profile.experience import ExperienceContext
from actual.profile.projection import EvidenceBackedProfileView

BASE = "http://127.0.0.1:8765"
OWNER = WorkspaceId("workspace_" + "7" * 32)
ACTOR = ActorId("actor_" + "6" * 32)
NOW = datetime(2026, 10, 6, 12, tzinfo=UTC)
PRIVATE = "PRIVATE_PROFILE_INTEGRATION_3a62"
PYTHON = {"kind": "skill", "subject": "python", "unit": "skill_level", "value": 2}


def identifier(kind: str, number: int = 1) -> str:
    return f"{kind}_{number:032x}"


@pytest.fixture
def profile_api(pg_engine: Engine) -> Iterator[TestClient]:
    app = create_app(
        ApiSettings(workspace_id=OWNER, actor_id=ACTOR), engine=pg_engine, clock=lambda: NOW
    )
    with TestClient(
        app, base_url=BASE, client=("127.0.0.1", 50000), raise_server_exceptions=False
    ) as client:
        yield client


def initialize(client: TestClient) -> None:
    response = client.post(
        "/api/v1/career",
        json={
            "expected_generation": 0,
            "profile": {"id": identifier("profile"), "name": "Explicitly synthetic profile"},
            "job": {
                "id": identifier("job"),
                "opportunity_id": identifier("opportunity"),
                "company": {
                    "id": identifier("company"),
                    "name": "Fabricated employer",
                    "context": "Synthetic company context.",
                },
                "title": "Synthetic engineer",
                "text": "Python at working level is essential.",
                "source_reference": "synthetic:profile-integration-job",
                "posted_at": "2026-10-01T10:00:00Z",
            },
        },
    )
    assert response.status_code == 201, response.text


def create_claim(client: TestClient, generation: int, assertion: dict = PYTHON) -> dict:
    payload = {
        "expected_generation": generation,
        "id": identifier("claim"),
        "assertion": assertion,
        "text": "Fabricated candidate declaration; it remains a claim.",
    }
    response = client.post("/api/v1/profile/claims", json=payload)
    assert response.status_code == 201, response.text
    return payload


def attach(
    client: TestClient,
    generation: int,
    *,
    number: int = 1,
    assertion: dict = PYTHON,
    source_kind: str = "synthetic_fixture",
    relation: str = "supports",
    context: dict | None = None,
) -> dict:
    payload = {
        "expected_generation": generation,
        "id": identifier("evidence", number),
        "claim_id": identifier("claim"),
        "assertion": assertion,
        "relation": relation,
        "source_kind": source_kind,
        "source_reference": f"synthetic:profile-integration-source:{number}",
        "excerpt": "Fabricated structured support; no external document is fetched.",
        "collected_at": "2026-10-05T10:00:00+02:00",
    }
    if context is not None:
        payload["experience_context"] = context
    response = client.post("/api/v1/profile/evidence", json=payload)
    assert response.status_code == 201, response.text
    return payload


def seed(
    client: TestClient,
    *,
    assertion: dict = PYTHON,
    evidence_assertion: dict | None = None,
    source_kind: str = "synthetic_fixture",
    context: dict | None = None,
) -> None:
    initialize(client)
    create_claim(client, 1, assertion)
    attach(
        client,
        2,
        assertion=assertion if evidence_assertion is None else evidence_assertion,
        source_kind=source_kind,
        context=context,
    )


def bound(generation: int, record: Claim | EvidenceRecord) -> dict:
    return {
        "schema_version": "actual-api-v1",
        "expected_generation": generation,
        "expected_revision": record.revision,
        "expected_digest": record.snapshot_digest,
    }


def evidence_command(
    client: TestClient, store: CareerStore, suffix: str, *, number: int = 1
) -> object:
    state = store.load()
    record = next(
        record
        for record in state.snapshot.profile.evidence
        if record.id.root == identifier("evidence", number)
    )
    return client.post(
        f"/api/v1/profile/evidence/{record.id.root}/{suffix}",
        json=bound(state.generation, record),
    )


def claim_command(client: TestClient, store: CareerStore) -> object:
    state = store.load()
    claim = state.snapshot.profile.claims[0]
    return client.post(
        f"/api/v1/profile/claims/{claim.id.root}/synthetic-review",
        json=bound(state.generation, claim),
    )


def safe_failure(response: object, status: int, code: str | None = None) -> dict:
    assert response.status_code == status, response.text
    payload = response.json()
    assert set(payload) == {"schema_version", "error", "request_id"}
    assert set(payload["error"]) == {"code", "message"}
    assert re.fullmatch(r"[0-9a-f]{32}", payload["request_id"])
    assert response.headers["x-request-id"] == payload["request_id"]
    assert response.headers["cache-control"] == "no-store"
    if code is not None:
        assert payload["error"]["code"] == code
    for forbidden in (PRIVATE, "Traceback", "psycopg", "password=", "SELECT ", "UPDATE "):
        assert forbidden not in response.text
    return payload


def roundtrip_profile(response: object, store: CareerStore) -> Profile:
    assert response.status_code == 200, response.text
    payload = response.json()
    checked = Profile.model_validate_json(json.dumps(payload["profile"]))
    state = store.load()
    assert payload["generation"] == state.generation
    assert canonical_bytes(checked) == canonical_bytes(state.snapshot.profile)
    return checked


def test_synthetic_source_and_claim_reviews_are_separate_durable_operations(
    profile_api: TestClient, pg_engine: Engine
) -> None:
    seed(profile_api)
    store = CareerStore(pg_engine, OWNER)
    before = store.load()
    original_claim = before.snapshot.profile.claims[0]
    original_evidence = before.snapshot.profile.evidence[0]
    safe_failure(claim_command(profile_api, store), 409)
    assert store.load() == before

    reviewed = roundtrip_profile(evidence_command(profile_api, store, "synthetic-review"), store)
    source, declaration = reviewed.evidence[0], reviewed.claims[0]
    assert source.qualifies_support
    assert source.review is not None
    assert source.review.kind == "synthetic_review"
    assert source.review.method == "explicit_synthetic_source_review_v1"
    assert source.review.reviewer_id == ACTOR
    assert source.review.reviewed_at == NOW
    assert source.review.independent_source_reference is None
    assert source.content_digest == original_evidence.content_digest
    assert source.snapshot_digest != original_evidence.snapshot_digest
    assert declaration.origin == "user_report" and declaration.status == "self_reported"
    assert declaration.review is None
    assert declaration.revision == original_claim.revision + 1
    assert declaration.evidence_refs == (evidence_ref(source),)

    accepted = roundtrip_profile(claim_command(profile_api, store), store)
    claim = accepted.claims[0]
    assert claim.status == "reviewed_supported"
    assert claim.review is not None
    assert claim.review.reviewer_id == ACTOR
    assert claim.review.reviewed_at == NOW
    assert claim.review.method == "explicit_synthetic_claim_review_v1"
    assert claim.origin == "user_report"  # Review does not rewrite origin into fact provenance.
    assert claim.evidence_refs == (evidence_ref(accepted.evidence[0]),)
    assert store.load().generation == 5
    assert len(store.load_events()) == 1  # The initial job observation; no invented event kind.


@pytest.mark.parametrize(
    "source_kind", ["user_report", "ai_proposal", "project_artifact", "imported_document"]
)
def test_review_cannot_certify_nonfixture_provenance(
    profile_api: TestClient, pg_engine: Engine, source_kind: str
) -> None:
    seed(profile_api, source_kind=source_kind)
    store = CareerStore(pg_engine, OWNER)
    before = store.load()
    safe_failure(evidence_command(profile_api, store, "synthetic-review"), 409)
    safe_failure(claim_command(profile_api, store), 409)
    assert store.load() == before
    assert before.snapshot.profile.evidence[0].review is None
    assert not before.snapshot.profile.evidence[0].qualifies_support
    assert before.snapshot.profile.claims[0].status == "self_reported"


def test_revision_digest_and_generation_bindings_reject_stale_reviews_atomically(
    profile_api: TestClient, pg_engine: Engine
) -> None:
    seed(profile_api)
    store = CareerStore(pg_engine, OWNER)
    before = store.load()
    record = before.snapshot.profile.evidence[0]
    route = f"/api/v1/profile/evidence/{record.id.root}/synthetic-review"
    for replacement in (
        {"expected_generation": before.generation - 1},
        {"expected_revision": record.revision + 1},
        {"expected_digest": record.content_digest},
    ):
        safe_failure(
            profile_api.post(route, json={**bound(before.generation, record), **replacement}), 409
        )
        assert store.load() == before
    response = profile_api.post(route, json=bound(before.generation, record))
    assert response.status_code == 200, response.text
    after = store.load()
    safe_failure(profile_api.post(route, json=bound(after.generation, record)), 409)
    assert store.load() == after


def test_source_withdrawal_invalidates_claim_review_and_current_references(
    profile_api: TestClient, pg_engine: Engine
) -> None:
    seed(profile_api)
    store = CareerStore(pg_engine, OWNER)
    assert evidence_command(profile_api, store, "synthetic-review").status_code == 200
    assert claim_command(profile_api, store).status_code == 200
    previous = store.load().snapshot.profile
    changed = roundtrip_profile(evidence_command(profile_api, store, "withdraw"), store)
    assert changed.evidence[0].status == "withdrawn"
    assert changed.evidence[0].review == previous.evidence[0].review
    assert not changed.evidence[0].qualifies_support
    assert changed.claims[0].status == "candidate_support"
    assert changed.claims[0].review is None
    assert changed.claims[0].evidence_refs == (evidence_ref(changed.evidence[0]),)
    assert claim_ref(changed.claims[0]) != claim_ref(previous.claims[0])
    assert evidence_ref(changed.evidence[0]) != evidence_ref(previous.evidence[0])
    before = store.load()
    safe_failure(claim_command(profile_api, store), 409)
    assert store.load() == before


def test_reviewed_contrary_source_cannot_be_hidden_and_withdrawal_does_not_reaccept(
    profile_api: TestClient, pg_engine: Engine
) -> None:
    seed(profile_api)
    attach(profile_api, 3, number=2, relation="contradicts")
    store = CareerStore(pg_engine, OWNER)
    assert evidence_command(profile_api, store, "synthetic-review").status_code == 200
    assert claim_command(profile_api, store).status_code == 200
    conflicted = roundtrip_profile(
        evidence_command(profile_api, store, "synthetic-review", number=2), store
    )
    claim = conflicted.claims[0]
    assert claim.status == "contradicted" and claim.review is None
    assert {ref.evidence_id for ref in claim.evidence_refs} == {
        record.id for record in conflicted.evidence
    }
    before = store.load()
    safe_failure(claim_command(profile_api, store), 409)
    assert store.load() == before
    changed = roundtrip_profile(evidence_command(profile_api, store, "withdraw", number=2), store)
    assert changed.claims[0].status != "reviewed_supported"
    assert changed.claims[0].review is None
    assert all(
        ref
        == evidence_ref(next(record for record in changed.evidence if record.id == ref.evidence_id))
        for ref in changed.claims[0].evidence_refs
    )


def test_review_requires_material_dependency_reconciliation(
    profile_api: TestClient, pg_engine: Engine
) -> None:
    seed(profile_api)
    store = CareerStore(pg_engine, OWNER)
    state = store.load()
    profile = state.snapshot.profile
    cv = CVVariant(
        id=CVId(identifier("cv")),
        workspace_id=OWNER,
        profile_id=profile.id,
        revision=1,
        classification="synthetic",
        name="Synthetic metadata only",
        summary="No CV generation occurs.",
        claim_refs=(claim_ref(profile.claims[0]),),
    )
    store.save(
        state.snapshot.model_copy(update={"cvs": (cv,)}), expected_generation=state.generation
    )
    before = store.load()
    safe_failure(
        evidence_command(profile_api, store, "synthetic-review"),
        409,
        "DEPENDENCY_RECONCILIATION_REQUIRED",
    )
    safe_failure(
        evidence_command(profile_api, store, "withdraw"),
        409,
        "DEPENDENCY_RECONCILIATION_REQUIRED",
    )
    assert store.load() == before
    assert store.load().snapshot.cvs == (cv,)


def test_duplicate_claim_and_evidence_ids_preserve_state(
    profile_api: TestClient, pg_engine: Engine
) -> None:
    initialize(profile_api)
    claim_payload = create_claim(profile_api, 1)
    store = CareerStore(pg_engine, OWNER)
    before = store.load()
    safe_failure(
        profile_api.post(
            "/api/v1/profile/claims", json={**claim_payload, "expected_generation": 2}
        ),
        409,
        "DUPLICATE_RESOURCE",
    )
    assert store.load() == before
    evidence_payload = attach(profile_api, 2)
    before = store.load()
    safe_failure(
        profile_api.post(
            "/api/v1/profile/evidence", json={**evidence_payload, "expected_generation": 3}
        ),
        409,
        "DUPLICATE_RESOURCE",
    )
    assert store.load() == before


def test_profile_source_review_and_ref_reconciliation_roll_back_at_commit(
    profile_api: TestClient, pg_engine: Engine, caplog: pytest.LogCaptureFixture
) -> None:
    seed(profile_api)
    store = CareerStore(pg_engine, OWNER)
    before = store.load()
    events = store.load_events()
    with pg_engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE FUNCTION profile_test_reject_commit() RETURNS trigger LANGUAGE plpgsql AS $$ "
            "BEGIN RAISE EXCEPTION 'PRIVATE_PROFILE_INTEGRATION_3a62' USING ERRCODE = '23514'; "
            "END $$"
        )
        connection.exec_driver_sql(
            "CREATE CONSTRAINT TRIGGER profile_test_commit_failure AFTER UPDATE ON evidence "
            "DEFERRABLE INITIALLY DEFERRED FOR EACH ROW "
            "EXECUTE FUNCTION profile_test_reject_commit()"
        )
    safe_failure(evidence_command(profile_api, store, "synthetic-review"), 409)
    assert store.load() == before
    assert store.load_events() == events
    assert before.snapshot.profile.evidence[0].review is None
    assert before.snapshot.profile.claims[0].evidence_refs == (
        evidence_ref(before.snapshot.profile.evidence[0]),
    )
    assert PRIVATE not in caplog.text


def test_two_pinned_source_reviews_have_one_committed_winner(
    profile_api: TestClient, pg_engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed(profile_api)
    store = CareerStore(pg_engine, OWNER)
    before = store.load()
    record = before.snapshot.profile.evidence[0]
    barrier = Barrier(2)
    original_load = StoreAdapter.load

    def synchronized_load(self: StoreAdapter) -> object:
        state = original_load(self)
        if state is not None and state.generation == before.generation:
            barrier.wait(timeout=10)
        return state

    monkeypatch.setattr(StoreAdapter, "load", synchronized_load)

    def review(_: int) -> object:
        return profile_api.post(
            f"/api/v1/profile/evidence/{record.id.root}/synthetic-review",
            json=bound(before.generation, record),
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(review, (1, 2)))
    assert sorted(response.status_code for response in responses) == [200, 409]
    safe_failure(next(response for response in responses if response.status_code == 409), 409)
    after = store.load()
    assert after.generation == before.generation + 1
    assert after.snapshot.profile.evidence[0].revision == record.revision + 1
    assert after.snapshot.profile.evidence[0].review is not None
    assert after.snapshot.profile.claims[0].status == "self_reported"
    assert after.snapshot.profile.claims[0].evidence_refs == (
        evidence_ref(after.snapshot.profile.evidence[0]),
    )


def test_clock_regression_blocks_source_review_without_changing_state(
    pg_engine: Engine,
) -> None:
    app = create_app(
        ApiSettings(workspace_id=OWNER, actor_id=ACTOR), engine=pg_engine, clock=lambda: NOW
    )
    with TestClient(
        app, base_url=BASE, client=("127.0.0.1", 50000), raise_server_exceptions=False
    ) as client:
        seed(client)
    store = CareerStore(pg_engine, OWNER)
    before = store.load()
    backwards_app = create_app(
        ApiSettings(workspace_id=OWNER, actor_id=ACTOR),
        engine=pg_engine,
        clock=lambda: NOW - timedelta(seconds=1),
    )
    with TestClient(
        backwards_app, base_url=BASE, client=("127.0.0.1", 50000), raise_server_exceptions=False
    ) as client:
        safe_failure(evidence_command(client, store, "synthetic-review"), 422)
    assert store.load() == before


def test_experience_context_roundtrips_and_cannot_keep_a_stale_source_review(
    profile_api: TestClient, pg_engine: Engine
) -> None:
    assertion = {"kind": "experience", "subject": "experience", "unit": "months", "value": 6}
    context = {
        "context_version": "actual-experience-context-v1",
        "category": "internship",
        "started_at": "2025-01-01T12:00:00+02:00",
        "ended_at": "2025-06-30T12:00:00+02:00",
        "ongoing": False,
    }
    seed(profile_api, assertion=assertion, context=context)
    store = CareerStore(pg_engine, OWNER)
    source = store.load().snapshot.profile.evidence[0]
    assert source.experience_context is not None
    assert source.experience_context.category == "internship"
    assert source.experience_context.started_at == datetime(2025, 1, 1, 10, tzinfo=UTC)
    assert source.experience_context.ended_at == datetime(2025, 6, 30, 10, tzinfo=UTC)
    assert source.experience_context.ongoing is False
    reviewed = roundtrip_profile(evidence_command(profile_api, store, "synthetic-review"), store)
    changed_context = ExperienceContext(
        context_version="actual-experience-context-v1",
        category="personal_project",
    )
    with pytest.raises(ValidationError):
        reviewed.evidence[0].model_copy(update={"experience_context": changed_context})
    cleared = reviewed.evidence[0].model_copy(
        update={
            "revision": reviewed.evidence[0].revision + 1,
            "experience_context": changed_context,
            "review": None,
        }
    )
    assert cleared.content_digest != reviewed.evidence[0].content_digest
    assert not cleared.qualifies_support
    assert evidence_ref(cleared) != evidence_ref(reviewed.evidence[0])


def test_legacy_evidence_keeps_absent_context_and_original_wire_digest(
    profile_api: TestClient, pg_engine: Engine
) -> None:
    seed(profile_api)
    store = CareerStore(pg_engine, OWNER)
    source = store.load().snapshot.profile.evidence[0]
    assert source.experience_context is None
    wire = source.model_dump(mode="json")
    assert "experience_context" not in wire
    original_bytes = canonical_bytes(source)
    restored = EvidenceRecord.model_validate_json(json.dumps(wire))
    assert canonical_bytes(restored) == original_bytes
    assert restored.content_digest == source.content_digest
    response = profile_api.get("/api/v1/profile")
    assert response.status_code == 200
    assert "experience_context" not in response.json()["profile"]["evidence"][0]


def projection(client: TestClient) -> EvidenceBackedProfileView:
    response = client.get("/api/v1/profile/evidence")
    assert response.status_code == 200, response.text
    payload = response.json()
    assert set(payload) == {"schema_version", "generation", "profile"}
    assert payload["schema_version"] == "actual-api-v1"
    return EvidenceBackedProfileView.model_validate_json(json.dumps(payload["profile"]))


def test_projection_distinguishes_declaration_source_review_and_claim_support(
    profile_api: TestClient, pg_engine: Engine
) -> None:
    seed(profile_api)
    store = CareerStore(pg_engine, OWNER)
    before = store.load()
    original = projection(profile_api)
    row = next(row for row in original.rows if row.subject == "python")
    assert row.state == "unverified"
    assert row.supported_value is None
    assert row.reviewed_source_value is None
    assert not row.eligible_claim_refs and not row.eligible_evidence_refs
    assert row.unreviewed_evidence_refs == (evidence_ref(before.snapshot.profile.evidence[0]),)
    assert canonical_bytes(projection(profile_api)) == canonical_bytes(original)
    assert store.load() == before  # Computing the view is read-only.

    assert evidence_command(profile_api, store, "synthetic-review").status_code == 200
    source_only = projection(profile_api)
    row = next(row for row in source_only.rows if row.subject == "python")
    assert row.state == "unverified"
    assert row.supported_value is None and row.reviewed_source_value == 2
    assert not row.eligible_claim_refs and not row.eligible_evidence_refs
    assert row.reviewed_source_refs == (evidence_ref(store.load().snapshot.profile.evidence[0]),)

    assert claim_command(profile_api, store).status_code == 200
    reviewed = store.load().snapshot.profile
    row = next(row for row in projection(profile_api).rows if row.subject == "python")
    assert row.state == "supported" and row.supported_value == 2
    assert row.eligible_claim_refs == (claim_ref(reviewed.claims[0]),)
    assert row.eligible_evidence_refs == (evidence_ref(reviewed.evidence[0]),)
    job = store.load().snapshot.jobs[0]
    requirement = normalize_requirement(job, quote=job.text, term="Python", priority="essential")
    assessment = match_requirements(job, reviewed, (requirement,))
    assert assessment.rows[0].status == "supported"
    assert assessment.rows[0].claim_refs == row.eligible_claim_refs
    assert assessment.rows[0].evidence_refs == row.eligible_evidence_refs
    assert assessment.proposal_only is True


def test_french_b2_declaration_and_a2_source_remain_visible_without_flattering_promotion(
    profile_api: TestClient, pg_engine: Engine
) -> None:
    b2 = {"kind": "language", "subject": "french", "unit": "cefr_level", "value": 4}
    a2 = {**b2, "value": 2}
    seed(profile_api, assertion=b2, evidence_assertion=a2)
    store = CareerStore(pg_engine, OWNER)
    assert evidence_command(profile_api, store, "synthetic-review").status_code == 200
    before = store.load()
    row = next(row for row in projection(profile_api).rows if row.subject == "french")
    assert row.state == "unverified"
    assert row.declaration_exceeds_support is True
    assert row.supported_value is None and row.reviewed_source_value == 2
    assert [declaration.assertion.value for declaration in row.declarations] == [4]
    assert row.reviewed_source_refs == (evidence_ref(before.snapshot.profile.evidence[0]),)
    assert not row.eligible_claim_refs and not row.eligible_evidence_refs
    assert not row.contrary_evidence_refs  # A lower credential is not proof of inability.
    safe_failure(claim_command(profile_api, store), 409)
    assert store.load() == before
    assert before.snapshot.profile.claims[0].assertion.value == 4
    assert before.snapshot.profile.claims[0].status == "self_reported"


def test_experience_projection_preserves_overlapping_categories_without_accumulation(
    profile_api: TestClient, pg_engine: Engine
) -> None:
    six_months = {"kind": "experience", "subject": "experience", "unit": "months", "value": 6}
    common = {
        "context_version": "actual-experience-context-v1",
        "started_at": "2025-01-01T00:00:00Z",
        "ended_at": "2025-06-30T00:00:00Z",
        "ongoing": False,
    }
    seed(profile_api, assertion=six_months, context={**common, "category": "internship"})
    attach(
        profile_api,
        3,
        number=2,
        assertion={**six_months, "value": 24},
        context={
            "context_version": "actual-experience-context-v1",
            "category": "personal_project",
            "started_at": "2024-01-01T00:00:00Z",
            "ongoing": True,
        },
    )
    store = CareerStore(pg_engine, OWNER)
    assert evidence_command(profile_api, store, "synthetic-review").status_code == 200
    assert evidence_command(profile_api, store, "synthetic-review", number=2).status_code == 200
    before = store.load()
    safe_failure(claim_command(profile_api, store), 409)
    assert store.load() == before
    view = projection(profile_api)
    assert {record.context.category for record in view.experience} == {
        "internship",
        "personal_project",
    }
    project = next(
        record for record in view.experience if record.context.category == "personal_project"
    )
    assert project.context.ongoing is True and project.context.ended_at is None
    row = next(row for row in view.rows if row.subject == "experience")
    assert row.supported_value is None and row.reviewed_source_value is None
    assert not row.eligible_claim_refs and not row.eligible_evidence_refs
    assert row.contextual_evidence_refs == tuple(
        evidence_ref(record) for record in before.snapshot.profile.evidence
    )
    assert all(record.qualifies_review for record in view.experience)
    assert "professional_months" not in view.model_dump(mode="json")
    state = store.load()
    job = state.snapshot.jobs[0].model_copy(
        update={"text": "Five years of professional experience are essential."}
    )
    requirement = normalize_requirement(
        job, quote=job.text, term="professional experience", priority="essential"
    )
    assert requirement.resolution == "abstained"
    assessment = match_requirements(job, state.snapshot.profile, (requirement,))
    assert assessment.rows[0].status == "unknown"
    assert not assessment.rows[0].evidence_refs


def test_review_routes_cannot_use_foreign_workspace_record_ids(
    profile_api: TestClient, pg_engine: Engine
) -> None:
    seed(profile_api)
    store = CareerStore(pg_engine, OWNER)
    before = store.load()
    foreign_app = create_app(
        ApiSettings(workspace_id=WorkspaceId("workspace_" + "a" * 32), actor_id=ACTOR),
        engine=pg_engine,
        clock=lambda: NOW,
    )
    record, claim = before.snapshot.profile.evidence[0], before.snapshot.profile.claims[0]
    with TestClient(
        foreign_app, base_url=BASE, client=("127.0.0.1", 50000), raise_server_exceptions=False
    ) as foreign:
        safe_failure(
            foreign.post(
                f"/api/v1/profile/evidence/{record.id.root}/synthetic-review",
                json=bound(before.generation, record),
            ),
            404,
        )
        safe_failure(
            foreign.post(
                f"/api/v1/profile/claims/{claim.id.root}/synthetic-review",
                json=bound(before.generation, claim),
            ),
            404,
        )
        safe_failure(foreign.get("/api/v1/profile/evidence"), 404)
    assert store.load() == before


def test_new_profile_projection_and_review_routes_preserve_real_data_guard(
    profile_api: TestClient, pg_engine: Engine
) -> None:
    initialize(profile_api)
    source = CareerStore(pg_engine, OWNER).load().snapshot
    other = WorkspaceId("workspace_" + "b" * 32)
    companies = tuple(
        company.model_copy(update={"workspace_id": other, "classification": "personal"})
        for company in source.companies
    )
    jobs = tuple(
        job.model_copy(update={"workspace_id": other, "classification": "personal"})
        for job in source.jobs
    )
    personal = source.model_copy(
        update={
            "workspace_id": other,
            "classification": "personal",
            "companies": companies,
            "jobs": jobs,
            "profile": source.profile.model_copy(
                update={"workspace_id": other, "classification": "personal"}
            ),
        }
    )
    CareerStore(pg_engine, other).save(personal, expected_generation=0)
    app = create_app(
        ApiSettings(workspace_id=other, actor_id=ACTOR), engine=pg_engine, clock=lambda: NOW
    )
    with TestClient(
        app, base_url=BASE, client=("127.0.0.1", 50000), raise_server_exceptions=False
    ) as client:
        safe_failure(client.get("/api/v1/profile/evidence"), 403, "SYNTHETIC_ONLY")
        body = {"expected_generation": 1, "expected_revision": 1, "expected_digest": "a" * 64}
        for route in (
            f"/api/v1/profile/evidence/{identifier('evidence')}/synthetic-review",
            f"/api/v1/profile/claims/{identifier('claim')}/synthetic-review",
            f"/api/v1/profile/evidence/{identifier('evidence')}/withdraw",
        ):
            safe_failure(client.post(route, json=body), 403, "SYNTHETIC_ONLY")


def test_invalid_temporal_context_and_future_collection_never_commit_evidence(
    profile_api: TestClient, pg_engine: Engine
) -> None:
    initialize(profile_api)
    assertion = {"kind": "experience", "subject": "experience", "unit": "months", "value": 6}
    create_claim(profile_api, 1, assertion)
    store = CareerStore(pg_engine, OWNER)
    before = store.load()
    payload = {
        "expected_generation": before.generation,
        "id": identifier("evidence"),
        "claim_id": identifier("claim"),
        "assertion": assertion,
        "relation": "supports",
        "source_kind": "synthetic_fixture",
        "source_reference": "synthetic:invalid-temporal-source",
        "excerpt": "Fabricated temporal metadata; invalid observations must be rejected.",
        "collected_at": "2026-10-05T10:00:00Z",
    }
    context = {"context_version": "actual-experience-context-v1", "category": "internship"}
    for changed in (
        {"context_version": "actual-experience-context-v999"},
        {"category": "employment-plus-projects"},
        {"started_at": "2025-01-01T00:00:00"},
        {"started_at": "2025-06-01T00:00:00Z", "ended_at": "2025-01-01T00:00:00Z"},
        {"ended_at": "2025-06-01T00:00:00Z", "ongoing": True},
        {"started_at": "2026-10-06T00:00:00Z"},
        {"ongoing": "true"},
    ):
        safe_failure(
            profile_api.post(
                "/api/v1/profile/evidence",
                json={**payload, "experience_context": {**context, **changed}},
            ),
            422,
        )
        assert store.load() == before
    safe_failure(
        profile_api.post(
            "/api/v1/profile/evidence", json={**payload, "collected_at": "2026-10-07T00:00:00Z"}
        ),
        422,
    )
    assert store.load() == before
