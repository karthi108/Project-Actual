"""Replay the same bounded runtime with transient state and no provider handles."""

from datetime import UTC, datetime
from typing import Annotated, Literal, cast

from pydantic import Field

from actual.core.primitives import Contract, Digest, WorkspaceId
from actual.workflows.ir import Name, Step, Workflow, value_type
from actual.workflows.runtime import Runtime
from actual.workflows.state import Run, Value
from actual.workflows.storage import Conflict


class Case(Contract):
    id: Name
    classification: Literal["synthetic"] = "synthetic"
    workflow: Workflow
    trigger: Annotated[tuple[Value, ...], Field(max_length=8)] = ()
    # A historical observation, interpreted only inside the isolated simulator.
    observed_policy: Literal["allow", "deny"] = "deny"


class Result(Contract):
    case: Name
    definition_digest: Digest
    status: Literal["succeeded", "failed", "cancelled", "human_wait"]
    branches: tuple[Literal["true", "false"], ...]
    human_escalation: bool
    policy_denials: Annotated[int, Field(ge=0)]
    failure_code: Name | None
    steps: tuple[Name, ...]
    model_calls: Literal[0] = 0
    provider_calls: Literal[0] = 0


class Memory:
    def __init__(self, case: Case):
        case = Case.model_validate(case)
        expected = {slot.name: slot.type for slot in case.workflow.trigger_schema}
        if (
            len(case.trigger) != len(expected)
            or {v.name: value_type(v.value) for v in case.trigger} != expected
        ):
            raise ValueError("Replay trigger schema mismatch")
        self.workflow = case.workflow
        self.run = Run(
            id="run_replay",
            workspace_id=WorkspaceId("workspace_" + "0" * 32),
            definition_digest=case.workflow.digest,
            trigger_id=case.id,
            trigger=case.trigger,
            current=next(s.id for s in case.workflow.steps if s.kind == "trigger"),
            started_at=datetime(2026, 10, 7, tzinfo=UTC),
        )
        self.fence = 0

    def load(self, identifier: str) -> Run:
        if identifier != self.run.id:
            raise Conflict("Unknown replay run")
        return self.run

    def definition(self, digest: str) -> Workflow:
        if digest != self.workflow.digest:
            raise Conflict("Replay definition mismatch")
        return self.workflow

    def claim(self, identifier: str, now: datetime) -> tuple[Run, int] | None:
        run = self.load(identifier)
        if run.status in ("succeeded", "failed", "cancelled") or (
            run.due_at is not None and run.due_at > now
        ):
            return None
        self.fence += 1
        return run, self.fence

    def finish(self, old: Run, fence: int, changed: Run, now: datetime) -> Run:
        if old != self.run or fence != self.fence or changed.revision != old.revision + 1:
            raise Conflict("Stale replay state")
        self.run = Run.model_validate(changed)
        return self.run


class _ObservedPolicy:
    def __init__(self, observation: Literal["allow", "deny"]):
        self.observation = observation

    def allows(self, run: Run, workflow: Workflow, step: Step) -> bool:
        return self.observation == "allow"


def replay(case: Case, mode: Literal["replay", "shadow"] = "replay") -> Result:
    case = Case.model_validate(case)
    memory = Memory(case)
    now = memory.run.started_at
    runtime = Runtime(memory, _ObservedPolicy(case.observed_policy), clock=lambda: now, mode=mode)
    for _ in range(case.workflow.max_steps * 3 + 2):
        run = runtime.tick(memory.run.id)
        if run.status in ("succeeded", "failed", "cancelled", "human_wait"):
            break
        if run.due_at is not None:
            now = run.due_at
    else:
        raise Conflict("Replay driver budget exceeded")
    return Result(
        case=case.id,
        definition_digest=case.workflow.digest,
        status=run.status,
        branches=tuple(
            cast(Literal["true", "false"], p.outcome)
            for p in run.progress
            if p.outcome in ("true", "false")
        ),
        human_escalation=run.status == "human_wait",
        policy_denials=sum(p.outcome == "deny" for p in run.progress),
        failure_code=run.failure_code,
        steps=tuple(p.step for p in run.progress),
    )
