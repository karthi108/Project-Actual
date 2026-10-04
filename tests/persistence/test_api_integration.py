"""HTTP use cases commit against the accepted real-PostgreSQL repository."""

import json
import re
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, func, select

from actual.api.app import create_app
from actual.api.config import ApiSettings
from actual.api.wiring import StoreAdapter
from actual.career.jobs import Company, Job
from actual.career.snapshot import CareerSnapshot
from actual.careerlab.generator import generate_inputs
from actual.careerlab_bridge import ImportContext, map_observable
from actual.core.primitives import (
    ActorId,
    CompanyId,
    JobId,
    ProfileId,
    WorkspaceId,
    canonical_bytes,
)
from actual.persistence import schema
from actual.persistence.errors import CorruptStorageError
from actual.persistence.repository import CareerStore
from actual.profile.contracts import Profile

BASE = "http://127.0.0.1:8765"
OWNER = WorkspaceId("workspace_" + "9" * 32)
ACTOR = ActorId("actor_" + "8" * 32)
NOW = datetime(2026, 10, 4, 12, tzinfo=UTC)
PRIVATE = "PRIVATE_API_INPUT_28f64"


def identifier(kind: str, number: int) -> str:
    return f"{kind}_{number:032x}"


def manual_job(number: int = 1, company: int = 1) -> dict:
    return {
        "id": identifier("job", number),
        "opportunity_id": identifier("opportunity", number),
        "company": {
            "id": identifier("company", company),
            "name": f"Synthetic Company {company}",
            "context": "Fabricated company context for API tests.",
        },
        "title": f"Synthetic Engineer {number}",
        "text": "Fabricated posting requires Python development. No external opportunity exists.",
        "source_reference": "manual:synthetic-api-posting",
        "posted_at": "2026-10-01T10:00:00+02:00",
    }


