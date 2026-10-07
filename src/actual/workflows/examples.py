"""Fabricated graphs for contract/runtime checks, never personal workflow capture."""

from .ir import Binding, Edge, Step, Workflow, slot


def text_workflow() -> Workflow:
    return Workflow(
        id="synthetic_text",
        version=1,
        trigger_schema=(slot("text", "text"),),
        steps=(
            Step(id="start", kind="trigger"),
            Step(
                id="copy",
                kind="deterministic",
                capability="copy_text",
                inputs=(Binding(name="text", source="trigger", field="text"),),
            ),
            Step(id="done", kind="terminate"),
            Step(id="failed", kind="terminate", terminal="failed"),
        ),
        edges=(
            Edge(source="start", outcome="success", target="copy"),
            Edge(source="copy", outcome="success", target="done"),
            Edge(source="copy", outcome="error", target="failed"),
        ),
    )


def effect_workflow() -> Workflow:
    return Workflow(
        id="synthetic_effect",
        version=1,
        steps=(
            Step(id="start", kind="trigger"),
            Step(id="policy", kind="policy", protects="send"),
            Step(id="review", kind="human_approval", protects="send"),
            Step(
                id="send",
                kind="tool",
                capability="fake_write",
                effect="EXTERNAL_WRITE",
                permissions=("fake_write",),
                idempotency="provider_key",
                human_review=True,
                inputs=(
                    Binding(name="destination", source="literal", value="synthetic_inbox"),
                    Binding(name="text", source="literal", value="Fabricated message"),
                ),
            ),
            Step(id="done", kind="terminate"),
            Step(id="failed", kind="terminate", terminal="failed"),
        ),
        edges=(
            Edge(source="start", outcome="success", target="policy"),
            Edge(source="policy", outcome="allow", target="review"),
            Edge(source="policy", outcome="deny", target="failed"),
            Edge(source="review", outcome="approved", target="send"),
            Edge(source="review", outcome="denied", target="failed"),
            Edge(source="review", outcome="timeout", target="failed"),
            Edge(source="send", outcome="success", target="done"),
            Edge(source="send", outcome="error", target="failed"),
        ),
    )


def read_workflow() -> Workflow:
    return Workflow(
        id="synthetic_read",
        version=1,
        trigger_schema=(slot("resource", "text"),),
        steps=(
            Step(id="start", kind="trigger"),
            Step(
                id="read",
                kind="tool",
                capability="fake_read",
                permissions=("fake_read",),
                inputs=(Binding(name="resource", source="trigger", field="resource"),),
            ),
            Step(id="done", kind="terminate"),
            Step(id="failed", kind="terminate", terminal="failed"),
        ),
        edges=(
            Edge(source="start", outcome="success", target="read"),
            Edge(source="read", outcome="success", target="done"),
            Edge(source="read", outcome="error", target="failed"),
        ),
    )
