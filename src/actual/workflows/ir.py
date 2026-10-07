"""Closed declarative graphs. Registration describes effects; it grants no authority."""

from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from actual.core.primitives import Contract, content_digest
from actual.core.workflow import EffectKind

type Name = Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]{0,47}$", strict=True)]
type Scalar = Annotated[str, Field(max_length=4096)] | bool | int
type ValueType = Literal["text", "boolean", "integer"]
type Kind = Literal[
    "trigger",
    "deterministic",
    "ai",
    "tool",
    "policy",
    "human_approval",
    "branch",
    "wait",
    "terminate",
]


class Slot(Contract):
    name: Name
    type: ValueType


class Capability(Contract):
    name: Name
    kind: Literal["deterministic", "ai", "tool"]
    inputs: tuple[Slot, ...]
    outputs: tuple[Slot, ...]
    effect: EffectKind
    permissions: tuple[Name, ...] = ()
    idempotency: Literal["pure", "provider_key", "reconcile"]
    human_review: bool = False


def slot(name: str, type_: ValueType) -> Slot:
    return Slot(name=name, type=type_)


CAPABILITIES = (
    Capability(
        name="copy_text",
        kind="deterministic",
        inputs=(slot("text", "text"),),
        outputs=(slot("text", "text"),),
        effect="READ_ONLY",
        idempotency="pure",
    ),
    Capability(
        name="is_nonempty",
        kind="deterministic",
        inputs=(slot("text", "text"),),
        outputs=(slot("value", "boolean"),),
        effect="READ_ONLY",
        idempotency="pure",
    ),
    Capability(
        name="propose_text",
        kind="ai",
        inputs=(slot("text", "text"),),
        outputs=(slot("text", "text"),),
        effect="READ_ONLY",
        permissions=("local_model",),
        idempotency="pure",
        human_review=True,
    ),
    Capability(
        name="fake_read",
        kind="tool",
        inputs=(slot("resource", "text"),),
        outputs=(slot("text", "text"),),
        effect="READ_ONLY",
        permissions=("fake_read",),
        idempotency="pure",
    ),
    Capability(
        name="fake_write",
        kind="tool",
        inputs=(slot("destination", "text"), slot("text", "text")),
        outputs=(slot("receipt", "text"),),
        effect="EXTERNAL_WRITE",
        permissions=("fake_write",),
        idempotency="provider_key",
        human_review=True,
    ),
)


def capability(name: str) -> Capability:
    for item in CAPABILITIES:
        if item.name == name:
            return item
    raise ValueError("Unregistered capability")


def value_type(value: Scalar) -> ValueType:
    if type(value) is bool:
        return "boolean"
    if type(value) is int:
        return "integer"
    return "text"


class Binding(Contract):
    name: Name
    source: Literal["literal", "trigger", "output"]
    value: Scalar | None = None
    step: Name | None = None
    field: Name | None = None

    @model_validator(mode="after")
    def shape(self) -> Self:
        if self.source == "literal":
            if self.value is None or self.step is not None or self.field is not None:
                raise ValueError("Literal requires only a bounded scalar")
        elif self.value is not None or self.field is None:
            raise ValueError("Reference requires field and no literal")
        elif (self.source == "output") != (self.step is not None):
            raise ValueError("Only output references identify a step")
        return self


class Retry(Contract):
    attempts: Annotated[int, Field(ge=1, le=5)] = 1
    backoff_seconds: Annotated[int, Field(ge=1, le=300)] = 1


