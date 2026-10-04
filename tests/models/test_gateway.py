"""Deterministic gateway checks use one fake call, never real model inference."""

import asyncio
import hashlib
import json
import logging
from dataclasses import asdict, replace
from datetime import UTC, datetime, timedelta, timezone

import pytest
from pydantic import BaseModel, ConfigDict, Field

from actual.capabilities.probe import PROBE, ProbeInput, ProbeOutput
from actual.models.contracts import (
    MAX_OUTPUT_BYTES,
    Capability,
    GenerationSettings,
    PreparedInference,
    ProviderIdentity,
    ProviderReply,
)
from actual.models.errors import FailureCode, ModelFailure
from actual.models.gateway import MODEL_LOG, ModelGateway, canonical_json, metadata_json

VALID_OUTPUT = {
    "schema_version": "actual-probe-output-v1",
    "marker": "synthetic-probe",
    "token_count": 2,
    "first_token": "red",
}
START = datetime(2026, 10, 4, 12, tzinfo=UTC)


class FakeProvider:
    def __init__(
        self,
        *,
        content: str = canonical_json(VALID_OUTPUT),
        failure: Exception | None = None,
        delay: float = 0.0,
        settings: GenerationSettings | None = None,
    ) -> None:
        self.identity = ProviderIdentity(
            provider="fake", model="qwen3:4b-instruct", endpoint="http://127.0.0.1:11434"
        )
        self.settings = settings or GenerationSettings()
        self.content = content
        self.failure = failure
        self.delay = delay
        self.requests: list[PreparedInference] = []
        self.cancelled = False

    async def infer(self, request: PreparedInference) -> ProviderReply:
        self.requests.append(request)
        try:
            await asyncio.sleep(self.delay)
        except asyncio.CancelledError:
            self.cancelled = True
            raise
        if self.failure:
            raise self.failure
        return ProviderReply(
            content=self.content,
            model=self.identity.model,
            model_digest="a" * 64,
            server_version="0.23.0",
            model_family="qwen3",
            quantization="Q4_K_M",
        )


def run(provider: FakeProvider, request: ProbeInput | None = None) -> object:
    gateway = ModelGateway(provider, capabilities=(PROBE,))
    return asyncio.run(
        gateway.run(PROBE, request or ProbeInput(synthetic=True, tokens=("red", "blue")))
    )


def test_typed_proposal_preserves_versions_settings_and_metadata() -> None:
    provider = FakeProvider()
    clocks = iter([START, START + timedelta(milliseconds=125)])
    ticks = iter([3.0, 3.125])
    gateway = ModelGateway(
        provider, capabilities=(PROBE,), clock=lambda: next(clocks), monotonic=lambda: next(ticks)
    )
    proposal = asyncio.run(gateway.run(PROBE, ProbeInput(synthetic=True, tokens=("red", "blue"))))
    assert type(proposal.value) is ProbeOutput
    assert proposal.value.token_count == 2
    assert proposal.metadata.identity == provider.identity
    assert proposal.metadata.settings == provider.settings
    assert proposal.metadata.response_model == provider.identity.model
    assert proposal.metadata.model_digest == "a" * 64
    assert proposal.metadata.server_version == "0.23.0"
    assert proposal.metadata.model_family == "qwen3"
    assert proposal.metadata.quantization == "Q4_K_M"
    assert proposal.metadata.capability == "synthetic_probe:v1"
    assert proposal.metadata.schema_version == "actual-probe-output-v1"
    assert proposal.metadata.proposal_only is True
    assert proposal.metadata.started_at == START
    assert proposal.metadata.finished_at == START + timedelta(milliseconds=125)
    assert proposal.metadata.duration_ms == 125
    assert len(proposal.metadata.request_id) == 32
    assert len(provider.requests) == 1
    prepared = provider.requests[0]
    assert (
        proposal.metadata.schema_sha256
        == hashlib.sha256(prepared.output_schema_json.encode()).hexdigest()
    )
    assert (
        proposal.metadata.prompt_sha256
        == hashlib.sha256(
            canonical_json(
                {"instructions": prepared.instructions, "input": prepared.input_json}
            ).encode()
        ).hexdigest()
    )
    assert metadata_json(proposal.metadata) == metadata_json(proposal.metadata)
    parsed = json.loads(metadata_json(proposal.metadata))
    assert parsed["started_at"] == "2026-10-04T12:00:00.000000Z"
    assert parsed["settings"]["temperature"] == 0.0
    assert "content" not in parsed and "value" not in parsed
    assert "token_count" not in repr(proposal)


