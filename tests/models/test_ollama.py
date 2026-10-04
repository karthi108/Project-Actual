"""Real HTTP envelopes with deterministic local transport, never a model download."""

import asyncio
import json
import time
from collections.abc import AsyncIterator

import httpx2 as httpx
import pytest

from actual.models.config import OllamaSettings
from actual.models.contracts import GenerationSettings, PreparedInference
from actual.models.errors import FailureCode, ModelFailure
from actual.models.ollama import MAX_PROVIDER_BYTES, SUPPORTED_SERVER, OllamaQwenProvider

MODEL = "qwen3:4b-instruct"
DIGEST = "a" * 64
PREPARED = PreparedInference(
    instructions="Synthetic probe only. PRIVATE_PROMPT_CANARY",
    input_json='{"synthetic":true,"tokens":["red"]}',
    output_schema_json='{"type":"object","properties":{"token_count":{"type":"integer"}}}',
)


class Chunks(httpx.AsyncByteStream):
    def __init__(self, values: list[bytes], *, delay: float = 0) -> None:
        self.values, self.delay = values, delay

    async def __aiter__(self) -> AsyncIterator[bytes]:
        for value in self.values:
            if self.delay:
                await asyncio.sleep(self.delay)
            yield value


class LocalServer:
    """Only provider HTTP behavior is faked; no accepted ACTUAL layer is changed."""

    def __init__(self) -> None:
        details = {"format": "gguf", "family": "qwen3", "quantization_level": "Q4_K_M"}
        self.records = {
            "/api/status": {"cloud": {"disabled": True}},
            "/api/version": {"version": SUPPORTED_SERVER},
            "/api/tags": {"models": [{"name": MODEL, "digest": DIGEST, "details": details}]},
            "/api/show": {"details": details, "capabilities": ["completion"]},
            "/api/chat": {
                "model": MODEL,
                "done": True,
                "done_reason": "stop",
                "message": {"role": "assistant", "content": '{"token_count":1}'},
            },
        }
        self.requests: list[httpx.Request] = []
        self.overrides: dict[str, httpx.Response | Exception] = {}

    async def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        override = self.overrides.get(request.url.path)
        if isinstance(override, Exception):
            raise override
        if override is not None:
            return override
        payload = json.dumps(self.records[request.url.path]).encode()
        return httpx.Response(
            200,
            headers={"content-type": "application/json", "content-length": str(len(payload))},
            stream=Chunks([payload[: len(payload) // 2], payload[len(payload) // 2 :]]),
        )

    @property
    def paths(self) -> list[str]:
        return [request.url.path for request in self.requests]

    def provider(self, *, settings: OllamaSettings | None = None) -> OllamaQwenProvider:
        return OllamaQwenProvider(
            settings or OllamaSettings(), transport=httpx.MockTransport(self.handle)
        )


def fail(server: LocalServer, code: FailureCode) -> None:
    with pytest.raises(ModelFailure) as captured:
        asyncio.run(server.provider().infer(PREPARED))
    assert captured.value.code == code
    assert "PRIVATE_" not in str(captured.value)


def test_local_schema_request_and_observed_metadata_are_preserved(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HTTP_PROXY", "http://PRIVATE_PROXY.invalid:8000")
    monkeypatch.setenv("HTTPS_PROXY", "http://PRIVATE_PROXY.invalid:8000")
    monkeypatch.setenv("ALL_PROXY", "http://PRIVATE_PROXY.invalid:8000")
    server = LocalServer()
    provider = server.provider()
    result = asyncio.run(provider.infer(PREPARED))
    assert provider.identity.provider == "ollama"
    assert provider.identity.model == MODEL
    assert provider.identity.endpoint == "http://127.0.0.1:11434"
    assert server.paths == ["/api/status", "/api/version", "/api/tags", "/api/show", "/api/chat"]
    assert all(request.url.host == "127.0.0.1" for request in server.requests)
    assert json.loads(server.requests[-2].content) == {"model": MODEL + ":local", "verbose": False}
    body = json.loads(server.requests[-1].content)
    assert set(body) == {
        "model",
        "messages",
        "format",
        "stream",
        "think",
        "truncate",
        "shift",
        "keep_alive",
        "options",
    }
    assert body["model"] == MODEL + ":local"
    assert body["format"] == json.loads(PREPARED.output_schema_json)
    assert body["messages"] == [
        {"role": "system", "content": PREPARED.instructions},
        {"role": "user", "content": '{"synthetic":true,"tokens":["red"]}'},
    ]
    assert body["options"] == {"temperature": 0.0, "seed": 42, "num_ctx": 4096, "num_predict": 128}
    assert body["stream"] is body["think"] is body["truncate"] is body["shift"] is False
    assert body["keep_alive"] == 0
    assert "tools" not in body
    assert result.content == '{"token_count":1}'
    assert result.model == MODEL
    assert result.model_digest == DIGEST
    assert result.server_version == SUPPORTED_SERVER
    assert result.model_family == "qwen3"
    assert result.quantization == "Q4_K_M"


@pytest.mark.parametrize("wire_model", [MODEL, MODEL + ":local"])
def test_exact_local_wire_echo_is_preserved_without_changing_canonical_identity(
    wire_model: str,
) -> None:
    server = LocalServer()
    server.records["/api/chat"]["model"] = wire_model
    result = asyncio.run(server.provider().infer(PREPARED))
    assert result.model == MODEL
    assert result.reported_model == wire_model


@pytest.mark.parametrize(
    "status", [{}, {"cloud": {}}, {"cloud": {"disabled": False}}, {"cloud": {"disabled": 1}}]
)
def test_cloud_status_must_explicitly_prove_disabled_before_prompt_dispatch(status: dict) -> None:
    server = LocalServer()
    server.records["/api/status"] = status
    fail(server, FailureCode.LOCAL_PRIVACY_REQUIRED)
    assert server.paths == ["/api/status"]


def test_status_endpoint_unavailable_and_unreviewed_server_version_fail_closed() -> None:
    server = LocalServer()
    server.overrides["/api/status"] = httpx.Response(404, content=b"PRIVATE_PROVIDER_BODY")
    fail(server, FailureCode.LOCAL_PRIVACY_REQUIRED)
    assert "/api/chat" not in server.paths
    server = LocalServer()
    server.records["/api/version"] = {"version": "0.34.4"}
    fail(server, FailureCode.INVALID_PROVIDER_RESPONSE)
    assert "/api/show" not in server.paths


def test_catalog_requires_one_installed_matching_local_model_and_digest() -> None:
    server = LocalServer()
    server.records["/api/tags"] = {"models": []}
    fail(server, FailureCode.MODEL_NOT_FOUND)
    assert "/api/chat" not in server.paths
    server = LocalServer()
    server.records["/api/tags"]["models"].append(server.records["/api/tags"]["models"][0])
    fail(server, FailureCode.INVALID_PROVIDER_RESPONSE)
    server = LocalServer()
    server.records["/api/tags"]["models"][0]["digest"] = "not-a-digest"
    fail(server, FailureCode.INVALID_PROVIDER_RESPONSE)


@pytest.mark.parametrize("stage", ["/api/tags", "/api/show", "/api/chat"])
def test_remote_model_metadata_fails_even_for_an_allowlisted_name(stage: str) -> None:
    server = LocalServer()
    record = server.records[stage]["models"][0] if stage == "/api/tags" else server.records[stage]
    record["remote_model"] = "PRIVATE_REMOTE_MODEL"
    fail(server, FailureCode.LOCAL_PRIVACY_REQUIRED)
    if stage != "/api/chat":
        assert "/api/chat" not in server.paths


def test_non_gguf_non_qwen_and_no_completion_models_are_rejected() -> None:
    for field, value in (("format", "remote"), ("family", "llama")):
        server = LocalServer()
        server.records["/api/tags"]["models"][0]["details"][field] = value
        fail(server, FailureCode.LOCAL_PRIVACY_REQUIRED)
        assert "/api/chat" not in server.paths
    server = LocalServer()
    server.records["/api/show"]["capabilities"] = ["embedding"]
    fail(server, FailureCode.MODEL_UNAVAILABLE)
    assert "/api/chat" not in server.paths


@pytest.mark.parametrize(
    ("path", "status", "code"),
    [
        ("/api/show", 404, FailureCode.MODEL_NOT_FOUND),
        ("/api/chat", 404, FailureCode.MODEL_NOT_FOUND),
        ("/api/chat", 500, FailureCode.MODEL_UNAVAILABLE),
        ("/api/chat", 429, FailureCode.PROVIDER_FAILURE),
        ("/api/chat", 400, FailureCode.PROVIDER_FAILURE),
    ],
)
def test_http_failure_codes_do_not_leak_bodies_or_retry(
    path: str, status: int, code: FailureCode
) -> None:
    server = LocalServer()
    server.overrides[path] = httpx.Response(status, content=b"PRIVATE_PROVIDER_ERROR")
    fail(server, code)
    assert server.paths.count(path) == 1


@pytest.mark.parametrize(
    ("error", "code"),
    [
        (httpx.ConnectError("PRIVATE_CONNECT_FAILURE"), FailureCode.PROVIDER_UNAVAILABLE),
        (httpx.ReadTimeout("PRIVATE_TIMEOUT_FAILURE"), FailureCode.TIMEOUT),
        (httpx.RemoteProtocolError("PRIVATE_PROTOCOL_FAILURE"), FailureCode.PROVIDER_FAILURE),
    ],
)
def test_transport_errors_are_safe_explicit_failures_without_retry(
    error: Exception, code: FailureCode
) -> None:
    server = LocalServer()
    server.overrides["/api/status"] = error
    fail(server, code)
    assert server.paths == ["/api/status"]


def test_redirect_is_not_followed_to_external_destination() -> None:
    server = LocalServer()
    server.overrides["/api/chat"] = httpx.Response(
        307, headers={"location": "http://PRIVATE_REMOTE.invalid/api/chat"}
    )
    fail(server, FailureCode.PROVIDER_FAILURE)
    assert server.paths.count("/api/chat") == 1
    assert all(request.url.host == "127.0.0.1" for request in server.requests)


@pytest.mark.parametrize(
    "payload",
    [b"", b"{", b"[]", b'{"done":true,"done":false}', b'{"duration":NaN}', b'{"text":"\\ud800"}'],
)
def test_malformed_provider_json_is_rejected(payload: bytes) -> None:
    server = LocalServer()
    server.overrides["/api/chat"] = httpx.Response(
        200, headers={"content-type": "application/json"}, stream=Chunks([payload])
    )
    fail(server, FailureCode.INVALID_PROVIDER_RESPONSE)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("done", False),
        ("done", 1),
        ("done_reason", "length"),
        ("model", "qwen3:8b"),
        ("message.role", "system"),
        ("message.content", ""),
        ("message.content", None),
        ("message.thinking", "PRIVATE_REASONING"),
        ("message.tool_calls", [{"function": {"name": "shell"}}]),
    ],
)
def test_incomplete_wrong_model_or_tool_bearing_responses_fail_closed(
    field: str, value: object
) -> None:
    server = LocalServer()
    record = server.records["/api/chat"]
    if field.startswith("message."):
        record["message"][field.split(".")[1]] = value
    else:
        record[field] = value
    fail(server, FailureCode.INVALID_PROVIDER_RESPONSE)


def test_provider_error_object_is_not_a_successful_empty_result() -> None:
    server = LocalServer()
    server.records["/api/chat"] = {"error": "PRIVATE_MODEL_LOAD_FAILURE"}
    fail(server, FailureCode.MODEL_UNAVAILABLE)


@pytest.mark.parametrize(
    "headers",
    [
        {"content-type": "text/plain"},
        {"content-type": "application/json", "content-encoding": "gzip"},
        {"content-type": "application/json", "content-length": "not-a-number"},
        {"content-type": "application/json", "content-length": "2"},
    ],
)
def test_invalid_media_compression_or_declared_lengths_fail_closed(headers: dict[str, str]) -> None:
    server = LocalServer()
    payload = json.dumps(server.records["/api/chat"]).encode()
    server.overrides["/api/chat"] = httpx.Response(200, headers=headers, stream=Chunks([payload]))
    fail(server, FailureCode.INVALID_PROVIDER_RESPONSE)


def test_declared_and_chunked_response_limits_cannot_be_bypassed() -> None:
    for declared in (True, False):
        server = LocalServer()
        headers = {"content-type": "application/json"}
        if declared:
            headers["content-length"] = str(MAX_PROVIDER_BYTES + 1)
        server.overrides["/api/chat"] = httpx.Response(
            200, headers=headers, stream=Chunks([b"x" * MAX_PROVIDER_BYTES, b"x"])
        )
        fail(server, FailureCode.OUTPUT_LIMIT)


def test_total_timeout_bounds_a_slow_drip_response_without_retry() -> None:
    server = LocalServer()
    # Each small read finishes promptly; only a deadline over the entire call can
    # stop this response before all chunks arrive.
    server.overrides["/api/chat"] = httpx.Response(
        200, headers={"content-type": "application/json"}, stream=Chunks([b" "] * 20, delay=0.1)
    )
    provider = server.provider(
        settings=OllamaSettings(generation=GenerationSettings(timeout_seconds=1.0))
    )
    started = time.monotonic()
    with pytest.raises(ModelFailure) as captured:
        asyncio.run(provider.infer(PREPARED))
    assert captured.value.code == FailureCode.TIMEOUT
    assert time.monotonic() - started < 1.7
    assert server.paths.count("/api/chat") == 1


def test_default_transport_disables_ambient_proxies_redirects_and_retries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    server = LocalServer()
    original_client = httpx.AsyncClient
    construction = {}

    def transport(**options: object) -> httpx.MockTransport:
        construction["transport"] = options
        return httpx.MockTransport(server.handle)

    def client(**options: object) -> httpx.AsyncClient:
        construction["client"] = options
        return original_client(**options)

    monkeypatch.setattr(httpx, "AsyncHTTPTransport", transport)
    monkeypatch.setattr(httpx, "AsyncClient", client)
    asyncio.run(OllamaQwenProvider(OllamaSettings()).infer(PREPARED))
    assert construction["transport"]["trust_env"] is False
    assert construction["transport"]["retries"] == 0
    assert construction["client"]["trust_env"] is False
    assert construction["client"]["follow_redirects"] is False


@pytest.mark.parametrize(
    ("field", "value"), [("timeout_seconds", float("inf")), ("context_tokens", 8193)]
)
def test_forged_nested_settings_fail_before_any_network_request(field: str, value: object) -> None:
    server = LocalServer()
    settings = OllamaSettings()
    object.__setattr__(settings.generation, field, value)
    with pytest.raises(ModelFailure) as captured:
        server.provider(settings=settings)
    assert captured.value.code == FailureCode.CONFIGURATION
    assert not server.requests


def test_returned_settings_cannot_mutate_provider_configuration() -> None:
    server = LocalServer()
    provider = server.provider()
    object.__setattr__(provider.settings, "timeout_seconds", float("inf"))
    assert provider.settings.timeout_seconds == 120.0
    assert asyncio.run(provider.infer(PREPARED)).model == MODEL
