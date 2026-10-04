"""Stable application failures contain codes, never client data or source prose."""

from enum import StrEnum


class UseCaseCode(StrEnum):
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    STATE_CONFLICT = "STATE_CONFLICT"
    STALE_GENERATION = "STALE_GENERATION"
    DUPLICATE_RESOURCE = "DUPLICATE_RESOURCE"
    INVALID_APPLICATION_TRANSITION = "INVALID_APPLICATION_TRANSITION"
    INVALID_DOMAIN_INPUT = "INVALID_DOMAIN_INPUT"
    DEPENDENCY_RECONCILIATION_REQUIRED = "DEPENDENCY_RECONCILIATION_REQUIRED"
    SYNTHETIC_ONLY = "SYNTHETIC_ONLY"


class UseCaseError(Exception):
    def __init__(self, code: UseCaseCode) -> None:
        self.code = code
        super().__init__(code.value)
