"""Two deliberately small synthetic families on the existing typed engine."""

from .deterministic import Action, Meeting
from .ir import Binding, Edge, Step, Workflow, slot
from .state import Value


def meeting_workflow() -> Workflow:
    return Workflow(
        id="synthetic_meeting",
        version=1,
        trigger_schema=(slot("text", "text"),),
        steps=(
            Step(id="start", kind="trigger"),
            Step(
                id="extract",
                kind="deterministic",
                capability="extract_meeting_actions",
                inputs=(Binding(name="text", source="trigger", field="text"),),
            ),
            Step(id="done", kind="terminate"),
            Step(id="failed", kind="terminate", terminal="failed"),
        ),
        edges=(
            Edge(source="start", outcome="success", target="extract"),
            Edge(source="extract", outcome="success", target="done"),
            Edge(source="extract", outcome="error", target="failed"),
        ),
    )


def email_workflow() -> Workflow:
    return Workflow(
        id="synthetic_email_triage",
        version=1,
        trigger_schema=(slot("text", "text"),),
        steps=(
            Step(id="start", kind="trigger"),
            Step(
                id="triage",
                kind="deterministic",
                capability="triage_subject",
                inputs=(Binding(name="text", source="trigger", field="text"),),
            ),
            Step(
                id="branch",
                kind="branch",
                inputs=(
                    Binding(name="value", source="output", step="triage", field="needs_review"),
                ),
            ),
            Step(id="human_review", kind="terminate"),
            Step(id="routine", kind="terminate"),
            Step(id="failed", kind="terminate", terminal="failed"),
        ),
        edges=(
            Edge(source="start", outcome="success", target="triage"),
            Edge(source="triage", outcome="success", target="branch"),
            Edge(source="triage", outcome="error", target="failed"),
            Edge(source="branch", outcome="true", target="human_review"),
            Edge(source="branch", outcome="false", target="routine"),
        ),
    )


def meeting_input() -> tuple[Value, ...]:
    return (
        Value(
            name="text",
            value=Meeting(
                title="fabricated_planning",
                actions=(
                    Action(task="review_synthetic_note", assignee="fictional_owner"),
                    Action(task="ask_for_missing_date"),
                ),
            ).model_dump_json(),
        ),
    )
