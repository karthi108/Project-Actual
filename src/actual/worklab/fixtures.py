"""Public shared-development observations only; no expected answers or future outcomes."""

from actual.workflows.examples import effect_workflow, text_workflow
from actual.workflows.ir import Binding, Edge, Step, Workflow, slot
from actual.workflows.state import Value

from .replay import Case


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