def test_prepared_json_and_schema_hash_are_deterministic_but_request_ids_are_new() -> None:
    provider = FakeProvider()
    gateway = ModelGateway(provider, capabilities=(PROBE,))
    first = asyncio.run(gateway.run(PROBE, ProbeInput(synthetic=True, tokens=("red", "blue"))))
    second = asyncio.run(gateway.run(PROBE, ProbeInput(synthetic=True, tokens=("red", "blue"))))
    assert provider.requests[0] == provider.requests[1]
    assert first.metadata.schema_sha256 == second.metadata.schema_sha256
    assert first.metadata.prompt_sha256 == second.metadata.prompt_sha256
    assert first.metadata.request_id != second.metadata.request_id
    assert "instructions" not in repr(provider.requests[0])
    assert json.loads(provider.requests[0].output_schema_json)["additionalProperties"] is False


def test_structural_validation_does_not_promote_a_wrong_answer_to_truth() -> None:
    provider = FakeProvider(content=canonical_json({**VALID_OUTPUT, "token_count": 8}))
    gateway = ModelGateway(provider, capabilities=(PROBE,))
    proposal = asyncio.run(gateway.run(PROBE, ProbeInput(synthetic=True, tokens=("red",))))
    assert proposal.value.token_count == 8
    assert proposal.metadata.proposal_only is True
    assert not hasattr(proposal, "verified")


@pytest.mark.parametrize(
    "content",
    [
        "",
        "   ",
        "not-json",
        '```json\n{"token_count":2}\n```',
        '[{"token_count":2}]',
        '{"token_count":2',
        '{"token_count":2,"token_count":3}',
        '{"token_count":NaN}',
        '{"token_count":Infinity}',
        '{"token_count":1e999}',
        '{"token_count":"\\ud800"}',
        '{"a":' * 33 + "0" + "}" * 33,
    ],
)
def test_invalid_or_ambiguous_json_fails_once(content: str) -> None:
    provider = FakeProvider(content=content)
    with pytest.raises(ModelFailure) as captured:
        run(provider)
    assert captured.value.code == FailureCode.INVALID_OUTPUT
    assert str(captured.value) == "invalid_output"
    assert len(provider.requests) == 1


@pytest.mark.parametrize(
    "change",
    [
        {"token_count": "2"},
        {"token_count": True},
        {"token_count": -1},
        {"token_count": 9},
        {"token_count": 2.0},
        {"first_token": "yellow"},
        {"marker": "verified"},
        {"schema_version": "actual-probe-output-v2"},
        {"unexpected": "private-content"},
    ],
)
def test_schema_invalid_output_is_not_repaired_or_retried(change: dict[str, object]) -> None:
    provider = FakeProvider(content=canonical_json({**VALID_OUTPUT, **change}))
    with pytest.raises(ModelFailure) as captured:
        run(provider)
    assert captured.value.code == FailureCode.INVALID_OUTPUT
    assert "private-content" not in str(captured.value)
    assert len(provider.requests) == 1


@pytest.mark.parametrize("missing", list(VALID_OUTPUT))
def test_every_output_property_is_required(missing: str) -> None:
    provider = FakeProvider(
        content=canonical_json(
            {key: value for key, value in VALID_OUTPUT.items() if key != missing}
        )
    )
    with pytest.raises(ModelFailure) as captured:
        run(provider)
    assert captured.value.code == FailureCode.INVALID_OUTPUT


def test_output_byte_limit_and_invalid_unicode_fail_closed() -> None:
    for content, expected in (
        ("x" * (MAX_OUTPUT_BYTES + 1), FailureCode.OUTPUT_LIMIT),
        ("\ud800", FailureCode.INVALID_OUTPUT),
    ):
        provider = FakeProvider(content=content)
        with pytest.raises(ModelFailure) as captured:
            run(provider)
        assert captured.value.code == expected
        assert len(provider.requests) == 1


