"""Local Ollama transport. No capability instructions, tools or domain authority."""

import asyncio
import re
from dataclasses import asdict

import httpx2 as httpx
from pydantic import JsonValue

from .codec import decode_object, encode_object
from .config import OllamaSettings
from .contracts import (
    MAX_INSTRUCTIONS_BYTES,
    GenerationSettings,
    PreparedInference,
    ProviderIdentity,
    ProviderReply,
)
from .errors import FailureCode, ModelFailure

MAX_PROVIDER_BYTES = 131_072
SUPPORTED_SERVER = "0.34.3"


def _remote(record: dict[str, JsonValue]) -> bool:
    return any(record.get(key) not in (None, "") for key in ("remote_host", "remote_model"))


def _object(value: JsonValue) -> dict[str, JsonValue]:
    if not isinstance(value, dict):
        raise ModelFailure(FailureCode.INVALID_PROVIDER_RESPONSE)
    return value


def _string(value: JsonValue, limit: int = 128) -> str:
    if not isinstance(value, str) or not value or len(value) > limit:
        raise ModelFailure(FailureCode.INVALID_PROVIDER_RESPONSE)
    return value


class OllamaQwenProvider:
    """One fresh non-proxied client per bounded operation; injected transport is for tests."""

    def __init__(
        self,
        settings: OllamaSettings,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        # Revalidate even manually forged dataclass settings before any network access.
        self._configuration = OllamaSettings(
            settings.base_url, settings.model, settings.generation, settings.mode
        )
        self._transport = transport

    @property
    def identity(self) -> ProviderIdentity:
        return ProviderIdentity(
            provider="ollama",
            model=self._configuration.model,
            endpoint=self._configuration.base_url,
        )

    @property
    def settings(self) -> GenerationSettings:
        return GenerationSettings(**asdict(self._configuration.generation))

    async def _request(
        self,
        client: httpx.AsyncClient,
        path: str,
        body: dict[str, JsonValue] | None = None,
    ) -> dict[str, JsonValue]:
        method = "GET" if body is None else "POST"
        content = None if body is None else encode_object(body)
        async with client.stream(
            method,
            self._configuration.base_url + path,
            content=content,
            headers={"Content-Type": "application/json", "Accept-Encoding": "identity"},
            follow_redirects=False,
        ) as response:
            if path == "/api/status" and response.status_code != 200:
                raise ModelFailure(FailureCode.LOCAL_PRIVACY_REQUIRED)
            if response.status_code == 404 and path in {"/api/show", "/api/chat"}:
                raise ModelFailure(FailureCode.MODEL_NOT_FOUND)
            if response.status_code >= 500 and path == "/api/chat":
                raise ModelFailure(FailureCode.MODEL_UNAVAILABLE)
            if response.status_code != 200:
                raise ModelFailure(FailureCode.PROVIDER_FAILURE)
            if (
                response.headers.get("content-encoding", "identity").lower() != "identity"
                or response.headers.get("content-type", "").split(";", 1)[0].lower()
                != "application/json"
            ):
                raise ModelFailure(FailureCode.INVALID_PROVIDER_RESPONSE)
            declared = response.headers.get("content-length")
            if declared is not None:
                if not re.fullmatch(r"[0-9]{1,10}", declared):
                    raise ModelFailure(FailureCode.INVALID_PROVIDER_RESPONSE)
                if int(declared) > MAX_PROVIDER_BYTES:
                    raise ModelFailure(FailureCode.OUTPUT_LIMIT)
            collected = bytearray()
            async for chunk in response.aiter_raw():
                if len(collected) + len(chunk) > MAX_PROVIDER_BYTES:
                    raise ModelFailure(FailureCode.OUTPUT_LIMIT)
                collected.extend(chunk)
            if declared is not None and len(collected) != int(declared):
                raise ModelFailure(FailureCode.INVALID_PROVIDER_RESPONSE)
        record = decode_object(bytes(collected))
        if "error" in record:
            raise ModelFailure(
                FailureCode.MODEL_UNAVAILABLE
                if path == "/api/chat"
                else FailureCode.PROVIDER_FAILURE
            )
        return record

    async def infer(self, request: PreparedInference) -> ProviderReply:
        try:
            async with asyncio.timeout(self.settings.timeout_seconds):
                transport = (
                    self._transport
                    if self._transport is not None
                    else httpx.AsyncHTTPTransport(retries=0, trust_env=False)
                )
                async with httpx.AsyncClient(
                    transport=transport,
                    trust_env=False,
                    follow_redirects=False,
                    timeout=httpx.Timeout(self.settings.timeout_seconds, connect=5.0),
                ) as client:
                    return await self._infer(client, request)
        except ModelFailure:
            raise
        except (TimeoutError, httpx.TimeoutException):
            raise ModelFailure(FailureCode.TIMEOUT) from None
        except httpx.ConnectError:
            raise ModelFailure(FailureCode.PROVIDER_UNAVAILABLE) from None
        except httpx.HTTPError:
            raise ModelFailure(FailureCode.PROVIDER_FAILURE) from None
        except Exception:
            raise ModelFailure(FailureCode.INVALID_PROVIDER_RESPONSE) from None

    async def _infer(self, client: httpx.AsyncClient, request: PreparedInference) -> ProviderReply:
        if not isinstance(request, PreparedInference):
            raise ModelFailure(FailureCode.INPUT_REJECTED)
        # These checks are provider-specific; no prompt has been sent at this point.
        status = await self._request(client, "/api/status")
        cloud = status.get("cloud")
        if not isinstance(cloud, dict) or cloud.get("disabled") is not True:
            raise ModelFailure(FailureCode.LOCAL_PRIVACY_REQUIRED)
        version = _string((await self._request(client, "/api/version")).get("version"))
        # :local, truncate/shift and cloud status are verified for this concrete server.
        # Future versions require an explicit adapter compatibility review.
        if version != SUPPORTED_SERVER:
            raise ModelFailure(FailureCode.INVALID_PROVIDER_RESPONSE)
        catalog = (await self._request(client, "/api/tags")).get("models")
        if not isinstance(catalog, list):
            raise ModelFailure(FailureCode.INVALID_PROVIDER_RESPONSE)
        selected = [
            item
            for item in catalog
            if isinstance(item, dict) and item.get("name") == self.identity.model
        ]
        if not selected:
            raise ModelFailure(FailureCode.MODEL_NOT_FOUND)
        if len(selected) != 1:
            raise ModelFailure(FailureCode.INVALID_PROVIDER_RESPONSE)
        installed = selected[0]
        if _remote(installed):
            raise ModelFailure(FailureCode.LOCAL_PRIVACY_REQUIRED)
        details = _object(installed.get("details"))
        family = _string(details.get("family"))
        quantization = _string(details.get("quantization_level"))
        digest = _string(installed.get("digest"))
        if details.get("format") != "gguf" or not family.startswith("qwen"):
            raise ModelFailure(FailureCode.LOCAL_PRIVACY_REQUIRED)
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ModelFailure(FailureCode.INVALID_PROVIDER_RESPONSE)
        local_model = self.identity.model + ":local"
        shown = await self._request(client, "/api/show", {"model": local_model, "verbose": False})
        shown_details = _object(shown.get("details"))
        if (
            _remote(shown)
            or shown_details.get("format") != "gguf"
            or shown_details.get("family") != family
            or shown_details.get("quantization_level") != quantization
        ):
            raise ModelFailure(FailureCode.LOCAL_PRIVACY_REQUIRED)
        capabilities = shown.get("capabilities")
        if not isinstance(capabilities, list) or "completion" not in capabilities:
            raise ModelFailure(FailureCode.MODEL_UNAVAILABLE)
        schema = decode_object(
            request.output_schema_json.encode("utf-8"),
            max_bytes=16_384,
            code=FailureCode.INPUT_REJECTED,
        )
        input_data = decode_object(
            request.input_json.encode("utf-8"), max_bytes=4096, code=FailureCode.INPUT_REJECTED
        )
        if (
            not request.instructions
            or len(request.instructions.encode("utf-8")) > MAX_INSTRUCTIONS_BYTES
        ):
            raise ModelFailure(FailureCode.INPUT_REJECTED)
        body: dict[str, JsonValue] = {
            "model": local_model,
            "messages": [
                {"role": "system", "content": request.instructions},
                {"role": "user", "content": encode_object(input_data).decode("utf-8")},
            ],
            "format": schema,
            "stream": False,
            "think": False,
            "truncate": False,
            "shift": False,
            "keep_alive": 0,
            "options": {
                "temperature": self.settings.temperature,
                "seed": self.settings.seed,
                "num_ctx": self.settings.context_tokens,
                "num_predict": self.settings.max_output_tokens,
            },
        }
        result = await self._request(client, "/api/chat", body)
        if _remote(result):
            raise ModelFailure(FailureCode.LOCAL_PRIVACY_REQUIRED)
        if (
            result.get("done") is not True
            or result.get("done_reason") != "stop"
            or result.get("model") not in {self.identity.model, local_model}
        ):
            raise ModelFailure(FailureCode.INVALID_PROVIDER_RESPONSE)
        message = _object(result.get("message"))
        if message.get("role") != "assistant" or message.get("tool_calls") not in (None, []):
            raise ModelFailure(FailureCode.INVALID_PROVIDER_RESPONSE)
        if message.get("thinking") not in (None, ""):
            raise ModelFailure(FailureCode.INVALID_PROVIDER_RESPONSE)
        content = _string(message.get("content"), limit=32_768)
        return ProviderReply(
            content=content,
            model=self.identity.model,
            model_digest=digest,
            server_version=version,
            model_family=family,
            quantization=quantization,
            reported_model=_string(result.get("model")),
        )
