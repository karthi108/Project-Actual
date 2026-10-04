"""Restricted local synthetic inference configuration; no installation changes."""

import os
import re
from dataclasses import asdict, dataclass, field
from typing import Literal
from urllib.parse import urlsplit

from .contracts import GenerationSettings
from .errors import FailureCode, ModelFailure

LOCAL_QWEN_MODELS = frozenset({"qwen3:4b-instruct", "qwen3:8b", "qwen3.5:4b-q4_K_M"})


@dataclass(frozen=True)
class OllamaSettings:
    base_url: str = "http://127.0.0.1:11434"
    model: str = "qwen3:4b-instruct"
    generation: GenerationSettings = field(default_factory=GenerationSettings)
    mode: Literal["synthetic-development"] = "synthetic-development"

    def __post_init__(self) -> None:
        if (
            self.mode != "synthetic-development"
            or not isinstance(self.model, str)
            or self.model not in LOCAL_QWEN_MODELS
            or not isinstance(self.generation, GenerationSettings)
            or not isinstance(self.base_url, str)
            or len(self.base_url) > 256
            or any(character.isspace() for character in self.base_url)
        ):
            raise ModelFailure(FailureCode.CONFIGURATION)
        object.__setattr__(self, "generation", GenerationSettings(**asdict(self.generation)))
        try:
            parsed = urlsplit(self.base_url)
            host, port = parsed.hostname, parsed.port
            if (
                parsed.scheme != "http"
                or host not in {"127.0.0.1", "localhost", "::1"}
                or port is None
                or not 1 <= port <= 65535
                or parsed.username is not None
                or parsed.password is not None
                or parsed.path not in {"", "/"}
                or parsed.query
                or parsed.fragment
                or "?" in self.base_url
                or "#" in self.base_url
            ):
                raise ValueError
        except ValueError:
            raise ModelFailure(FailureCode.CONFIGURATION) from None
        # Resolve the accepted localhost spelling without any DNS lookup.
        canonical_host = "[::1]" if host == "::1" else "127.0.0.1"
        object.__setattr__(self, "base_url", f"http://{canonical_host}:{port}")

    @classmethod
    def from_environment(cls) -> "OllamaSettings":
        if os.environ.get("ACTUAL_MODEL_MODE") != "synthetic-development":
            raise ModelFailure(FailureCode.CONFIGURATION)

        def number(name: str, default: int) -> int:
            raw = os.environ.get(name, str(default))
            if not re.fullmatch(r"[0-9]{1,6}", raw):
                raise ModelFailure(FailureCode.CONFIGURATION)
            return int(raw)

        return cls(
            base_url=os.environ.get("ACTUAL_OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
            model=os.environ.get("ACTUAL_OLLAMA_MODEL", "qwen3:4b-instruct"),
            generation=GenerationSettings(
                timeout_seconds=float(number("ACTUAL_MODEL_TIMEOUT_SECONDS", 120)),
                context_tokens=number("ACTUAL_MODEL_CONTEXT_TOKENS", 4096),
                max_output_tokens=number("ACTUAL_MODEL_MAX_OUTPUT_TOKENS", 128),
            ),
        )
