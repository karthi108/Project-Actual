"""Explicit synthetic scope and fixed loopback listener; no authentication claim."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Literal

from actual.core.primitives import ActorId, WorkspaceId


class ConfigurationError(Exception):
    """Only a generic configuration failure may leave the launch boundary."""


@dataclass(frozen=True)
class ApiSettings:
    workspace_id: WorkspaceId
    actor_id: ActorId
    port: int = 8765
    mode: Literal["synthetic-development"] = "synthetic-development"

    def __post_init__(self) -> None:
        try:
            object.__setattr__(self, "workspace_id", WorkspaceId.model_validate(self.workspace_id))
            object.__setattr__(self, "actor_id", ActorId.model_validate(self.actor_id))
            if type(self.port) is not int or not 1 <= self.port <= 65535:
                raise ValueError
            if self.mode != "synthetic-development":
                raise ValueError
        except (ValueError, TypeError):
            raise ConfigurationError("Explicit synthetic API configuration is required") from None

    @property
    def authorities(self) -> frozenset[str]:
        return frozenset(f"{host}:{self.port}" for host in ("localhost", "127.0.0.1", "[::1]"))

    @property
    def origins(self) -> frozenset[str]:
        return frozenset(f"http://{authority}" for authority in self.authorities)

    @classmethod
    def from_environment(cls) -> ApiSettings:
        try:
            if os.environ.get("ACTUAL_API_MODE") != "synthetic-development":
                raise ValueError
            port = os.environ.get("ACTUAL_API_PORT", "8765")
            if re.fullmatch(r"[1-9][0-9]{0,4}", port) is None:
                raise ValueError
            return cls(
                workspace_id=WorkspaceId(os.environ["ACTUAL_API_WORKSPACE_ID"]),
                actor_id=ActorId(os.environ["ACTUAL_API_ACTOR_ID"]),
                port=int(port),
            )
        except (ValueError, TypeError, KeyError, ConfigurationError):
            raise ConfigurationError("Explicit synthetic API configuration is required") from None
