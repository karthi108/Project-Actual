"""Small provider-independent contracts; model proposals confer no authority."""

import math
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal, Protocol, TypeVar

from pydantic import BaseModel

from actual.models.errors import FailureCode, ModelFailure

InputT = TypeVar("InputT", bound=BaseModel)
OutputT = TypeVar("OutputT", bound=BaseModel)

MAX_INPUT_BYTES = 4096
MAX_OUTPUT_BYTES = 32768
MAX_INSTRUCTIONS_BYTES = 8192
MAX_SCHEMA_BYTES = 16384


def _label(value: object, *, maximum: int = 128, model: bool = False) -> bool:
    expression = r"[A-Za-z0-9][A-Za-z0-9._:/-]*" if model else r"[A-Za-z0-9][A-Za-z0-9._-]*"
    return (
        type(value) is str and len(value) <= maximum and re.fullmatch(expression, value) is not None
    )


@dataclass(frozen=True, kw_only=True)
class GenerationSettings:
    timeout_seconds: float = 120.0
    context_tokens: int = 4096
    max_output_tokens: int = 128
    temperature: float = 0.0
    seed: int = 42

    def __post_init__(self) -> None:
        if (
            type(self.timeout_seconds) not in (int, float)
            or not math.isfinite(self.timeout_seconds)
            or not 1 <= self.timeout_seconds <= 300
            or type(self.context_tokens) is not int
            or not 512 <= self.context_tokens <= 8192
            or type(self.max_output_tokens) is not int
            or not 16 <= self.max_output_tokens <= 512
            or type(self.temperature) not in (int, float)
            or self.temperature != 0
            or type(self.seed) is not int
            or not 0 <= self.seed <= 2**31 - 1
        ):
            raise ModelFailure(FailureCode.CONFIGURATION)
        object.__setattr__(self, "timeout_seconds", float(self.timeout_seconds))
        object.__setattr__(self, "temperature", 0.0)


@dataclass(frozen=True, kw_only=True)
class ProviderIdentity:
    provider: str
    model: str
    endpoint: str = field(repr=False)

    def __post_init__(self) -> None:
        if (
            not _label(self.provider, maximum=32)
            or not _label(self.model, maximum=128, model=True)
            or type(self.endpoint) is not str
            or not self.endpoint
            or len(self.endpoint) > 128
        ):
            raise ModelFailure(FailureCode.CONFIGURATION)


@dataclass(frozen=True, kw_only=True)
class PreparedInference:
    """Transport-ready data produced only after a registered input is validated."""

    instructions: str = field(repr=False)
    input_json: str = field(repr=False)
    output_schema_json: str = field(repr=False)


@dataclass(frozen=True, kw_only=True)
class ProviderReply:
    content: str = field(repr=False)
    model: str
    model_digest: str | None
    server_version: str | None
    reported_model: str | None = None
    model_family: str | None = None
    quantization: str | None = None

    def __post_init__(self) -> None:
        if (
            type(self.content) is not str
            or not _label(self.model, model=True)
            or (
                self.model_digest is not None
                and (
                    type(self.model_digest) is not str
                    or re.fullmatch(r"(?:sha256:)?[a-f0-9]{64}", self.model_digest) is None
                )
            )
            or (self.server_version is not None and not _label(self.server_version, maximum=64))
            or (self.reported_model is not None and not _label(self.reported_model, model=True))
            or (self.model_family is not None and not _label(self.model_family, maximum=64))
            or (self.quantization is not None and not _label(self.quantization, maximum=64))
        ):
            raise ModelFailure(FailureCode.INVALID_PROVIDER_RESPONSE)


class ModelProvider(Protocol):
    @property
    def identity(self) -> ProviderIdentity: ...

    @property
    def settings(self) -> GenerationSettings: ...

    async def infer(self, request: PreparedInference) -> ProviderReply: ...


