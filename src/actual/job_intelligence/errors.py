"""Content-free failures at the Job Intelligence application boundary."""

from enum import StrEnum


class IntelligenceCode(StrEnum):
    INPUT_REJECTED = "input_rejected"
    INVALID_REQUIREMENT = "invalid_requirement"
    UNSAFE_SOURCE = "unsafe_source"
    DUPLICATE_REQUIREMENT = "duplicate_requirement"
    INVALID_ASSESSMENT = "invalid_assessment"


class IntelligenceFailure(Exception):
    def __init__(self, code: IntelligenceCode | str) -> None:
        try:
            self.code = IntelligenceCode(code)
        except (ValueError, TypeError):
            self.code = IntelligenceCode.INPUT_REJECTED
        super().__init__(self.code.value)
