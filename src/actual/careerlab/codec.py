"""Strict, non-coercing JSON schema boundary and canonical encoding."""

import json
import types
from dataclasses import fields, is_dataclass
from typing import Any, Literal, TypeAliasType, cast, get_args, get_origin, get_type_hints

from .contracts import GroundTruth, Record, ScenarioInput, SplitMembership


class SchemaError(ValueError):
    """A record does not match its closed fixture schema."""


def _decode(kind: Any, value: object, path: str) -> Any:
    if isinstance(kind, TypeAliasType):
        return _decode(kind.__value__, value, path)
    origin = get_origin(kind)
    args = get_args(kind)
    if origin is types.UnionType:
        for option in args:
            try:
                return _decode(option, value, path)
            except SchemaError:
                pass
        raise SchemaError(f"{path}: does not match permitted union")
    if origin is Literal:
        if not any(type(value) is type(item) and value == item for item in args):
            raise SchemaError(f"{path}: unsupported literal")
        return value
    if origin is tuple:
        if not isinstance(value, list):
            raise SchemaError(f"{path}: expected JSON array")
        if len(args) != 2 or args[1] is not Ellipsis:
            raise SchemaError(f"{path}: unsupported tuple schema")
        return tuple(_decode(args[0], item, f"{path}[{i}]") for i, item in enumerate(value))
    if isinstance(kind, type) and is_dataclass(kind):
        if not isinstance(value, dict) or not all(isinstance(k, str) for k in value):
            raise SchemaError(f"{path}: expected record")
        hints = get_type_hints(kind)
        expected = {field.name for field in fields(kind)}
        if set(value) != expected:
            raise SchemaError(f"{path}: fields differ; expected {sorted(expected)}")
        decoded = {name: _decode(hints[name], value[name], f"{path}.{name}") for name in hints}
        return kind(**decoded)
    if kind in (str, int, bool, type(None)) and type(value) is kind:
        return value
    raise SchemaError(f"{path}: wrong type")


def _encode(value: object) -> object:
    if isinstance(value, Record):
        return {field.name: _encode(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, tuple):
        return [_encode(item) for item in value]
    if value is None or type(value) in (str, int, bool):
        return value
    raise SchemaError("Only closed fixture records may be serialized")


def decode_record[T](kind: type[T], value: object) -> T:
    return cast(T, _decode(kind, value, kind.__name__))


def record_data(value: Record) -> dict[str, object]:
    data = cast(dict[str, object], _encode(value))
    # Validate Python-created records as strictly as records arriving via JSON.
    decode_record(type(value), data)
    return data


def canonical_bytes(value: object) -> bytes:
    """Stable JSON: sorted keys, fixed separators, UTF-8 and one LF terminator."""
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def observable_bytes(value: ScenarioInput) -> bytes:
    if type(value) is not ScenarioInput:
        raise SchemaError("Observable entry point accepts ScenarioInput only")
    return canonical_bytes(record_data(value))


def oracle_bytes(value: GroundTruth) -> bytes:
    if type(value) is not GroundTruth:
        raise SchemaError("Evaluator entry point accepts GroundTruth only")
    return canonical_bytes(record_data(value))


def membership_bytes(value: SplitMembership) -> bytes:
    return canonical_bytes(record_data(value))


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise SchemaError(f"Duplicate JSON field: {key}")
        result[key] = value
    return result


def load_record[T](kind: type[T], payload: bytes) -> T:
    try:
        data = json.loads(payload, object_pairs_hook=_unique_object)
    except (ValueError, UnicodeError) as error:
        raise SchemaError("Invalid fixture JSON") from error
    return decode_record(kind, data)
