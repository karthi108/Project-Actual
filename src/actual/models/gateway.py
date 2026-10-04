"""Validate typed proposals without granting models authority or side effects."""

import asyncio
import hashlib
import json
import logging
import math
import time
from collections.abc import Callable
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import ValidationError

from actual.models.codec import decode_object
from actual.models.contracts import (
    MAX_INPUT_BYTES,
    MAX_OUTPUT_BYTES,
    MAX_SCHEMA_BYTES,
    Capability,
    GenerationSettings,
    InferenceMetadata,
    InputT,
    ModelProvider,
    OutputT,
    PreparedInference,
    Proposal,
    ProviderIdentity,
    ProviderReply,
)
from actual.models.errors import FailureCode, ModelFailure

MODEL_LOG = logging.getLogger("actual.models.runs")


def canonical_json(value: object) -> str:
    """Stable UTF-8 JSON representation; no content is logged or persisted."""
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    )


def metadata_json(metadata: InferenceMetadata) -> str:
    payload = asdict(metadata)
    payload["started_at"] = metadata.started_at.isoformat(timespec="microseconds").replace(
        "+00:00", "Z"
    )
    payload["finished_at"] = metadata.finished_at.isoformat(timespec="microseconds").replace(
        "+00:00", "Z"
    )
    return canonical_json(payload)


def _utc_now(clock: Callable[[], datetime]) -> datetime:
    try:
        value = clock()
        if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("An aware server clock is required")
        return value.astimezone(UTC)
    except Exception:
        raise ModelFailure(FailureCode.PROVIDER_FAILURE) from None


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class ModelGateway:
    """Call only explicitly registered capabilities; accept strict output once."""

    def __init__(
        self,
        provider: ModelProvider,
        *,
        capabilities: tuple[Capability[Any, Any], ...],
        clock: Callable[[], datetime] | None = None,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        if not capabilities or len({capability.identifier for capability in capabilities}) != len(
            capabilities
        ):
            raise ModelFailure(FailureCode.CONFIGURATION)
        self._provider = provider
        self._capabilities = capabilities
        self._clock = clock or (lambda: datetime.now(UTC))
        self._monotonic = monotonic

    async def run(
        self, capability: Capability[InputT, OutputT], request: InputT
    ) -> Proposal[OutputT]:
        request_id = uuid4().hex
        duration_ms = 0.0
        failure: FailureCode | None = None
        identity: ProviderIdentity | None = None
        started_tick: float | None = None
        capability_id: str | None = None
        try:
            if not any(registered is capability for registered in self._capabilities):
                raise ModelFailure(FailureCode.UNSUPPORTED_CAPABILITY)
            # Recheck frozen configuration before deriving any log fields.
            Capability(**asdict(capability))
            capability_id = capability.identifier
            prepared = self._prepare(capability, request)
            candidate_identity = self._provider.identity
            settings = self._provider.settings
            if (
                type(candidate_identity) is not ProviderIdentity
                or type(settings) is not GenerationSettings
            ):
                raise ModelFailure(FailureCode.INVALID_PROVIDER_RESPONSE)
            identity = ProviderIdentity(**asdict(candidate_identity))
            settings = GenerationSettings(**asdict(settings))
            started_at = _utc_now(self._clock)
            started_tick = self._monotonic()
            if not math.isfinite(started_tick):
                raise ModelFailure(FailureCode.PROVIDER_FAILURE)
            try:
                async with asyncio.timeout(settings.timeout_seconds):
                    reply = await self._provider.infer(prepared)
            except TimeoutError:
                raise ModelFailure(FailureCode.TIMEOUT) from None
            if type(reply) is not ProviderReply:
                raise ModelFailure(FailureCode.INVALID_PROVIDER_RESPONSE)
            # Reconstruct frozen adapter data to catch any unchecked mutation.
            reply = ProviderReply(**asdict(reply))
            if reply.model != identity.model:
                raise ModelFailure(FailureCode.INVALID_PROVIDER_RESPONSE)
            try:
                output_bytes = reply.content.encode("utf-8")
            except UnicodeError:
                raise ModelFailure(FailureCode.INVALID_OUTPUT) from None
            output = decode_object(
                output_bytes, max_bytes=MAX_OUTPUT_BYTES, code=FailureCode.INVALID_OUTPUT
            )
            try:
                value = capability.output_model.model_validate_json(
                    canonical_json(output), strict=True
                )
            except (ValidationError, ValueError, TypeError):
                raise ModelFailure(FailureCode.INVALID_OUTPUT) from None
            finished_at = _utc_now(self._clock)
            duration_ms = (self._monotonic() - started_tick) * 1000
            metadata = InferenceMetadata(
                request_id=request_id,
                identity=identity,
                settings=settings,
                response_model=reply.reported_model or reply.model,
                model_digest=reply.model_digest,
                server_version=reply.server_version,
                model_family=reply.model_family,
                quantization=reply.quantization,
                capability=capability.identifier,
                schema_version=capability.schema_version,
                schema_sha256=_hash(prepared.output_schema_json),
                prompt_sha256=_hash(
                    canonical_json(
                        {"instructions": prepared.instructions, "input": prepared.input_json}
                    )
                ),
                started_at=started_at,
                finished_at=finished_at,
                duration_ms=duration_ms,
            )
            return Proposal(value=value, metadata=metadata)
        except ModelFailure as error:
            failure = error.code
            raise
        except asyncio.CancelledError:
            failure = FailureCode.PROVIDER_FAILURE
            raise
        except Exception:
            failure = FailureCode.PROVIDER_FAILURE
            raise ModelFailure(failure) from None
        finally:
            if failure is not None and started_tick is not None:
                try:
                    duration_ms = (self._monotonic() - started_tick) * 1000
                except Exception:
                    duration_ms = 0.0
            # Registered configuration labels only; no input, output, endpoint or exception text.
            MODEL_LOG.info(
                canonical_json(
                    {
                        "request_id": request_id,
                        "provider": identity.provider if identity else None,
                        "model": identity.model if identity else None,
                        "capability": capability_id,
                        "duration_ms": round(duration_ms, 3)
                        if math.isfinite(duration_ms) and duration_ms >= 0
                        else 0,
                        "status": "success" if failure is None else "failure",
                        "error_code": failure.value if failure else None,
                    }
                )
            )

    @staticmethod
    def _prepare(capability: Capability[InputT, OutputT], request: InputT) -> PreparedInference:
        try:
            if type(request) is not capability.input_model:
                raise ModelFailure(FailureCode.INPUT_REJECTED)
            if (
                set(request.__dict__) - set(capability.input_model.model_fields)
                or request.__pydantic_extra__ is not None
            ):
                raise ModelFailure(FailureCode.INPUT_REJECTED)
            validated = capability.input_model.model_validate(
                request.model_dump(mode="python", warnings=False), strict=True
            )
            input_json = canonical_json(validated.model_dump(mode="json", warnings=False))
            if len(input_json.encode("utf-8")) > MAX_INPUT_BYTES:
                raise ModelFailure(FailureCode.INPUT_REJECTED)
            schema_json = canonical_json(capability.output_model.model_json_schema())
            if len(schema_json.encode("utf-8")) > MAX_SCHEMA_BYTES:
                raise ModelFailure(FailureCode.CONFIGURATION)
            return PreparedInference(
                instructions=capability.instructions,
                input_json=input_json,
                output_schema_json=schema_json,
            )
        except ModelFailure:
            raise
        except Exception:
            raise ModelFailure(FailureCode.INPUT_REJECTED) from None
