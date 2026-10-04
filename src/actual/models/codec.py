"""Bounded strict JSON for untrusted provider envelopes and model output."""

import json
import math
from typing import cast

from pydantic import JsonValue

from .errors import FailureCode, ModelFailure


def decode_object(
    data: bytes,
    *,
    max_bytes: int = 131_072,
    code: FailureCode = FailureCode.INVALID_PROVIDER_RESPONSE,
) -> dict[str, JsonValue]:
    if len(data) > max_bytes:
        raise ModelFailure(FailureCode.OUTPUT_LIMIT)

    def pairs(entries: list[tuple[str, JsonValue]]) -> dict[str, JsonValue]:
        result: dict[str, JsonValue] = {}
        for key, value in entries:
            if key in result:
                raise ValueError
            result[key] = value
        return result

    def nonfinite(value: str) -> None:
        raise ValueError

    def check(value: object, depth: int = 0) -> None:
        if depth > 32:
            raise ValueError
        if isinstance(value, str):
            value.encode("utf-8", errors="strict")
        elif isinstance(value, float) and not math.isfinite(value):
            raise ValueError
        elif isinstance(value, dict):
            for key, item in value.items():
                check(key, depth + 1)
                check(item, depth + 1)
        elif isinstance(value, list):
            for item in value:
                check(item, depth + 1)

    try:
        value: object = json.loads(
            data.decode("utf-8", errors="strict"), object_pairs_hook=pairs, parse_constant=nonfinite
        )
        if not isinstance(value, dict):
            raise ValueError
        check(value)
    except (ValueError, UnicodeError, RecursionError):
        raise ModelFailure(code) from None
    return cast(dict[str, JsonValue], value)


def encode_object(value: object) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        ).encode("utf-8", errors="strict")
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise ModelFailure(FailureCode.INPUT_REJECTED) from None
