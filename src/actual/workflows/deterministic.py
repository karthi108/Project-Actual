"""Fixed pure handlers; source fields remain unverified observations."""

from typing import Annotated, Literal

from pydantic import Field, ValidationError

from actual.core.primitives import Contract, Instant

from .connectors import ToolError
from .ir import Name, Step
from .state import Value


class Action(Contract):
    task: Name
    assignee: Name | None = None
    deadline: Instant | None = None


class Meeting(Contract):
    title: Name
    actions: Annotated[tuple[Action, ...], Field(max_length=8)]
    classification: Literal["synthetic"] = "synthetic"


def execute(step: Step, values: tuple[Value, ...]) -> tuple[Value, ...]:
    if len(values) != 1 or values[0].name != "text" or not isinstance(values[0].value, str):
        raise ToolError("invalid_output")
    supplied = values[0].value
    if step.capability == "copy_text":
        return (Value(name="text", value=supplied),)
    if step.capability == "is_nonempty":
        return (Value(name="value", value=bool(supplied.strip())),)
    if step.capability == "triage_subject":
        routine = supplied.casefold().startswith("fyi:")
        return (
            Value(name="category", value="routine" if routine else "human_review"),
            Value(name="needs_review", value=not routine),
        )
    if step.capability == "extract_meeting_actions":
        try:
            meeting = Meeting.model_validate_json(supplied)
            # Preserves explicit task/assignee/deadline, including unknown values.
            return (
                Value(name="actions", value=meeting.model_dump_json()),
                Value(name="count", value=len(meeting.actions)),
            )
        except (ValidationError, ValueError):
            raise ToolError("invalid_output") from None
    raise ToolError("denied")