@pytest.mark.parametrize(
    "code",
    [
        FailureCode.PROVIDER_UNAVAILABLE,
        FailureCode.MODEL_NOT_FOUND,
        FailureCode.MODEL_UNAVAILABLE,
        FailureCode.TIMEOUT,
        FailureCode.LOCAL_PRIVACY_REQUIRED,
        FailureCode.INVALID_PROVIDER_RESPONSE,
    ],
)
def test_explicit_provider_failures_are_preserved_without_retry(code: FailureCode) -> None:
    provider = FakeProvider(failure=ModelFailure(code))
    with pytest.raises(ModelFailure) as captured:
        run(provider)
    assert captured.value.code == code
    assert len(provider.requests) == 1


def test_unknown_transport_error_does_not_escape_or_leak_content(
    caplog: pytest.LogCaptureFixture,
) -> None:
    provider = FakeProvider(failure=RuntimeError("secret-body-and-private-url"))
    with caplog.at_level(logging.INFO, logger=MODEL_LOG.name):
        with pytest.raises(ModelFailure) as captured:
            run(provider)
    assert captured.value.code == FailureCode.PROVIDER_FAILURE
    assert captured.value.__suppress_context__ is True
    assert "secret-body-and-private-url" not in str(captured.value)
    assert "secret-body-and-private-url" not in caplog.text
    assert len(provider.requests) == 1


def test_gateway_deadline_bounds_even_a_provider_without_its_own_timeout() -> None:
    provider = FakeProvider(delay=10, settings=GenerationSettings(timeout_seconds=1))
    with pytest.raises(ModelFailure) as captured:
        run(provider)
    assert captured.value.code == FailureCode.TIMEOUT
    assert provider.cancelled
    assert len(provider.requests) == 1


def test_success_and_invalid_output_logs_have_only_allowlisted_metadata(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO, logger=MODEL_LOG.name):
        run(FakeProvider())
        with pytest.raises(ModelFailure):
            run(FakeProvider(content='{"private-source":"PRIVATE_SENSITIVE_BODY"}'))
    records = [
        json.loads(record.message) for record in caplog.records if record.name == MODEL_LOG.name
    ]
    assert len(records) == 2
    assert [record["status"] for record in records] == ["success", "failure"]
    assert records[1]["error_code"] == "invalid_output"
    assert set(records[0]) == {
        "request_id",
        "provider",
        "model",
        "capability",
        "duration_ms",
        "status",
        "error_code",
    }
    assert "PRIVATE_SENSITIVE_BODY" not in caplog.text
    assert "token_count" not in caplog.text
    assert "127.0.0.1" not in caplog.text


def test_unchecked_provider_identity_and_capability_cannot_contaminate_logs(
    caplog: pytest.LogCaptureFixture,
) -> None:
    marker = "PRIVATE_INPUT\nlog injection"
    for wrong_type in (False, True):
        provider = FakeProvider()
        if wrong_type:
            provider.identity = marker
        else:
            object.__setattr__(provider.identity, "model", marker)
        gateway = ModelGateway(provider, capabilities=(PROBE,))
        with caplog.at_level(logging.INFO, logger=MODEL_LOG.name):
            with pytest.raises(ModelFailure):
                asyncio.run(gateway.run(PROBE, ProbeInput(synthetic=True, tokens=())))
        assert provider.requests == []
    capability = replace(PROBE)
    gateway = ModelGateway(FakeProvider(), capabilities=(capability,))
    object.__setattr__(capability, "name", marker)
    with caplog.at_level(logging.INFO, logger=MODEL_LOG.name):
        with pytest.raises(ModelFailure):
            asyncio.run(gateway.run(capability, ProbeInput(synthetic=True, tokens=())))
    assert marker not in caplog.text
    records = [
        json.loads(record.message) for record in caplog.records if record.name == MODEL_LOG.name
    ]
    assert all(record["provider"] is None and record["model"] is None for record in records)
    assert records[-1]["capability"] is None


