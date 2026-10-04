"""Content-free failures shared by gateway callers and model adapters."""

from enum import StrEnum


class FailureCode(StrEnum):
    CONFIGURATION = "configuration"
    LOCAL_PRIVACY_REQUIRED = "local_privacy_required"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    MODEL_NOT_FOUND = "model_not_found"
    MODEL_UNAVAILABLE = "model_unavailable"
    TIMEOUT = "timeout"
    PROVIDER_FAILURE = "provider_failure"
    INVALID_PROVIDER_RESPONSE = "invalid_provider_response"
    INVALID_OUTPUT = "invalid_output"
    INPUT_REJECTED = "input_rejected"
    UNSUPPORTED_CAPABILITY = "unsupported_capability"
    OUTPUT_LIMIT = "output_limit"


class ModelFailure(Exception):
    """Never retain provider response bodies, prompts or raw transport errors."""

    def __init__(self, code: FailureCode) -> None:
        self.code = code
        super().__init__(code.value)
