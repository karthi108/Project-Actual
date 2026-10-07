"""Stable bounded jitter; no random replay-dependent control decisions."""

import hashlib


def maximum(base: int, attempt: int) -> int:
    if not 1 <= base <= 300 or not 0 <= attempt < 5:
        raise ValueError("Bounded retry parameters required")
    delay = min(300, base * (1 << attempt))
    return min(300, delay + delay // 4)


def delay(base: int, attempt: int, identity: str) -> int:
    maximum(base, attempt)
    value = min(300, base * (1 << attempt))
    window = value // 4
    jitter = int.from_bytes(hashlib.sha256(identity.encode()).digest()[:4]) % (window + 1)
    return min(300, value + jitter)