def test_provider_response_model_must_match_the_selected_identity() -> None:
    class WrongModel(FakeProvider):
        async def infer(self, request: PreparedInference) -> ProviderReply:
            return replace(await super().infer(request), model="other-model:latest")

    provider = WrongModel()
    with pytest.raises(ModelFailure) as captured:
        run(provider)
    assert captured.value.code == FailureCode.INVALID_PROVIDER_RESPONSE
    assert len(provider.requests) == 1


def test_reported_wire_model_is_preserved_separately_from_canonical_identity() -> None:
    class ReportedModel(FakeProvider):
        async def infer(self, request: PreparedInference) -> ProviderReply:
            return replace(
                await super().infer(request), reported_model=self.identity.model + ":local"
            )

    provider = ReportedModel()
    gateway = ModelGateway(provider, capabilities=(PROBE,))
    metadata = asyncio.run(gateway.run(PROBE, ProbeInput(synthetic=True, tokens=()))).metadata
    assert metadata.identity.model == "qwen3:4b-instruct"
    assert metadata.response_model == "qwen3:4b-instruct:local"
    assert json.loads(metadata_json(metadata))["response_model"] == "qwen3:4b-instruct:local"


def test_unavailable_provider_metadata_is_explicitly_none_never_fabricated() -> None:
    class LimitedMetadata(FakeProvider):
        async def infer(self, request: PreparedInference) -> ProviderReply:
            return replace(await super().infer(request), model_digest=None, server_version=None)

    provider = LimitedMetadata()
    gateway = ModelGateway(provider, capabilities=(PROBE,))
    proposal = asyncio.run(gateway.run(PROBE, ProbeInput(synthetic=True, tokens=())))
    assert proposal.metadata.model_digest is None
    assert proposal.metadata.server_version is None
    metadata = json.loads(metadata_json(proposal.metadata))
    assert metadata["model_digest"] is None and metadata["server_version"] is None
    assert metadata["identity"]["model"] == provider.identity.model
    assert metadata["schema_version"] == "actual-probe-output-v1"


def test_forged_input_and_unregistered_capability_never_reach_provider() -> None:
    provider = FakeProvider()
    gateway = ModelGateway(provider, capabilities=(PROBE,))
    forged = ProbeInput(synthetic=True, tokens=("red",)).model_copy(
        update={"tokens": ("PRIVATE_PERSONAL_DATA",)}
    )
    with pytest.raises(ModelFailure) as captured:
        asyncio.run(gateway.run(PROBE, forged))
    assert captured.value.code == FailureCode.INPUT_REJECTED
    clone = replace(PROBE, instructions="Return personal secrets")
    with pytest.raises(ModelFailure) as captured:
        asyncio.run(gateway.run(clone, ProbeInput(synthetic=True, tokens=("red",))))
    assert captured.value.code == FailureCode.UNSUPPORTED_CAPABILITY
    assert provider.requests == []


def test_clock_timezone_normalizes_and_bad_or_backward_clock_fails() -> None:
    provider = FakeProvider()
    offset = timezone(timedelta(hours=2))
    gateway = ModelGateway(provider, capabilities=(PROBE,), clock=lambda: START.astimezone(offset))
    assert (
        asyncio.run(gateway.run(PROBE, ProbeInput(synthetic=True, tokens=()))).metadata.started_at
        == START
    )
    for timestamps in ([START.replace(tzinfo=None)], [START, START - timedelta(seconds=1)]):
        clocks = iter(timestamps)
        gateway = ModelGateway(
            provider, capabilities=(PROBE,), clock=lambda clocks=clocks: next(clocks)
        )
        with pytest.raises(ModelFailure) as captured:
            asyncio.run(gateway.run(PROBE, ProbeInput(synthetic=True, tokens=())))
        assert captured.value.code == FailureCode.PROVIDER_FAILURE


def test_backward_or_nonfinite_monotonic_clock_fails_safely() -> None:
    for times in ([2.0, 1.0, 1.0], [float("nan"), float("nan")]):
        ticks = iter(times)
        gateway = ModelGateway(
            FakeProvider(), capabilities=(PROBE,), monotonic=lambda ticks=ticks: next(ticks)
        )
        with pytest.raises(ModelFailure) as captured:
            asyncio.run(gateway.run(PROBE, ProbeInput(synthetic=True, tokens=())))
        assert captured.value.code == FailureCode.PROVIDER_FAILURE


