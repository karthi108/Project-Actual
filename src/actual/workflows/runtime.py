"""One durable bounded step at a time; no background service or effect executor."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Literal, Protocol

from .connectors import ReadConnector, ToolError
from .deterministic import execute as deterministic
from .ir import Step, Workflow
from .state import Output, Progress, Run, Value


class RuntimeStore(Protocol):
    def load(self, identifier: str) -> Run: ...
    def claim(self, identifier: str, now: datetime) -> tuple[Run, int] | None: ...
    def definition(self, digest: str) -> Workflow: ...
    def finish(self, old: Run, fence: int, changed: Run, now: datetime) -> Run: ...


class Policy(Protocol):
    def allows(self, run: Run, workflow: Workflow, step: Step) -> bool: ...


class Deny:
    def allows(self, run: Run, workflow: Workflow, step: Step) -> bool:
        return False


class EffectExecutor(Protocol):
    def execute(
        self, run: Run, step: Step, values: tuple[Value, ...], fence: int
    ) -> tuple[Value, ...]: ...


def inputs(run: Run, step: Step) -> tuple[Value, ...]:
    result: list[Value] = []
    for binding in step.inputs:
        if binding.source == "literal":
            assert binding.value is not None
            value = binding.value
        else:
            source = (
                run.trigger
                if binding.source == "trigger"
                else next(output.values for output in run.outputs if output.step == binding.step)
            )
            value = next(item.value for item in source if item.name == binding.field)
        result.append(Value(name=binding.name, value=value))
    return tuple(result)


def route(
    workflow: Workflow, run: Run, outcome: str, now: datetime, values: tuple[Value, ...] = ()
) -> Run:
    target = next(
        edge.target
        for edge in workflow.edges
        if edge.source == run.current and edge.outcome == outcome
    )
    return run.model_copy(
        update={
            "current": target,
            "status": "ready",
            "due_at": None,
            "attempts": 0,
            "executions": run.executions + 1,
            "revision": run.revision + 1,
            "progress": (
                *run.progress,
                Progress(
                    step=run.current, attempt=max(1, run.attempts + 1), outcome=outcome, at=now
                ),
            ),
            "outputs": (*run.outputs, Output(step=run.current, values=values))
            if values
            else run.outputs,
        }
    )


class Runtime:
    def __init__(
        self,
        store: RuntimeStore,
        policy: Policy | None = None,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        connector: ReadConnector | None = None,
        effects: EffectExecutor | None = None,
        mode: Literal["synthetic", "replay", "shadow"] = "synthetic",
    ):
        if mode != "synthetic" and (connector is not None or effects is not None):
            raise ValueError("Replay/shadow cannot acquire provider handles")
        self.store, self.policy, self.clock = store, policy or Deny(), clock
        self.connector = connector
        self.effects = effects
        self.mode = mode

    def tick(self, identifier: str) -> Run:
        now = self.clock()
        claim = self.store.claim(identifier, now)
        if claim is None:
            return self.store.load(identifier)
        run, fence = claim
        workflow = self.store.definition(run.definition_digest)
        step = next(item for item in workflow.steps if item.id == run.current)
        if run.executions >= workflow.max_steps or now >= run.started_at + timedelta(
            seconds=workflow.max_duration_seconds
        ):
            changed = run.model_copy(update={"status": "failed", "revision": run.revision + 1})
        elif step.kind == "terminate":
            changed = run.model_copy(update={"status": step.terminal, "revision": run.revision + 1})
        elif step.kind in ("wait", "human_approval"):
            if run.due_at is None:
                changed = run.model_copy(
                    update={
                        "status": "waiting" if step.kind == "wait" else "human_wait",
                        "due_at": now
                        + timedelta(
                            seconds=(
                                step.wait_seconds if step.kind == "wait" else step.timeout_seconds
                            )
                        ),
                        "revision": run.revision + 1,
                    }
                )
            else:
                changed = route(workflow, run, "success" if step.kind == "wait" else "timeout", now)
        elif step.kind == "trigger":
            changed = route(workflow, run, "success", now)
        elif step.kind == "policy":
            changed = route(
                workflow, run, "allow" if self.policy.allows(run, workflow, step) else "deny", now
            )
        elif step.kind == "branch":
            changed = route(workflow, run, "true" if inputs(run, step)[0].value else "false", now)
        else:
            values: tuple[Value, ...] = ()
            error, retryable = "unavailable", True
            if step.kind in ("ai", "tool") and self.mode != "synthetic":
                error, retryable = "mode_denied", False
            elif step.kind == "deterministic":
                try:
                    values = deterministic(step, inputs(run, step))
                except ToolError as failure:
                    error, retryable = failure.code, False
            elif step.kind == "tool" and step.effect != "READ_ONLY" and self.effects is not None:
                try:
                    values = self.effects.execute(run, step, inputs(run, step), fence)
                except ToolError as failure:
                    error, retryable = failure.code, False
            elif step.kind == "tool" and self.connector is not None:
                try:
                    values = self.connector.execute(run, step, inputs(run, step))
                except ToolError as failure:
                    error, retryable = failure.code, failure.retryable
            if values:
                changed = route(workflow, run, "success", now, values)
            elif retryable and run.attempts + 1 < step.retry.attempts:
                changed = run.model_copy(
                    update={
                        "status": "waiting",
                        "attempts": run.attempts + 1,
                        "executions": run.executions + 1,
                        "revision": run.revision + 1,
                        "due_at": now
                        + timedelta(seconds=min(300, step.retry.backoff_seconds * 2**run.attempts)),
                        "progress": (
                            *run.progress,
                            Progress(
                                step=step.id,
                                attempt=run.attempts + 1,
                                outcome=error,
                                at=now,
                            ),
                        ),
                        "failure_code": error,
                    }
                )
            else:
                changed = route(workflow, run, "error", now).model_copy(
                    update={"failure_code": error}
                )
        finished = self.clock()
        if finished >= now + timedelta(seconds=step.timeout_seconds):
            # Pure computation can be repeated after lease expiry, never committed late.
            return self.store.load(identifier)
        return self.store.finish(run, fence, changed, finished)
