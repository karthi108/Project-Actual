"""Bounded run snapshots; definitions and progress remain separate."""

from typing import Annotated, Literal

from pydantic import Field

from actual.core.primitives import ActorId, Contract, Digest, Instant, WorkspaceId

from .ir import Name, Scalar


class Value(Contract):
    name: Name
    value: Scalar


class Output(Contract):
    step: Name
    values: Annotated[tuple[Value, ...], Field(max_length=8)]


class Progress(Contract):
    step: Name
    attempt: Annotated[int, Field(ge=1, le=5)]
    outcome: Name
    at: Instant


class Run(Contract):
    runtime_version: Literal["actual-runtime-v1"] = "actual-runtime-v1"
    id: Name
    workspace_id: WorkspaceId
    initiator: ActorId | None = None
    definition_digest: Digest
    trigger_id: Name
    trigger: Annotated[tuple[Value, ...], Field(max_length=8)]
    current: Name
    status: Literal["ready", "waiting", "human_wait", "succeeded", "failed", "cancelled"] = "ready"
    revision: Annotated[int, Field(ge=1)] = 1
    attempts: Annotated[int, Field(ge=0, le=5)] = 0
    executions: Annotated[int, Field(ge=0, le=320)] = 0
    started_at: Instant
    due_at: Instant | None = None
    outputs: Annotated[tuple[Output, ...], Field(max_length=64)] = ()
    progress: Annotated[tuple[Progress, ...], Field(max_length=320)] = ()
    failure_code: Name | None = None