class Step(Contract):
    id: Name
    kind: Kind
    capability: Name | None = None
    inputs: Annotated[tuple[Binding, ...], Field(max_length=8)] = ()
    effect: EffectKind = "READ_ONLY"
    permissions: Annotated[tuple[Name, ...], Field(max_length=8)] = ()
    human_review: bool = False
    idempotency: Literal["pure", "provider_key", "reconcile"] = "pure"
    timeout_seconds: Annotated[int, Field(ge=1, le=300)] = 30
    retry: Retry = Retry()
    failure: Literal["route_error"] = "route_error"
    classification: Literal["synthetic"] = "synthetic"
    # Gates name the exact consequential step they guard; no blanket workflow approval.
    protects: Name | None = None
    wait_seconds: Annotated[int, Field(ge=1, le=86400)] = 1
    terminal: Literal["succeeded", "failed", "cancelled"] = "succeeded"

    @model_validator(mode="after")
    def registered(self) -> Self:
        if self.kind in ("deterministic", "ai", "tool"):
            registered = capability(self.capability or "")
            if (self.kind, self.effect, self.permissions, self.idempotency, self.human_review) != (
                registered.kind,
                registered.effect,
                registered.permissions,
                registered.idempotency,
                registered.human_review,
            ):
                raise ValueError("Capability metadata cannot be weakened")
            expected = {item.name for item in registered.inputs}
        else:
            if self.capability is not None or self.effect != "READ_ONLY" or self.permissions:
                raise ValueError("Control steps cannot declare executable effects")
            if self.idempotency != "pure" or self.human_review:
                raise ValueError("Control metadata is fixed")
            expected = {"value"} if self.kind == "branch" else set()
        if {item.name for item in self.inputs} != expected or len(self.inputs) != len(expected):
            raise ValueError("Input schema mismatch or duplicate binding")
        if (self.kind in ("policy", "human_approval")) != (self.protects is not None):
            raise ValueError("Gates must identify their exact action step")
        if self.effect != "READ_ONLY" and self.retry.attempts != 1:
            raise ValueError("Effect retries require the later intent recovery boundary")
        return self


def outcomes(step: Step) -> tuple[str, ...]:
    if step.kind == "terminate":
        return ()
    if step.kind == "branch":
        return ("true", "false")
    if step.kind == "policy":
        return ("allow", "deny")
    if step.kind == "human_approval":
        return ("approved", "denied", "timeout")
    if step.kind == "wait":
        return ("success",)
    if step.kind == "trigger":
        return ("success",)
    return ("success", "error")


class Edge(Contract):
    source: Name
    outcome: Literal[
        "success", "error", "true", "false", "allow", "deny", "approved", "denied", "timeout"
    ]
    target: Name