def initialize(http: TestClient) -> dict:
    response = http.post(
        "/api/v1/career",
        json={
            "expected_generation": 0,
            "profile": {"id": identifier("profile", 1), "name": "Explicitly synthetic candidate"},
            "job": manual_job(),
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture
def api(pg_engine: Engine) -> Iterator[TestClient]:
    app = create_app(
        ApiSettings(workspace_id=OWNER, actor_id=ACTOR), engine=pg_engine, clock=lambda: NOW
    )
    with TestClient(
        app, base_url=BASE, client=("127.0.0.1", 50000), raise_server_exceptions=False
    ) as http:
        yield http


def failure(response: object, status: int) -> dict:
    assert response.status_code == status, response.text
    value = response.json()
    assert set(value) == {"schema_version", "request_id", "error"}
    assert value["schema_version"] == "actual-api-v1"
    assert set(value["error"]) == {"code", "message"}
    assert value["error"]["code"]
    assert re.fullmatch(r"[0-9a-f]{32}", value["request_id"])
    assert value["request_id"] == response.headers["x-request-id"]
    assert response.headers["cache-control"] == "no-store"
    assert PRIVATE not in response.text
    for forbidden in ("Traceback", "psycopg", "password=", "SELECT ", "INSERT ", "K:\\"):
        assert forbidden not in response.text
    return value


def test_initialization_is_typed_synthetic_and_durably_roundtrips(
    api: TestClient, pg_engine: Engine
) -> None:
    created = initialize(api)
    assert created["generation"] == 1
    snapshot = CareerSnapshot.model_validate_json(json.dumps(created["snapshot"]))
    assert snapshot.workspace_id == OWNER
    assert snapshot.classification == "synthetic"
    assert snapshot.jobs[0].posted_at == datetime(2026, 10, 1, 8, tzinfo=UTC)
    assert snapshot.profile.claims == snapshot.profile.evidence == ()
    assert snapshot.requirements == snapshot.cvs == snapshot.drafts == ()
    persisted = CareerStore(pg_engine, OWNER).load()
    assert canonical_bytes(persisted.snapshot) == canonical_bytes(snapshot)
    assert api.get("/api/v1/career").json() == created
    events = api.get("/api/v1/events").json()["items"]
    assert len(events) == 1
    assert events[0]["activity"] == "job_added"
    assert events[0]["actor_id"] == ACTOR.root
    assert events[0]["workspace_id"] == OWNER.root


def test_observable_careerlab_snapshot_is_readable_without_answers_or_review_rewriting(
    api: TestClient, pg_engine: Engine
) -> None:
    # This is an accepted public development input, never a held-out example.
    snapshot = map_observable(
        generate_inputs()[0], ImportContext(workspace_id=OWNER, actor_id=ACTOR)
    )
    store = CareerStore(pg_engine, OWNER)
    store.save(snapshot, expected_generation=0)
    response = api.get("/api/v1/career")
    assert response.status_code == 200
    observed = CareerSnapshot.model_validate_json(json.dumps(response.json()["snapshot"]))
    assert canonical_bytes(observed) == canonical_bytes(snapshot)
    assert observed.cvs  # Accepted CV metadata is read through the aggregate, without editing.
    keys: set[str] = set()
    pending: list[object] = [response.json()]
    while pending:
        item = pending.pop()
        if isinstance(item, dict):
            keys.update(item)
            pending.extend(item.values())
        elif isinstance(item, list):
            pending.extend(item)
    assert not keys & {
        "recruiter_outcome",
        "fit_label",
        "rubric",
        "lineage",
        "edge_case_category",
        "hidden_truth",
    }
    claim = next(claim for claim in snapshot.profile.claims if claim.review is not None)
    failure(
        api.post(
            "/api/v1/profile/evidence",
            json={
                "expected_generation": 1,
                "id": identifier("evidence", 987),
                "claim_id": claim.id.root,
                "assertion": claim.assertion.model_dump(mode="json"),
                "relation": "supports",
                "source_kind": "user_report",
                "source_reference": "manual:additional-fabricated-source",
                "excerpt": "Synthetic addition cannot invalidate an accepted review silently.",
                "collected_at": "2026-10-03T12:00:00Z",
            },
        ),
        409,
    )
    assert store.load().snapshot == snapshot
    assert store.load_events() == ()


def test_missing_and_conflicting_resource_errors_are_stable(api: TestClient) -> None:
    failure(api.get("/api/v1/career"), 404)
    initialize(api)
    failure(api.get(f"/api/v1/jobs/{identifier('job', 88)}"), 404)
    failure(api.get(f"/api/v1/applications/{identifier('application', 88)}"), 404)
    failure(api.get("/api/v1/jobs/not-an-id"), 422)
    failure(api.post("/api/v1/jobs", json={"expected_generation": 1, "job": manual_job()}), 409)


def test_stale_generation_never_overwrites_or_creates_an_event(
    api: TestClient, pg_engine: Engine
) -> None:
    initialize(api)
    first = api.post("/api/v1/jobs", json={"expected_generation": 1, "job": manual_job(2)})
    assert first.status_code == 201, first.text
    assert first.json()["generation"] == 2
    store = CareerStore(pg_engine, OWNER)
    before = store.load()
    events = store.load_events()
    failure(api.post("/api/v1/jobs", json={"expected_generation": 1, "job": manual_job(3)}), 409)
    assert store.load() == before
    assert store.load_events() == events


def test_concurrent_http_mutations_have_one_committed_winner(
    api: TestClient, pg_engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    initialize(api)
    barrier = Barrier(2)
    original_load = StoreAdapter.load

    def read_same_generation(self: StoreAdapter) -> object:
        state = original_load(self)
        if state is not None and state.generation == 1:
            barrier.wait(timeout=10)
        return state

    monkeypatch.setattr(StoreAdapter, "load", read_same_generation)

    def add(number: int) -> object:
        return api.post("/api/v1/jobs", json={"expected_generation": 1, "job": manual_job(number)})

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(add, (2, 3)))
    assert sorted(response.status_code for response in responses) == [201, 409]
    winner = next(response for response in responses if response.status_code == 201)
    loser = next(response for response in responses if response.status_code == 409)
    failure(loser, 409)
    winning_id = winner.json()["job"]["id"]
    stored = CareerStore(pg_engine, OWNER).load()
    assert stored.generation == 2
    assert {job.id.root for job in stored.snapshot.jobs} == {identifier("job", 1), winning_id}
    events = CareerStore(pg_engine, OWNER).load_events()
    assert len(events) == 2
    assert {event.payload.job.object_id.root for event in events} == {
        identifier("job", 1),
        winning_id,
    }


def test_company_reuse_requires_exact_existing_context(api: TestClient, pg_engine: Engine) -> None:
    initialize(api)
    changed = manual_job(2)
    changed["company"]["context"] = PRIVATE
    failure(api.post("/api/v1/jobs", json={"expected_generation": 1, "job": changed}), 409)
    snapshot = CareerStore(pg_engine, OWNER).load().snapshot
    assert len(snapshot.jobs) == len(snapshot.companies) == 1
    assert snapshot.companies[0].context != PRIVATE
    accepted = api.post("/api/v1/jobs", json={"expected_generation": 1, "job": manual_job(2)})
    assert accepted.status_code == 201
    assert len(CareerStore(pg_engine, OWNER).load().snapshot.companies) == 1


def test_job_source_url_remains_inert_data(
    api: TestClient, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    initialize(api)
    job = manual_job(2)
    job["source_reference"] = f"https://attacker.invalid/{PRIVATE}?token=synthetic-private-value"

    def forbidden_network(*args: object, **kwargs: object) -> None:
        raise AssertionError("Job intake attempted an external HTTP request")

    # HTTPX client requests are local ASGI calls; block its ordinary outbound send path.
    monkeypatch.setattr("httpx2.HTTPTransport.handle_request", forbidden_network)
    response = api.post("/api/v1/jobs", json={"expected_generation": 1, "job": job})
    assert response.status_code == 201, response.text
    assert response.json()["job"]["source_reference"] == job["source_reference"]
    assert PRIVATE not in caplog.text
    assert "token=synthetic-private-value" not in caplog.text


def test_claim_and_evidence_preserve_unverified_provenance(
    api: TestClient, pg_engine: Engine
) -> None:
    initialize(api)
    assertion = {"kind": "skill", "subject": "python", "unit": "skill_level", "value": 2}
    claim_response = api.post(
        "/api/v1/profile/claims",
        json={
            "expected_generation": 1,
            "id": identifier("claim", 1),
            "assertion": assertion,
            "text": "Synthetic candidate reports Python development experience.",
        },
    )
    assert claim_response.status_code == 201, claim_response.text
    claim = claim_response.json()["profile"]["claims"][0]
    assert claim["origin"] == "user_report"
    assert claim["status"] == "self_reported"
    assert claim["asserted_by"] == ACTOR.root
    assert claim["review"] is None
    evidence_response = api.post(
        "/api/v1/profile/evidence",
        json={
            "expected_generation": 2,
            "id": identifier("evidence", 1),
            "claim_id": identifier("claim", 1),
            "assertion": assertion,
            "relation": "supports",
            "source_kind": "user_report",
            "source_reference": "manual:synthetic-report",
            "excerpt": "Fabricated report, without independent verification.",
            "collected_at": "2026-10-03T12:00:00Z",
        },
    )
    assert evidence_response.status_code == 201, evidence_response.text
    profile = evidence_response.json()["profile"]
    evidence, updated = profile["evidence"][0], profile["claims"][0]
    assert evidence["source_kind"] == "user_report"
    assert evidence["source_actor_id"] == ACTOR.root
    assert evidence["review"] is None
    assert updated["status"] != "reviewed_supported"
    assert updated["origin"] == "user_report"
    assert updated["asserted_by"] == ACTOR.root
    assert updated["asserted_at"] == claim["asserted_at"]
    assert updated["review"] is None
    assert updated["evidence_refs"][0]["evidence_id"] == evidence["id"]
    stored = CareerStore(pg_engine, OWNER).load().snapshot.profile
    assert not stored.evidence[0].qualifies_support
    assert api.get("/api/v1/profile").json()["profile"] == profile


@pytest.mark.parametrize("forged", ["status", "origin", "review", "workspace_id", "asserted_by"])
def test_claim_requests_cannot_forge_truth_or_server_identity(api: TestClient, forged: str) -> None:
    initialize(api)
    payload = {
        "expected_generation": 1,
        "id": identifier("claim", 1),
        "assertion": {"kind": "skill", "subject": "python", "unit": "skill_level", "value": 2},
        "text": PRIVATE,
        forged: "reviewed_supported",
    }
    failure(api.post("/api/v1/profile/claims", json=payload), 422)
    assert api.get("/api/v1/profile").json()["profile"]["claims"] == []


def test_evidence_cannot_forge_review_or_link_to_foreign_claim(api: TestClient) -> None:
    initialize(api)
    payload = {
        "expected_generation": 1,
        "id": identifier("evidence", 1),
        "claim_id": identifier("claim", 987),
        "assertion": {"kind": "skill", "subject": "python", "unit": "skill_level", "value": 2},
        "relation": "supports",
        "source_kind": "project_artifact",
        "source_reference": "manual:synthetic-artifact",
        "excerpt": PRIVATE,
        "collected_at": "2026-10-03T12:00:00Z",
    }
    failure(
        api.post("/api/v1/profile/evidence", json={**payload, "review": {"kind": "source_review"}}),
        422,
    )
    failure(api.post("/api/v1/profile/evidence", json=payload), 404)
    assert api.get("/api/v1/profile").json()["profile"]["evidence"] == []


def test_application_manual_lifecycle_commits_exact_observations(
    api: TestClient, pg_engine: Engine
) -> None:
    initialize(api)
    application_id = identifier("application", 1)
    created = api.post(
        "/api/v1/applications",
        json={
            "expected_generation": 1,
            "id": application_id,
            "job_id": identifier("job", 1),
            "occurred_at": "2026-10-03T12:00:00Z",
        },
    )
    assert created.status_code == 201, created.text
    application = created.json()["application"]
    assert application["state"] == "preparing"
    assert application["history"][0]["basis"] == "user_reported"
    assert application["history"][0]["actor_id"] == ACTOR.root
    generation = 2
    for index, state in enumerate(
        ("ready_for_review", "reviewed", "applied", "interview", "offer", "closed"), 13
    ):
        response = api.post(
            f"/api/v1/applications/{application_id}/status",
            json={
                "expected_generation": generation,
                "state": state,
                "occurred_at": f"2026-10-03T{index:02d}:00:00Z",
            },
        )
        assert response.status_code == 200, response.text
        generation += 1
        application = response.json()["application"]
        assert response.json()["generation"] == generation
        assert application["state"] == state
    store = CareerStore(pg_engine, OWNER)
    stored = store.load().snapshot.applications[0]
    assert [item.state for item in stored.history] == [
        "preparing",
        "ready_for_review",
        "reviewed",
        "applied",
        "interview",
        "offer",
        "closed",
    ]
    events = [
        event for event in store.load_events() if event.activity == "application_status_recorded"
    ]
    assert len(events) == len(stored.history)
    assert all(event.actor_id == ACTOR for event in events)
    assert all(event.payload.basis == "user_reported" for event in events)
    assert api.get(f"/api/v1/applications/{application_id}").json()["application"] == application


def test_invalid_transition_and_duplicate_intent_are_atomic(
    api: TestClient, pg_engine: Engine
) -> None:
    initialize(api)
    application_id = identifier("application", 1)
    response = api.post(
        "/api/v1/applications",
        json={
            "expected_generation": 1,
            "id": application_id,
            "job_id": identifier("job", 1),
            "occurred_at": "2026-10-03T12:00:00Z",
        },
    )
    assert response.status_code == 201
    store = CareerStore(pg_engine, OWNER)
    before, events = store.load(), store.load_events()
    failure(
        api.post(
            f"/api/v1/applications/{application_id}/status",
            json={
                "expected_generation": 2,
                "state": "offer",
                "occurred_at": "2026-10-03T13:00:00Z",
            },
        ),
        409,
    )
    failure(
        api.post(
            "/api/v1/applications",
            json={
                "expected_generation": 2,
                "id": identifier("application", 2),
                "job_id": identifier("job", 1),
                "occurred_at": "2026-10-03T13:00:00Z",
            },
        ),
        409,
    )
    assert store.load() == before
    assert store.load_events() == events
    applied = api.post(
        f"/api/v1/applications/{application_id}/status",
        json={
            "expected_generation": 2,
            "state": "applied",
            "external_manual": True,
            "occurred_at": "2026-10-03T13:00:00Z",
        },
    )
    assert applied.status_code == 200, applied.text
    history = applied.json()["application"]["history"]
    assert [item["state"] for item in history] == ["preparing", "applied"]
    assert history[-1]["external_manual"] is True
    assert history[-1]["basis"] == "user_reported"
    assert history[-1]["actor_id"] == ACTOR.root


def test_deferred_postgresql_commit_failure_cannot_return_http_success(
    api: TestClient, pg_engine: Engine, caplog: pytest.LogCaptureFixture
) -> None:
    initialize(api)
    store = CareerStore(pg_engine, OWNER)
    before, events = store.load(), store.load_events()
    with pg_engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE FUNCTION api_test_reject_commit() RETURNS trigger LANGUAGE plpgsql AS $$ "
            "BEGIN RAISE EXCEPTION 'PRIVATE_API_INPUT_28f64 synthetic deferred commit failure' "
            "USING ERRCODE = '23514'; END $$"
        )
        connection.exec_driver_sql(
            "CREATE CONSTRAINT TRIGGER api_test_commit_failure AFTER INSERT ON jobs "
            "DEFERRABLE INITIALLY DEFERRED FOR EACH ROW "
            "EXECUTE FUNCTION api_test_reject_commit()"
        )
    failure(api.post("/api/v1/jobs", json={"expected_generation": 1, "job": manual_job(2)}), 409)
    assert store.load() == before
    assert store.load_events() == events
    assert PRIVATE not in caplog.text
    with pg_engine.connect() as connection:
        assert connection.execute(select(func.count()).select_from(schema.jobs)).scalar_one() == 1


def test_lists_use_stable_order_and_bounded_pagination(api: TestClient) -> None:
    initialize(api)
    for number, generation in ((9, 1), (3, 2)):
        response = api.post(
            "/api/v1/jobs", json={"expected_generation": generation, "job": manual_job(number)}
        )
        assert response.status_code == 201
    first = api.get("/api/v1/jobs?offset=0&limit=2")
    assert first.status_code == 200
    page = first.json()
    assert page["total"] == 3
    assert page["next_offset"] == 2
    assert page["generation"] == 3
    repeated = api.get("/api/v1/jobs?offset=0&limit=2").json()
    assert repeated == page
    tail = api.get("/api/v1/jobs?offset=2&limit=2").json()
    ids = [item["id"] for item in (*page["items"], *tail["items"])]
    assert ids == sorted(ids)
    assert tail["next_offset"] is None
    past = api.get("/api/v1/jobs?offset=99&limit=2").json()
    assert past["items"] == []
    assert past["total"] == 3
    assert past["next_offset"] is None
    for query in ("limit=0", "limit=101", "offset=-1", "limit=one"):
        failure(api.get(f"/api/v1/jobs?{query}"), 422)
    events = api.get("/api/v1/events?offset=0&limit=2").json()
    assert events["total"] == 3
    assert events["next_offset"] == 2
    tail_events = api.get("/api/v1/events?offset=2&limit=2").json()
    all_events = (*events["items"], *tail_events["items"])
    keys = [(item["occurred_at"], item["event_id"]) for item in all_events]
    assert keys == sorted(keys)
    assert "generation" not in events


@pytest.mark.parametrize("exception", [CorruptStorageError(PRIVATE), RuntimeError(PRIVATE)])
def test_corrupt_or_unexpected_storage_failure_has_no_sensitive_error_output(
    api: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    exception: Exception,
) -> None:
    initialize(api)

    def fail_load(self: CareerStore) -> None:
        raise exception

    monkeypatch.setattr(CareerStore, "load", fail_load)
    failure(api.get("/api/v1/career"), 500)
    assert PRIVATE not in caplog.text


def test_deleted_workspace_is_inaccessible_through_all_runtime_reads(
    api: TestClient, pg_engine: Engine
) -> None:
    initialize(api)
    CareerStore(pg_engine, OWNER).delete(deleted_at=NOW)
    for path in (
        "/api/v1/career",
        "/api/v1/jobs",
        "/api/v1/profile",
        "/api/v1/applications",
        "/api/v1/events",
    ):
        failure(api.get(path), 410)
    failure(api.post("/api/v1/jobs", json={"expected_generation": 1, "job": manual_job(2)}), 410)
    failure(api.get("/health/ready"), 503)


@pytest.mark.parametrize("classification", ["personal", "sensitive"])
def test_real_classified_store_cannot_be_exposed_in_development_mode(
    api: TestClient, pg_engine: Engine, classification: str
) -> None:
    job_data = manual_job()
    company = Company(
        id=CompanyId(job_data["company"]["id"]),
        workspace_id=OWNER,
        revision=1,
        classification=classification,
        name="Fabricated privacy fixture",
        context=PRIVATE,
    )
    job = Job(
        id=JobId(job_data["id"]),
        workspace_id=OWNER,
        revision=1,
        classification=classification,
        company_id=company.id,
        opportunity_id=job_data["opportunity_id"],
        title="Fabricated test",
        text=PRIVATE,
        source_reference="manual:fabricated-privacy-test",
        posted_at=NOW - timedelta(days=1),
        decision="new",
    )
    profile = Profile(
        id=ProfileId(identifier("profile", 1)),
        workspace_id=OWNER,
        revision=1,
        classification=classification,
        name="Fabricated profile",
    )
    snapshot = CareerSnapshot(
        workspace_id=OWNER,
        classification=classification,
        as_of=NOW,
        companies=(company,),
        jobs=(job,),
        profile=profile,
    )
    CareerStore(pg_engine, OWNER).save(snapshot, expected_generation=0)
    for path in ("/api/v1/career", "/api/v1/jobs", "/api/v1/profile", "/api/v1/events"):
        failure(api.get(path), 403)
    failure(api.post("/api/v1/jobs", json={"expected_generation": 1, "job": manual_job(2)}), 403)
    failure(api.get("/health/ready"), 503)


def test_readiness_distinguishes_reachable_migrated_database(
    api: TestClient, unmigrated_engine: Engine
) -> None:
    assert api.get("/health/ready").status_code == 200
    app = create_app(
        ApiSettings(workspace_id=OWNER, actor_id=ACTOR), engine=unmigrated_engine, clock=lambda: NOW
    )
    # The api fixture uses the same underlying fixture engine, already migrated.
    # Remove only its version marker to simulate schema incompatibility, not a migration.
    with unmigrated_engine.begin() as connection:
        connection.exec_driver_sql("UPDATE alembic_version SET version_num = 'unknown_future'")
    with TestClient(
        app, base_url=BASE, client=("127.0.0.1", 50000), raise_server_exceptions=False
    ) as http:
        failure(http.get("/health/ready"), 503)
        failure(http.get("/api/v1/career"), 503)
        assert http.get("/health/live").status_code == 200


def test_api_writes_through_runtime_dml_role(runtime_engine: Engine) -> None:
    app = create_app(
        ApiSettings(workspace_id=OWNER, actor_id=ACTOR), engine=runtime_engine, clock=lambda: NOW
    )
    with TestClient(
        app, base_url=BASE, client=("127.0.0.1", 50000), raise_server_exceptions=False
    ) as http:
        initialize(http)
        response = http.post("/api/v1/jobs", json={"expected_generation": 1, "job": manual_job(2)})
        assert response.status_code == 201, response.text
        assert http.get("/api/v1/career").json()["generation"] == 2
