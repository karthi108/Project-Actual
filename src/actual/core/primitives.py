"""Closed immutable boundary records, opaque typed IDs and canonical UTC values."""

import hashlib
import json
import re
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Annotated, Any, ClassVar, Literal, Self

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    GetJsonSchemaHandler,
    PlainSerializer,
    RootModel,
    model_validator,
)
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import CoreSchema


class Contract(BaseModel):
    model_config = ConfigDict(
        strict=True,
        extra="forbid",
        frozen=True,
        validate_default=True,
        revalidate_instances="always",
        hide_input_in_errors=True,
    )
    schema_version: Literal["actual-core-v1"] = "actual-core-v1"

    @classmethod
    def model_validate(
        cls,
        obj: Any,
        *,
        strict: bool | None = None,
        extra: Literal["allow", "ignore", "forbid"] | None = None,
        from_attributes: bool | None = None,
        context: Any | None = None,
        by_alias: bool | None = None,
        by_name: bool | None = None,
    ) -> Self:
        if strict is False or extra in ("allow", "ignore") or from_attributes is True:
            raise ValueError("Domain validation cannot disable strict closed fields")
        return super().model_validate(
            obj,
            strict=True,
            extra="forbid",
            from_attributes=from_attributes,
            context=context,
            by_alias=by_alias,
            by_name=by_name,
        )

    @classmethod
    def model_validate_json(
        cls,
        json_data: str | bytes | bytearray,
        *,
        strict: bool | None = None,
        extra: Literal["allow", "ignore", "forbid"] | None = None,
        context: Any | None = None,
        by_alias: bool | None = None,
        by_name: bool | None = None,
    ) -> Self:
        if strict is False or extra in ("allow", "ignore"):
            raise ValueError("Domain validation cannot disable strict closed fields")
        if not isinstance(json_data, (str, bytes, bytearray)):
            raise TypeError("JSON input must be text or bytes")
        if len(json_data) > 2_000_000:
            raise ValueError("Bounded JSON required")
        payload = json_data.encode("utf-8") if isinstance(json_data, str) else bytes(json_data)
        if len(payload) > 2_000_000:
            raise ValueError("Bounded JSON required")
        try:
            value = json.loads(payload, object_pairs_hook=_unique_pairs)
            _versions(value)
        except RecursionError as error:
            raise ValueError("JSON nesting exceeds the contract boundary") from error
        return super().model_validate_json(
            canonical_data(value),
            strict=True,
            extra="forbid",
            context=context,
            by_alias=by_alias,
            by_name=by_name,
        )

    @classmethod
    def model_validate_strings(
        cls,
        obj: Any,
        *,
        strict: bool | None = None,
        extra: Literal["allow", "ignore", "forbid"] | None = None,
        context: Any | None = None,
        by_alias: bool | None = None,
        by_name: bool | None = None,
    ) -> Self:
        raise TypeError("String coercion is not a domain boundary")

    @classmethod
    def model_construct(cls, _fields_set: set[str] | None = None, **values: Any) -> Self:
        raise TypeError("Unchecked construction is not a domain boundary")

    def model_copy(self, *, update: Mapping[str, Any] | None = None, deep: bool = False) -> Self:
        """Replacements are new validated snapshots, never unchecked updates."""
        return type(self).model_validate({**self.model_dump(mode="python"), **(update or {})})


