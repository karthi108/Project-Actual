"""Exercise the local HTTP trust boundary without opening a database connection."""

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
SENTINEL = "PRIVATE_BOUNDARY_INPUT_94c3"


@pytest.fixture
def client() -> Iterator[TestClient]:
    # Creating an engine is lazy; these transport/OpenAPI tests perform no SQL.
    engine = create_engine(
        "postgresql+psycopg://synthetic:synthetic@127.0.0.1:1/not_connected",
        hide_parameters=True,
        connect_args={"connect_timeout": 1},
    )
    settings = ApiSettings(
        workspace_id=WorkspaceId("workspace_" + "9" * 32),
        actor_id=ActorId("actor_" + "8" * 32),
    )
    try:
        app = create_app(settings, engine=engine, clock=lambda: datetime(2026, 10, 4, tzinfo=UTC))
        with TestClient(
            app,
            base_url=BASE,
            client=("127.0.0.1", 50000),
            raise_server_exceptions=False,
        ) as http:
            yield http
    finally:
        engine.dispose()


def assert_error(response: object, status: int) -> dict:
    assert response.status_code == status
    value = response.json()
    assert set(value) == {"schema_version", "error", "request_id"}
    assert value["schema_version"] == "actual-api-v1"
    assert set(value["error"]) == {"code", "message"}
    assert re.fullmatch(r"[0-9a-f]{32}", value["request_id"])
    assert value["request_id"] == response.headers["x-request-id"]
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "access-control-allow-origin" not in response.headers
    assert SENTINEL not in response.text
    return value


def test_liveness_requires_no_database_and_sets_safe_headers(client: TestClient) -> None:
    response = client.get("/health/live", headers={"x-request-id": SENTINEL})
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert re.fullmatch(r"[0-9a-f]{32}", response.headers["x-request-id"])
    assert response.headers["x-request-id"] != SENTINEL
    assert client.get("/health/live").headers["x-request-id"] != response.headers["x-request-id"]


def test_unreachable_database_is_unready_without_leaking_configuration(client: TestClient) -> None:
    response = client.get("/health/ready")
    assert_error(response, 503)
    assert "not_connected" not in response.text
    assert "synthetic:synthetic" not in response.text


def test_unknown_request_version_and_strict_generation_are_rejected(client: TestClient) -> None:
    for body in (
        {"schema_version": "actual-api-v999", "expected_generation": 1},
        {"expected_generation": "1"},
        {"expected_generation": True},
    ):
        assert_error(client.post("/api/v1/jobs", json=body), 422)


@pytest.mark.parametrize(
    "host",
    ["attacker.invalid", "127.0.0.1:9000", "localhost.attacker.invalid:8765", "127.0.0.1"],
)
def test_host_must_match_configured_loopback_port(client: TestClient, host: str) -> None:
    assert_error(client.get("/health/live", headers={"host": host}), 400)


@pytest.mark.parametrize("host", ["127.0.0.1:8765", "localhost:8765", "[::1]:8765"])
def test_exact_loopback_hosts_are_allowed(client: TestClient, host: str) -> None:
    assert client.get("/health/live", headers={"host": host}).status_code == 200


@pytest.mark.parametrize(
    "origin",
    ["null", "https://127.0.0.1:8765", "http://127.0.0.1:9000", "https://attacker.invalid"],
)
def test_foreign_or_null_origin_fails_closed(client: TestClient, origin: str) -> None:
    assert_error(client.get("/health/live", headers={"origin": origin}), 403)


def test_same_origin_is_allowed_without_enabling_cors(client: TestClient) -> None:
    response = client.get("/health/live", headers={"origin": BASE})
    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers
    assert_error(
        client.options(
            "/api/v1/jobs",
            headers={"origin": "https://attacker.invalid", "access-control-request-method": "POST"},
        ),
        403,
    )
    disallowed = client.delete("/health/live")
    assert_error(disallowed, 405)
    assert "GET" in disallowed.headers["allow"]


def test_cross_site_fetch_metadata_is_rejected(client: TestClient) -> None:
    assert_error(client.get("/health/live", headers={"sec-fetch-site": "cross-site"}), 403)