def test_duplicate_or_empty_capability_registry_is_rejected() -> None:
    for capabilities in ((), (PROBE, PROBE), (PROBE, replace(PROBE))):
        with pytest.raises(ModelFailure) as captured:
            ModelGateway(FakeProvider(), capabilities=capabilities)
        assert captured.value.code == FailureCode.CONFIGURATION


def test_capability_schema_version_cannot_mislabel_the_output_schema() -> None:
    with pytest.raises(ModelFailure) as captured:
        replace(PROBE, schema_version="unrelated-schema-v1")
    assert captured.value.code == FailureCode.CONFIGURATION


class LargerInput(BaseModel):
    model_config = ConfigDict(
        strict=True,
        extra="forbid",
        frozen=True,
        revalidate_instances="always",
        hide_input_in_errors=True,
    )
    synthetic: bool
    text: str = Field(max_length=5000)


def test_input_byte_limit_is_checked_before_provider_call() -> None:
    capability = Capability(
        name="bounded_test",
        version="v1",
        schema_version="actual-probe-output-v1",
        input_model=LargerInput,
        output_model=ProbeOutput,
        instructions="Synthetic-only test instructions",
    )
    provider = FakeProvider()
    gateway = ModelGateway(provider, capabilities=(capability,))
    with pytest.raises(ModelFailure) as captured:
        asyncio.run(gateway.run(capability, LargerInput(synthetic=True, text="x" * 4500)))
    assert captured.value.code == FailureCode.INPUT_REJECTED
    assert provider.requests == []


@pytest.mark.parametrize(
    "change",
    [
        {"timeout_seconds": 0},
        {"timeout_seconds": 301},
        {"timeout_seconds": float("nan")},
        {"timeout_seconds": True},
        {"context_tokens": 511},
        {"context_tokens": 8193},
        {"context_tokens": True},
        {"max_output_tokens": 15},
        {"max_output_tokens": 513},
        {"temperature": 0.1},
        {"temperature": False},
        {"seed": -1},
        {"seed": 2**31},
    ],
)
def test_generation_settings_reject_invalid_values(change: dict[str, object]) -> None:
    with pytest.raises(ModelFailure) as captured:
        GenerationSettings(**change)
    assert captured.value.code == FailureCode.CONFIGURATION


def test_generation_settings_boundaries_and_reply_metadata_validation() -> None:
    assert GenerationSettings(timeout_seconds=1, context_tokens=512, max_output_tokens=16, seed=0)
    assert GenerationSettings(
        timeout_seconds=300, context_tokens=8192, max_output_tokens=512, seed=2**31 - 1
    )
    reply = ProviderReply(
        content="PRIVATE_RESPONSE",
        model="qwen3:4b-instruct",
        model_digest="a" * 64,
        server_version="0.23.0",
    )
    assert "PRIVATE_RESPONSE" not in repr(reply)
    for change in (
        {"model_digest": "mutable-tag"},
        {"server_version": "secret body"},
        {"model": "private model\ntext"},
        {"reported_model": "private model\ntext"},
    ):
        with pytest.raises(ModelFailure) as captured:
            ProviderReply(**{**asdict(reply), **change})
        assert captured.value.code == FailureCode.INVALID_PROVIDER_RESPONSE


def test_bad_metadata_identifier_clock_and_duration_are_rejected() -> None:
    gateway = ModelGateway(FakeProvider(), capabilities=(PROBE,))
    metadata = asyncio.run(gateway.run(PROBE, ProbeInput(synthetic=True, tokens=()))).metadata
    for change in (
        {"request_id": "user-provided-text"},
        {"duration_ms": -1},
        {"duration_ms": float("inf")},
        {"proposal_only": False},
        {"started_at": START.replace(tzinfo=None)},
        {"schema_sha256": "tag"},
    ):
        with pytest.raises(ModelFailure) as captured:
            replace(metadata, **change)
        assert captured.value.code == FailureCode.PROVIDER_FAILURE
