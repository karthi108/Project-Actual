"""New payloads/reviews round-trip through the accepted real PostgreSQL boundary."""

from test_profile_integration import (
    OWNER,
    claim_command,
    evidence_command,
    identifier,
    seed,
)
from test_profile_integration import profile_api as profile_api

from actual.persistence.repository import CareerStore


def test_preparation_review_revision_and_historical_event(profile_api, pg_engine):
    client = profile_api
    seed(client)
    store = CareerStore(pg_engine, OWNER)
    assert evidence_command(client, store, "synthetic-review").status_code == 200
    assert claim_command(client, store).status_code == 200
    state = store.load()
    response = client.post(
        "/api/v1/cvs",
        json={
            "expected_generation": state.generation,
            "id": identifier("cv"),
            "name": "Synthetic supported variant",
            "claim_ids": [identifier("claim")],
        },
    )
    assert response.status_code == 201, response.text
    state = store.load()
    response = client.post(
        "/api/v1/cvs/compare",
        json={
            "expected_generation": state.generation,
            "job_id": identifier("job"),
            "selections": [
                {
                    "quote": "Python at working level is essential.",
                    "term": "Python",
                    "priority": "essential",
                }
            ],
        },
    )
    assert response.status_code == 200, response.text
    report = response.json()
    assert report["assessment"]["rows"][0]["status"] == "supported"
    assert report["suggested_cv_ids"] == [identifier("cv")]
    assert store.load().generation == state.generation
    response = client.post(
        "/api/v1/drafts",
        json={
            "expected_generation": state.generation,
            "id": identifier("draft"),
            "job_id": identifier("job"),
            "cv_id": identifier("cv"),
            "material_kind": "cv_adaptation",
        },
    )
    assert response.status_code == 201, response.text
    prepared = response.json()
    response = client.post(
        f"/api/v1/drafts/{identifier('draft')}/review",
        json={
            "expected_generation": prepared["generation"],
            "expected_revision": 1,
            "expected_digest": prepared["content_digest"],
            "decision": "accepted",
        },
    )
    assert response.status_code == 200, response.text
    reviewed = response.json()
    assert reviewed["draft"]["revision"] == 2
    assert store.load().snapshot.drafts[0].review is not None
    review_events = [event for event in store.load_events() if event.activity == "draft_reviewed"]
    assert len(review_events) == 1
    assert review_events[0].payload.draft.revision == 2
    response = client.post(
        f"/api/v1/drafts/{identifier('draft')}/revise",
        json={
            "expected_generation": reviewed["generation"],
            "expected_revision": reviewed["draft"]["revision"],
            "expected_digest": reviewed["content_digest"],
            "job_id": identifier("job"),
            "cv_id": identifier("cv"),
            "material_kind": "cover_letter",
        },
    )
    assert response.status_code == 200, response.text
    assert store.load().snapshot.drafts[0].review is None
    assert store.load().snapshot.drafts[0].revision == 3
    assert any(event.activity == "draft_reviewed" for event in store.load_events())


def test_preparation_http_rejects_authority_and_free_prose(profile_api):
    for field in (
        "text",
        "summary",
        "actor_id",
        "workspace_id",
        "reviewer_id",
        "submitted",
        "recipient",
        "classification",
    ):
        response = profile_api.post(
            "/api/v1/drafts",
            json={
                "expected_generation": 1,
                "id": identifier("draft"),
                "job_id": identifier("job"),
                "cv_id": identifier("cv"),
                "material_kind": "application_message",
                field: "UNTRUSTED_AUTHORITY",
            },
        )
        assert response.status_code == 422
        assert "UNTRUSTED_AUTHORITY" not in response.text