@pytest.mark.parametrize("header", ["host", "origin", "content-type", "content-length"])
def test_ambiguous_duplicate_headers_are_rejected(client: TestClient, header: str) -> None:
    values = {
        "host": "127.0.0.1:8765",
        "origin": BASE,
        "content-type": "application/json",
        "content-length": "2",
    }
    response = client.post(
        "/api/v1/jobs", content=b"{}", headers=[(header, values[header]), (header, values[header])]
    )
    assert_error(response, 400)


@pytest.mark.parametrize("media_type", ["text/plain", "application/x-www-form-urlencoded"])
def test_mutations_require_json_content_type(client: TestClient, media_type: str) -> None:
    assert_error(
        client.post("/api/v1/jobs", content=SENTINEL, headers={"content-type": media_type}), 415
    )


def test_compressed_request_bodies_are_not_accepted(client: TestClient) -> None:
    assert_error(
        client.post(
            "/api/v1/jobs",
            content=b"{}",
            headers={"content-type": "application/json", "content-encoding": "gzip"},
        ),
        415,
    )


@pytest.mark.parametrize(
    "body",
    [
        b'{"expected_generation":1,"expected_generation":2}',
        b'{"x":NaN}',
        b'{"x":Infinity}',
        b"\xff",
    ],
)
def test_ambiguous_or_non_json_payload_is_safely_rejected(client: TestClient, body: bytes) -> None:
    assert_error(
        client.post("/api/v1/jobs", content=body, headers={"content-type": "application/json"}), 422
    )


def test_excessive_nesting_and_actual_byte_length_are_bounded(client: TestClient) -> None:
    nested = b'{"x":' + b"[" * 32 + b"0" + b"]" * 32 + b"}"
    assert_error(
        client.post("/api/v1/jobs", content=nested, headers={"content-type": "application/json"}),
        422,
    )
    body = json.dumps({"text": "\u00e9" * 140_000}, ensure_ascii=False).encode()
    assert len(body) > 262_144
    assert_error(
        client.post(
            "/api/v1/jobs",
            content=body,
            headers={"content-type": "application/json", "content-length": "2"},
        ),
        413,
    )


def test_validation_errors_do_not_echo_private_payload_or_log_it(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    response = client.post("/api/v1/jobs", json={"expected_generation": SENTINEL, "job": SENTINEL})
    assert_error(response, 422)
    assert SENTINEL not in caplog.text
    assert "not_connected" not in response.text


@pytest.mark.parametrize(
    "path", ["/docs", "/redoc", "/openapi.json", "/api/v1/evaluator", "/api/v1/oracles"]
)
def test_unavailable_docs_and_hidden_oracle_routes_have_safe_errors(
    client: TestClient, path: str
) -> None:
    assert_error(client.get(path), 404)


def test_openapi_describes_only_the_authorized_typed_surface(client: TestClient) -> None:
    response = client.get("/api/v1/openapi.json")
    assert response.status_code == 200
    spec = response.json()
    paths = spec["paths"]
    for route in (
        "/api/v1/career",
        "/api/v1/jobs",
        "/api/v1/jobs/{job_id}",
        "/api/v1/profile",
        "/api/v1/profile/claims",
        "/api/v1/profile/evidence",
        "/api/v1/applications",
        "/api/v1/applications/{application_id}/status",
        "/api/v1/events",
    ):
        assert route in paths
    assert "post" not in paths["/api/v1/events"]
    encoded = json.dumps(spec).lower()
    for forbidden in (
        "recruiter_outcome",
        "hidden_truth",
        "password",
    ):
        assert forbidden not in encoded
    for path, operations in paths.items():
        for method, operation in operations.items():
            if method in {"get", "post"}:
                assert operation["responses"]
                assert all(
                    response["content"]["application/json"]["schema"]
                    for response in operation["responses"].values()
                    if "content" in response
                ), path


def test_remote_network_peer_is_rejected_before_liveness() -> None:
    engine = create_engine(
        "postgresql+psycopg://synthetic:synthetic@127.0.0.1:1/not_connected",
        connect_args={"connect_timeout": 1},
    )
    try:
        app = create_app(
            ApiSettings(
                workspace_id=WorkspaceId("workspace_" + "9" * 32),
                actor_id=ActorId("actor_" + "8" * 32),
            ),
            engine=engine,
        )
        with TestClient(
            app, base_url=BASE, client=("203.0.113.9", 50000), raise_server_exceptions=False
        ) as http:
            assert_error(http.get("/health/live"), 403)
    finally:
        engine.dispose()
