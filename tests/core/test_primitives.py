"""Canonical and strict boundary properties shared by all domain contracts."""

import json
from datetime import UTC, datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from actual.core import primitives as p
from actual.core.references import BusinessObjectRef
from actual.core.workflow import ContentReview


def review() -> ContentReview:
    return ContentReview(
        revision=1,
        content_digest="a" * 64,
        reviewer_id=p.ActorId("actor_" + "1" * 32),
        reviewed_at=datetime(2026, 1, 1, tzinfo=UTC),
        method="source inspection",
        decision="accepted",
    )


def test_every_identifier_kind_is_strict_distinct_frozen_and_roundtrips() -> None:
    kinds = [
        kind
        for kind in vars(p).values()
        if isinstance(kind, type) and issubclass(kind, p.Identifier) and kind is not p.Identifier
    ]
    values = []
    for kind in kinds:
        value = kind(f"{kind.prefix}_" + "1" * 32)
        assert kind.model_validate_json(value.model_dump_json()) == value
        assert kind.model_json_schema()["pattern"] == f"^{kind.prefix}_[0-9a-f]{{32}}$"
        with pytest.raises(ValidationError):
            value.model_copy(update={"root": "untyped"})
        with pytest.raises(TypeError):
            kind.model_construct(root=value.root)
        for bad in (True, 42, "", "1" * 32, kind.prefix + "_" + "A" * 32):
            with pytest.raises(ValidationError):
                kind(bad)
        with pytest.raises(ValidationError):
            value.root = "changed"
        values.append(value)
    assert len(set(values)) == len(kinds)
    with pytest.raises(ValidationError):
        BusinessObjectRef(
            workspace_id=p.WorkspaceId("workspace_" + "1" * 32),
            classification="synthetic",
            kind="company",
            object_id=p.JobId("job_" + "1" * 32),
            revision=1,
            content_digest="a" * 64,
        )


def test_equivalent_offset_instants_have_identical_canonical_bytes() -> None:
    baseline = review()
    for minutes in range(-720, 841, 30):
        value = baseline.reviewed_at.astimezone(timezone(timedelta(minutes=minutes)))
        changed = baseline.model_copy(update={"reviewed_at": value})
        assert p.canonical_bytes(changed) == p.canonical_bytes(baseline)
        assert changed.reviewed_at.tzinfo is UTC
    assert b"2026-01-01T00:00:00.000000Z" in p.canonical_bytes(baseline)


@pytest.mark.parametrize(
    "value",
    [
        datetime(2026, 1, 1),
        "2026-01-01",
        "2026-01-01T00:00:00",
        "2026-13-01T00:00:00Z",
        "0001-01-01T00:00:00+01:00",
        "9999-12-31T23:59:59-01:00",
        "2026-01-01T00:00:00.1234567Z",
        "2026-01-01T00:00:00+01:00:30",
        True,
        1767225600,
    ],
)
def test_timestamps_reject_naive_or_coercible_values(value: object) -> None:
    with pytest.raises(ValidationError):
        review().model_copy(update={"reviewed_at": value})


@pytest.mark.parametrize(
    "field,value",
    [
        ("revision", True),
        ("revision", 0),
        ("revision", 2147483648),
        ("revision", "1"),
        ("content_digest", "A" * 64),
        ("method", " "),
        ("method", "x" * 201),
        ("method", "nul\x00text"),
        ("schema_version", "actual-core-v2"),
        ("authority", True),
    ],
)
def test_updates_revalidate_strict_values_and_closed_fields(field: str, value: object) -> None:
    with pytest.raises(ValidationError):
        review().model_copy(update={field: value})


def test_public_validation_cannot_disable_guards_or_construct_unchecked() -> None:
    body = review().model_dump()
    for options in (
        {"strict": False},
        {"extra": "allow"},
        {"extra": "ignore"},
        {"from_attributes": True},
    ):
        with pytest.raises(ValueError):
            ContentReview.model_validate(body, **options)
    with pytest.raises(TypeError):
        ContentReview.model_construct(**body)
    with pytest.raises(TypeError):
        ContentReview.model_validate_strings(body)


def test_forged_instance_is_rejected_on_revalidation_and_serialization() -> None:
    value = review()
    object.__setattr__(value, "revision", 0)
    for check in (ContentReview.model_validate, p.canonical_bytes):
        with pytest.raises(ValidationError):
            check(value)


def test_explicit_wire_versions_duplicate_keys_and_bounds() -> None:
    payload = p.canonical_bytes(review())
    assert p.load_contract(ContentReview, payload) == review()
    assert ContentReview.model_validate_json(payload) == review()
    body = json.loads(payload)
    del body["schema_version"]
    with pytest.raises(ValueError):
        ContentReview.model_validate_json(json.dumps(body))
    duplicate = payload.replace(b'"revision":1', b'"revision":1,"revision":2')
    with pytest.raises(ValueError, match="Duplicate"):
        ContentReview.model_validate_json(duplicate)
    with pytest.raises(TypeError):
        ContentReview.model_validate_json(2_000_001)
    with pytest.raises(ValueError):
        ContentReview.model_validate_json(b" " * 2_000_001)
    with pytest.raises(TypeError):
        p.canonical_bytes(object())


def test_json_schema_exposes_closed_version_and_review_bounds() -> None:
    schema = ContentReview.model_json_schema()
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == "actual-core-v1"
    revision = schema["properties"]["revision"]
    if "$ref" in revision:
        revision = schema["$defs"][revision["$ref"].split("/")[-1]]
    assert revision["minimum"] == 1


def test_deeply_nested_wire_fails_with_a_predictable_validation_error() -> None:
    payload = b'{"schema_version":"actual-core-v1","nested":' * 2000 + b"null" + b"}" * 2000
    with pytest.raises(ValueError, match="nesting"):
        ContentReview.model_validate_json(payload)
    with pytest.raises(ValueError, match="nesting"):
        p.load_contract(ContentReview, payload)