@dataclass(frozen=True, kw_only=True)
class Capability[Input: BaseModel, Output: BaseModel]:
    """Trusted application code owns instructions, types and version identifiers."""

    name: str
    version: str
    schema_version: str
    input_model: type[Input]
    output_model: type[Output]
    instructions: str = field(repr=False)

    def __post_init__(self) -> None:
        if (
            not _label(self.name, maximum=64)
            or not _label(self.version, maximum=32)
            or not _label(self.schema_version, maximum=64)
            or type(self.instructions) is not str
            or not self.instructions.strip()
        ):
            raise ModelFailure(FailureCode.CONFIGURATION)
        try:
            instruction_size = len(self.instructions.encode("utf-8"))
        except UnicodeError:
            raise ModelFailure(FailureCode.CONFIGURATION) from None
        if instruction_size > MAX_INSTRUCTIONS_BYTES:
            raise ModelFailure(FailureCode.CONFIGURATION)
        for model in (self.input_model, self.output_model):
            if not isinstance(model, type) or not issubclass(model, BaseModel):
                raise ModelFailure(FailureCode.CONFIGURATION)
            if any(
                model.model_config.get(key) != value
                for key, value in (
                    ("strict", True),
                    ("extra", "forbid"),
                    ("frozen", True),
                    ("revalidate_instances", "always"),
                    ("hide_input_in_errors", True),
                )
            ):
                raise ModelFailure(FailureCode.CONFIGURATION)
        output_schema = self.output_model.model_json_schema()
        if output_schema.get("properties", {}).get("schema_version", {}).get(
            "const"
        ) != self.schema_version or "schema_version" not in output_schema.get("required", ()):
            raise ModelFailure(FailureCode.CONFIGURATION)

    @property
    def identifier(self) -> str:
        return f"{self.name}:{self.version}"


@dataclass(frozen=True, kw_only=True)
class InferenceMetadata:
    request_id: str
    identity: ProviderIdentity
    settings: GenerationSettings
    response_model: str
    model_digest: str | None
    server_version: str | None
    model_family: str | None
    quantization: str | None
    capability: str
    schema_version: str
    schema_sha256: str
    prompt_sha256: str
    started_at: datetime
    finished_at: datetime
    duration_ms: float
    proposal_only: Literal[True] = True

    def __post_init__(self) -> None:
        if (
            type(self.request_id) is not str
            or re.fullmatch(r"[a-f0-9]{32}", self.request_id) is None
            or type(self.identity) is not ProviderIdentity
            or type(self.settings) is not GenerationSettings
            or not _label(self.response_model, model=True)
            or (
                self.model_digest is not None
                and (
                    type(self.model_digest) is not str
                    or re.fullmatch(r"(?:sha256:)?[a-f0-9]{64}", self.model_digest) is None
                )
            )
            or (self.server_version is not None and not _label(self.server_version, maximum=64))
            or (self.model_family is not None and not _label(self.model_family, maximum=64))
            or (self.quantization is not None and not _label(self.quantization, maximum=64))
            or not _label(self.capability, model=True)
            or not _label(self.schema_version, maximum=64)
            or any(
                type(value) is not str or re.fullmatch(r"[a-f0-9]{64}", value) is None
                for value in (self.schema_sha256, self.prompt_sha256)
            )
            or not isinstance(self.started_at, datetime)
            or not isinstance(self.finished_at, datetime)
            or self.started_at.tzinfo != UTC
            or self.finished_at.tzinfo != UTC
            or self.finished_at < self.started_at
            or type(self.duration_ms) not in (float, int)
            or not math.isfinite(self.duration_ms)
            or self.duration_ms < 0
            or self.proposal_only is not True
        ):
            raise ModelFailure(FailureCode.PROVIDER_FAILURE)


@dataclass(frozen=True, kw_only=True)
class Proposal[Output: BaseModel]:
    """Structural validity is not factual verification or permission to act."""

    value: Output = field(repr=False)
    metadata: InferenceMetadata