class Workflow(Contract):
    ir_version: Literal["actual-workflow-v1"] = "actual-workflow-v1"
    id: Name
    version: Annotated[int, Field(ge=1, le=1_000_000)]
    classification: Literal["synthetic"] = "synthetic"
    trigger_schema: Annotated[tuple[Slot, ...], Field(max_length=8)] = ()
    steps: Annotated[tuple[Step, ...], Field(min_length=2, max_length=64)]
    edges: Annotated[tuple[Edge, ...], Field(min_length=1, max_length=192)]
    max_steps: Annotated[int, Field(ge=2, le=320)] = 64
    max_model_calls: Annotated[int, Field(ge=0, le=16)] = 0
    max_duration_seconds: Annotated[int, Field(ge=1, le=86400)] = 900

    @property
    def digest(self) -> str:
        return content_digest(self.model_dump(mode="json"))

    @model_validator(mode="after")
    def graph(self) -> Self:
        if len({item.name for item in self.trigger_schema}) != len(self.trigger_schema):
            raise ValueError("Duplicate trigger schema field")
        steps = {item.id: item for item in self.steps}
        triggers = [item.id for item in self.steps if item.kind == "trigger"]
        if len(steps) != len(self.steps) or len(triggers) != 1:
            raise ValueError("Unique steps and exactly one trigger required")
        if len({slot.name for slot in self.trigger_schema}) != len(self.trigger_schema):
            raise ValueError("Duplicate trigger fields")
        incoming: dict[str, list[Edge]] = {name: [] for name in steps}
        outgoing: dict[str, list[Edge]] = {name: [] for name in steps}
        for edge in self.edges:
            if edge.source not in steps or edge.target not in steps:
                raise ValueError("Missing edge endpoint")
            incoming[edge.target].append(edge)
            outgoing[edge.source].append(edge)
        if incoming[triggers[0]]:
            raise ValueError("Trigger cannot have incoming edges")
        for name, step in steps.items():
            actual = [edge.outcome for edge in outgoing[name]]
            if sorted(actual) != sorted(outcomes(step)):
                raise ValueError("Every allowed outcome needs exactly one route")
            if step.protects is not None and (
                step.protects not in steps or steps[step.protects].effect == "READ_ONLY"
            ):
                raise ValueError("Gate protects a registered consequential action")
        order: list[str] = []
        pending = set(steps)
        while pending:
            ready = sorted(
                name for name in pending if all(e.source in order for e in incoming[name])
            )
            if not ready:
                raise ValueError("Cycles are forbidden; bounded loops are not implemented")
            order.extend(ready)
            pending.difference_update(ready)
        dominators: dict[str, set[str]] = {}
        facts: dict[str, set[tuple[str, str]]] = {}
        for name in order:
            if name == triggers[0]:
                dominators[name], facts[name] = {name}, set()
            else:
                if not incoming[name]:
                    raise ValueError("Unreachable step")
                paths: list[set[tuple[str, str]]] = []
                for edge in incoming[name]:
                    path = facts[edge.source].copy()
                    parent = steps[edge.source]
                    if (parent.kind, edge.outcome) in (
                        ("policy", "allow"),
                        ("human_approval", "approved"),
                    ):
                        path.add((parent.kind, parent.protects or ""))
                    paths.append(path)
                facts[name] = set.intersection(*paths)
                dominators[name] = {name} | set.intersection(
                    *(dominators[edge.source] for edge in incoming[name])
                )
            step = steps[name]
            if (
                step.effect != "READ_ONLY"
                and not {("policy", name), ("human_approval", name)} <= facts[name]
            ):
                raise ValueError(
                    "Every action path requires its successful policy and approval gates"
                )
            expected_types = (
                {item.name: item.type for item in capability(step.capability or "").inputs}
                if step.capability
                else {"value": "boolean"}
            )
            for binding in step.inputs:
                actual_type: ValueType | None
                if binding.source == "literal":
                    assert binding.value is not None
                    actual_type = value_type(binding.value)
                elif binding.source == "trigger":
                    actual_type = next(
                        (s.type for s in self.trigger_schema if s.name == binding.field), None
                    )
                else:
                    source = steps.get(binding.step or "")
                    if source is None or source.id == name or source.id not in dominators[name]:
                        raise ValueError("Output reference must dominate its consumer")
                    if not source.capability:
                        raise ValueError("Control step has no output schema")
                    # Error paths do not provide outputs, even when their node dominates.
                    if any(
                        e.outcome == "error" and name in _reachable(e.target, outgoing)
                        for e in outgoing[source.id]
                    ):
                        raise ValueError("Reference may be absent on an error path")
                    actual_type = next(
                        (
                            s.type
                            for s in capability(source.capability).outputs
                            if s.name == binding.field
                        ),
                        None,
                    )
                if actual_type != expected_types[binding.name]:
                    raise ValueError("Binding type mismatch or missing field")
        if sum(step.retry.attempts for step in self.steps) > self.max_steps:
            raise ValueError("Step budget exceeded")
        if (
            sum(step.retry.attempts for step in self.steps if step.kind == "ai")
            > self.max_model_calls
        ):
            raise ValueError("Model budget exceeded")
        if (
            sum(
                step.wait_seconds
                if step.kind == "wait"
                else step.timeout_seconds * step.retry.attempts
                + step.retry.backoff_seconds * (2 ** (step.retry.attempts - 1) - 1)
                for step in self.steps
            )
            > self.max_duration_seconds
        ):
            raise ValueError("Duration budget exceeded")
        return self


def _reachable(start: str, outgoing: dict[str, list[Edge]]) -> set[str]:
    found: set[str] = set()
    pending = [start]
    while pending:
        name = pending.pop()
        if name not in found:
            found.add(name)
            pending.extend(edge.target for edge in outgoing[name])
    return found
