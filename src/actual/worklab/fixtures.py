"""Public shared-development observations only; no expected answers or future outcomes."""

from datetime import UTC, datetime, timedelta

from actual.core.primitives import ActorId, WorkspaceId
from actual.workflows.examples import effect_workflow, text_workflow
from actual.workflows.ir import Binding, Edge, Step, Workflow, slot
from actual.workflows.state import Value

from .replay import Case
from .teach import Activity, Event


def branch_workflow() -> Workflow:
    return Workflow(
        id="synthetic_branch",
        version=1,
        trigger_schema=(slot("text", "text"),),
        steps=(
            Step(id="start", kind="trigger"),
            Step(
                id="predicate",
                kind="deterministic",
                capability="is_nonempty",
                inputs=(Binding(name="text", source="trigger", field="text"),),
            ),
            Step(
                id="branch",
                kind="branch",
                inputs=(Binding(name="value", source="output", step="predicate", field="value"),),
            ),
            Step(id="done", kind="terminate"),
            Step(id="failed", kind="terminate", terminal="failed"),
        ),
        edges=(
            Edge(source="start", outcome="success", target="predicate"),
            Edge(source="predicate", outcome="success", target="branch"),
            Edge(source="predicate", outcome="error", target="failed"),
            Edge(source="branch", outcome="true", target="done"),
            Edge(source="branch", outcome="false", target="failed"),
        ),
    )


def observations() -> tuple[Case, ...]:
    return (
        Case(
            id="work_dev_copy",
            workflow=text_workflow(),
            trigger=(Value(name="text", value="Fabricated"),),
        ),
        Case(
            id="work_dev_nonempty",
            workflow=branch_workflow(),
            trigger=(Value(name="text", value="Fabricated"),),
        ),
        Case(
            id="work_dev_empty", workflow=branch_workflow(), trigger=(Value(name="text", value=""),)
        ),
        Case(id="work_dev_permission", workflow=effect_workflow(), observed_policy="deny"),
        Case(id="work_dev_review", workflow=effect_workflow(), observed_policy="allow"),
    )


def process_observations() -> tuple[Event, ...]:
    base: tuple[Activity, ...] = (
        "job_open",
        "company_research",
        "cv_compare",
        "application_prepare",
        "tracker_update",
    )
    variant: tuple[Activity, ...] = (
        "job_open",
        "cv_compare",
        "cv_compare",
        "application_prepare",
        "tracker_update",
    )
    result = []
    for name, activities, seconds in (
        ("session_a", base, (0, 10, 20, 30, 40)),
        ("session_b", base, (0, 10, 20, 30, 40)),
        ("session_c", variant, (0, 10, 20, 40, 50)),
    ):
        for index, (activity, offset) in enumerate(zip(activities, seconds, strict=True)):
            at = datetime(2026, 10, 7, tzinfo=UTC) + timedelta(seconds=offset)
            result.append(
                Event(
                    workspace_id=WorkspaceId("workspace_" + "0" * 32),
                    actor_id=ActorId("actor_" + "0" * 32),
                    session=name,
                    source_event=f"event_{index}",
                    application="synthetic_career",
                    activity=activity,
                    business_object="fabricated_job",
                    occurred_at=at,
                    recorded_at=at + timedelta(seconds=1),
                )
            )
    return tuple(result)