class Identifier(RootModel[str]):
    model_config = ConfigDict(strict=True, frozen=True, revalidate_instances="always")
    prefix: ClassVar[str] = ""

    @classmethod
    def model_construct(cls, *args: Any, **values: Any) -> Self:
        raise TypeError("Unchecked identifier construction is not a domain boundary")

    def model_copy(self, *, update: Mapping[str, Any] | None = None, deep: bool = False) -> Self:
        changes = update or {}
        if set(changes) - {"root"}:
            raise ValueError("Unknown identifier fields")
        return type(self).model_validate(changes.get("root", self.root), strict=True)

    @classmethod
    def __get_pydantic_json_schema__(
        cls, schema: CoreSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        value = handler(schema)
        if cls.prefix:
            value["pattern"] = f"^{cls.prefix}_[0-9a-f]{{32}}$"
        return value

    @model_validator(mode="after")
    def valid_identifier(self) -> Self:
        if not self.prefix or not re.fullmatch(self.prefix + r"_[0-9a-f]{32}", self.root):
            raise ValueError("Expected a kind-prefixed opaque identifier")
        return self


class WorkspaceId(Identifier):
    prefix = "workspace"


class ActorId(Identifier):
    prefix = "actor"


class CompanyId(Identifier):
    prefix = "company"


class JobId(Identifier):
    prefix = "job"


class OpportunityId(Identifier):
    prefix = "opportunity"


class ProfileId(Identifier):
    prefix = "profile"


class ClaimId(Identifier):
    prefix = "claim"


class EvidenceId(Identifier):
    prefix = "evidence"


class CVId(Identifier):
    prefix = "cv"


class DraftId(Identifier):
    prefix = "draft"


class ApplicationId(Identifier):
    prefix = "application"


class RequirementId(Identifier):
    prefix = "requirement"


class AssessmentId(Identifier):
    prefix = "assessment"


class EventId(Identifier):
    prefix = "event"


class CorrelationId(Identifier):
    prefix = "correlation"


class SourceEventId(Identifier):
    prefix = "source_event"


def _nonblank(value: str) -> str:
    if not value.strip() or "\x00" in value:
        raise ValueError("Nonblank text without NUL required")
    return value


type Text = Annotated[
    str, Field(strict=True, min_length=1, max_length=12000), AfterValidator(_nonblank)
]
type Label = Annotated[
    str, Field(strict=True, min_length=1, max_length=200), AfterValidator(_nonblank)
]
type SourceReference = Annotated[
    str, Field(strict=True, min_length=1, max_length=512), AfterValidator(_nonblank)
]
type Symbol = Annotated[str, Field(strict=True, pattern=r"^[a-z][a-z0-9_]{0,63}$")]
type Digest = Annotated[str, Field(strict=True, pattern=r"^[0-9a-f]{64}$")]
type Revision = Annotated[int, Field(strict=True, ge=1, le=2147483647)]
type Classification = Literal["synthetic", "personal", "sensitive"]


def classification_allows(parent: Classification, child: Classification) -> bool:
    if parent == "synthetic" or child == "synthetic":
        return parent == child
    return parent == "sensitive" or child == "personal"


def _instant(value: object) -> datetime:
    if isinstance(value, str):
        if not re.fullmatch(
            r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
            r"(?:\.[0-9]{1,6})?(?:Z|[+-][0-9]{2}:[0-9]{2})",
            value,
        ):
            raise ValueError(
                "ISO timestamp with explicit timezone and microsecond precision required"
            )
        try:
            value = datetime.fromisoformat(value)
        except ValueError as error:
            raise ValueError("Invalid timestamp") from error
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Timezone-aware timestamp required")
    try:
        return value.astimezone(UTC)
    except (OverflowError, ValueError) as error:
        raise ValueError("Timestamp outside representable UTC range") from error


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


type Instant = Annotated[datetime, BeforeValidator(_instant), PlainSerializer(_iso)]


def canonical_data(value: object) -> bytes:
    return (
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        )
        + "\n"
    ).encode("utf-8")


def content_digest(value: object) -> str:
    """Hash explicitly selected JSON data; a digest is identity, not authenticity."""
    return hashlib.sha256(canonical_data(value)).hexdigest()


def canonical_bytes(value: Contract) -> bytes:
    if not isinstance(value, Contract):
        raise TypeError("Only domain contracts can be serialized")
    checked = type(value).model_validate(value)
    payload = canonical_data(checked.model_dump(mode="json"))
    if len(payload) > 2_000_000:
        raise ValueError("Contract exceeds bounded wire size")
    return payload


def _unique_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def _versions(value: object) -> None:
    if isinstance(value, dict):
        if value.get("schema_version") != "actual-core-v1":
            raise ValueError("Missing or unsupported explicit schema version")
        for child in value.values():
            _versions(child)
    elif isinstance(value, list):
        for child in value:
            _versions(child)


def load_contract[T: Contract](kind: type[T], payload: bytes) -> T:
    if type(payload) is not bytes or len(payload) > 2_000_000:
        raise ValueError("Bounded JSON bytes required")
    return kind.model_validate_json(payload, strict=True)
