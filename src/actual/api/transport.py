"""Bound unauthenticated development traffic before parsing or use-case execution."""

import asyncio
import ipaddress
import json
import logging
import math
from time import monotonic
from uuid import uuid4

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from .config import ApiSettings
from .contracts import ErrorDetail, ErrorResponse

BODY_LIMIT = 262_144
BODY_TIMEOUT_SECONDS = 5.0
JSON_DEPTH_LIMIT = 32
REQUEST_LOG = logging.getLogger("actual.api.requests")


def error_response(scope: Scope, status: int, code: str, message: str) -> JSONResponse:
    state = scope.setdefault("state", {})
    state["error_code"] = code
    response = ErrorResponse(
        error=ErrorDetail(code=code, message=message), request_id=state["request_id"]
    )
    return JSONResponse(status_code=status, content=response.model_dump(mode="json"))


class BoundaryFailure(Exception):
    def __init__(self, status: int, code: str, message: str) -> None:
        self.status, self.code, self.message = status, code, message


def _header(scope: Scope, name: bytes) -> bytes | None:
    values = [value for key, value in scope["headers"] if key.lower() == name]
    if len(values) > 1:
        raise BoundaryFailure(400, "INVALID_HEADERS", "Ambiguous request headers are forbidden.")
    return values[0] if values else None


def _unique(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, child in pairs:
        if key in value:
            raise ValueError
        value[key] = child
    return value


def _constant(value: str) -> object:
    raise ValueError


def _check_json(body: bytes) -> None:
    try:
        value = json.loads(
            body.decode("utf-8"), object_pairs_hook=_unique, parse_constant=_constant
        )
        if not isinstance(value, dict):
            raise ValueError
        pending: list[tuple[object, int]] = [(value, 1)]
        while pending:
            item, depth = pending.pop()
            if depth > JSON_DEPTH_LIMIT:
                raise ValueError
            if isinstance(item, dict):
                for key, child in item.items():
                    key.encode("utf-8")
                    pending.append((child, depth + 1))
            elif isinstance(item, list):
                pending.extend((child, depth + 1) for child in item)
            elif isinstance(item, str):
                item.encode("utf-8")
            elif isinstance(item, float) and not math.isfinite(item):
                raise ValueError
    except (ValueError, UnicodeError, RecursionError):
        raise BoundaryFailure(
            422, "INVALID_JSON", "A bounded unambiguous JSON object is required."
        ) from None


class LocalBoundary:
    def __init__(self, app: ASGIApp, settings: ApiSettings) -> None:
        self.app, self.settings = app, settings

    def _destination(self, scope: Scope) -> None:
        peer = scope.get("client")
        try:
            if peer is None or not ipaddress.ip_address(peer[0]).is_loopback:
                raise ValueError
        except ValueError:
            raise BoundaryFailure(
                403, "LOCAL_ONLY", "Only direct loopback requests are permitted."
            ) from None
        host = _header(scope, b"host")
        if host is None or host.decode("latin-1").lower() not in self.settings.authorities:
            raise BoundaryFailure(400, "INVALID_HOST", "The request destination is not allowed.")
        origin = _header(scope, b"origin")
        if origin is not None and origin.decode("latin-1") not in self.settings.origins:
            raise BoundaryFailure(403, "INVALID_ORIGIN", "The request origin is not allowed.")
        fetch = _header(scope, b"sec-fetch-site")
        if fetch is not None and fetch not in (b"none", b"same-origin"):
            raise BoundaryFailure(403, "INVALID_ORIGIN", "The request origin is not allowed.")

    async def _body(self, scope: Scope, receive: Receive) -> bytes:
        encoding = _header(scope, b"content-encoding")
        if encoding is not None and encoding.lower() != b"identity":
            raise BoundaryFailure(
                415, "UNSUPPORTED_ENCODING", "Compressed request bodies are forbidden."
            )
        length = _header(scope, b"content-length")
        if length is not None:
            if not length.isdigit() or len(length) > 10:
                raise BoundaryFailure(400, "INVALID_LENGTH", "Invalid request length.")
            if int(length) > BODY_LIMIT:
                raise BoundaryFailure(413, "BODY_TOO_LARGE", "Request body exceeds the API limit.")
        if scope["method"] == "POST":
            media = _header(scope, b"content-type")
            if media is None or media.lower().split(b";", 1)[0].strip() != b"application/json":
                raise BoundaryFailure(415, "JSON_REQUIRED", "Commands require application/json.")
        chunks = bytearray()
        deadline = monotonic() + BODY_TIMEOUT_SECONDS
        while True:
            remaining = deadline - monotonic()
            if remaining <= 0:
                raise BoundaryFailure(408, "BODY_TIMEOUT", "Request body did not arrive in time.")
            try:
                message = await asyncio.wait_for(receive(), timeout=remaining)
            except TimeoutError:
                raise BoundaryFailure(
                    408, "BODY_TIMEOUT", "Request body did not arrive in time."
                ) from None
            if message["type"] != "http.request":
                raise BoundaryFailure(400, "INCOMPLETE_REQUEST", "Request body was incomplete.")
            chunks.extend(message.get("body", b""))
            if len(chunks) > BODY_LIMIT:
                raise BoundaryFailure(413, "BODY_TOO_LARGE", "Request body exceeds the API limit.")
            if not message.get("more_body", False):
                break
        body = bytes(chunks)
        if length is not None and len(body) != int(length):
            raise BoundaryFailure(400, "INVALID_LENGTH", "Invalid request length.")
        if scope["method"] == "POST":
            _check_json(body)
        elif body:
            raise BoundaryFailure(422, "UNEXPECTED_BODY", "This operation does not accept a body.")
        return body

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        started = monotonic()
        scope.setdefault("state", {})["request_id"] = uuid4().hex
        status, response_started = 500, False

        async def safe_send(message: Message) -> None:
            nonlocal status, response_started
            if message["type"] == "http.response.start":
                response_started = True
                status = message["status"]
                excluded = {b"cache-control", b"x-content-type-options", b"x-request-id"}
                headers = [
                    (key, val)
                    for key, val in message.get("headers", [])
                    if key.lower() not in excluded
                ]
                headers.extend(
                    (
                        (b"cache-control", b"no-store"),
                        (b"x-content-type-options", b"nosniff"),
                        (b"x-request-id", scope["state"]["request_id"].encode("ascii")),
                    )
                )
                message = {**message, "headers": headers}
            await send(message)

        try:
            self._destination(scope)
            body = await self._body(scope, receive)
            delivered = False

            async def replay() -> Message:
                nonlocal delivered
                if delivered:
                    return await receive()
                delivered = True
                return {"type": "http.request", "body": body, "more_body": False}

            await self.app(scope, replay, safe_send)
        except BoundaryFailure as error:
            await error_response(scope, error.status, error.code, error.message)(
                scope, receive, safe_send
            )
        except Exception:
            if response_started:
                raise
            await error_response(
                scope, 500, "INTERNAL_ERROR", "The request could not be completed."
            )(scope, receive, safe_send)
        finally:
            route = scope.get("route")
            REQUEST_LOG.info(
                json.dumps(
                    {
                        "request_id": scope["state"]["request_id"],
                        "method": scope["method"]
                        if scope["method"]
                        in ("GET", "POST", "HEAD", "OPTIONS", "PUT", "PATCH", "DELETE")
                        else "OTHER",
                        "route": getattr(route, "path", "unmatched"),
                        "status": status,
                        "duration_ms": round((monotonic() - started) * 1000, 3),
                        "error_code": scope["state"].get("error_code"),
                    },
                    separators=(",", ":"),
                )
            )
