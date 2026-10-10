"""Profile review authority stays outside untrusted HTTP fields."""

import json
import re
from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from actual.api.app import create_app
from actual.api.config import ApiSettings
from actual.core.primitives import ActorId, WorkspaceId

BASE = "http://127.0.0.1:8765"
PRIVATE = "PRIVATE_PROFILE_BOUNDARY_c71d"
EVIDENCE = "evidence_" + "1" * 32
CLAIM = "claim_" + "2" * 32
REVIEW_ROUTES = (
    f"/api/v1/profile/evidence/{EVIDENCE}/synthetic-review",
    f"/api/v1/profile/claims/{CLAIM}/synthetic-review",
    f"/api/v1/profile/evidence/{EVIDENCE}/withdraw",
)


@pytest.fixture
def profile_client() -> Iterator[TestClient]:
    # Construction is lazy. Invalid commands and OpenAPI never need PostgreSQL.
    engine = create_engine(
        "postgresql+psycopg://synthetic:synthetic@127.0.0.1:1/not_connected",
        hide_parameters=True,
        connect_args={"connect_timeout": 1},
    )
    try:
        app = create_app(
            ApiSettings(
                workspace_id=WorkspaceId("workspace_" + "9" * 32),
                actor_id=ActorId("actor_" + "8" * 32),
            ),
            engine=engine,
            clock=lambda: datetime(2026, 10, 6, tzinfo=UTC),
        )
        with TestClient(
            app, base_url=BASE, client=("127.0.0.1", 50000), raise_server_exceptions=False
        ) as client:
            yield client
    finally:
        engine.dispose()


def binding() -> dict:
    return {
        "schema_version": "actual-api-v1",
        "expected_generation": 1,
        "expected_revision": 1,
        "expected_digest": "a" * 64,
    }


def safe_error(response: object, status: int) -> dict:
    assert response.status_code == status, response.text
    payload = response.json()
    assert set(payload) == {"schema_version", "request_id", "error"}
    assert set(payload["error"]) == {"code", "message"}
    assert payload["schema_version"] == "actual-api-v1"
    assert re.fullmatch(r"[0-9a-f]{32}", payload["request_id"])
    assert response.headers["x-request-id"] == payload["request_id"]
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert PRIVATE not in response.text
    assert "not_connected" not in response.text
    assert "Traceback" not in response.text
    return payload


@pytest.mark.parametrize("route", REVIEW_ROUTES)
def test_profile_review_commands_cannot_supply_authority(
    profile_client: TestClient, caplog: pytest.LogCaptureFixture, route: str
) -> None:
    for field in (
        "actor_id",
        "workspace_id",
        "reviewer_id",
        "reviewed_at",
        "kind",
        "method",
        "status",
        "classification",
        "independent_source_reference",
        "review",
        "evaluator_answer",
    ):
        response = profile_client.post(route, json={**binding(), field: PRIVATE})
        assert safe_error(response, 422)["error"]["code"] == "INVALID_REQUEST"
    assert PRIVATE not in caplog.text


@pytest.mark.parametrize("route", REVIEW_ROUTES)
def test_profile_commands_require_exact_strict_versioned_bindings(
    profile_client: TestClient, route: str
) -> None:
    for changed in (
        {"schema_version": "actual-api-v999"},
        {"expected_generation": True},
        {"expected_generation": "1"},
        {"expected_generation": 0},
        {"expected_revision": True},
        {"expected_revision": "1"},
        {"expected_revision": 0},
        {"expected_digest": "A" * 64},
        {"expected_digest": "a" * 63},
        {"expected_digest": PRIVATE},
    ):
        safe_error(profile_client.post(route, json={**binding(), **changed}), 422)
    for missing in ("expected_generation", "expected_revision", "expected_digest"):
        body = binding()
        del body[missing]
        safe_error(profile_client.post(route, json=body), 422)


def test_profile_review_path_ids_are_typed(profile_client: TestClient) -> None:
    for route in (
        f"/api/v1/profile/evidence/{CLAIM}/synthetic-review",
        f"/api/v1/profile/claims/{EVIDENCE}/synthetic-review",
        "/api/v1/profile/evidence/not-an-id/withdraw",
    ):
        safe_error(profile_client.post(route, json=binding()), 422)


@pytest.mark.parametrize("route", REVIEW_ROUTES)
def test_local_destination_rules_cover_profile_mutations(
    profile_client: TestClient, route: str
) -> None:
    safe_error(
        profile_client.post(route, json=binding(), headers={"origin": "https://attacker.invalid"}),
        403,
    )
    safe_error(
        profile_client.post(route, json=binding(), headers={"host": "localhost.attacker.invalid"}),
        400,
    )
    safe_error(
        profile_client.post(route, json=binding(), headers={"sec-fetch-site": "cross-site"}),
        403,
    )


def test_new_profile_openapi_surface_is_closed_and_capability_oriented(
    profile_client: TestClient,
) -> None:
    response = profile_client.get("/api/v1/openapi.json")
    assert response.status_code == 200
    spec = response.json()
    assert "get" in spec["paths"]["/api/v1/profile/evidence"]
    for route in (
        "/api/v1/profile/evidence/{evidence_id}/synthetic-review",
        "/api/v1/profile/claims/{claim_id}/synthetic-review",
        "/api/v1/profile/evidence/{evidence_id}/withdraw",
    ):
        operation = spec["paths"][route]["post"]
        reference = operation["requestBody"]["content"]["application/json"]["schema"]["$ref"]
        body = spec["components"]["schemas"][reference.rsplit("/", 1)[1]]
        assert set(body["properties"]) == set(binding())
        assert body["additionalProperties"] is False
        assert set(body["required"]) == {
            "expected_generation",
            "expected_revision",
            "expected_digest",
        }
    assert not any(
        part in path
        for path in spec["paths"]
        for part in ("/chat", "/ask-ai", "/evaluator", "/oracles", "/independent-verification")
    )
    encoded = json.dumps(spec)
    assert "evaluator_answer" not in encoded
    assert "hidden_truth" not in encoded
