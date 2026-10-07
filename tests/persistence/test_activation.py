from datetime import UTC, datetime

import pytest

from actual.core.primitives import ActorId, WorkspaceId, content_digest
from actual.workflows.activation import controlled, migrate
from actual.workflows.approval import BusinessIntent
from actual.workflows.approval import migrate as migrate_approval
from actual.workflows.connectors import ToolError
from actual.workflows.examples import effect_workflow
from actual.workflows.storage import Conflict, Store
from actual.workflows.storage import migrate as migrate_runtime
from actual.worklab.fixtures import observations
from actual.worklab.shadow import Transition, compare

OWNER = WorkspaceId("workspace_" + "1" * 32)
ACTOR = ActorId("actor_" + "1" * 32)
NOW = datetime(2026, 10, 7, tzinfo=UTC)


def setup(engine):
    migrate_runtime(engine)
    migrate_approval(engine)
    migrate(engine)
    return controlled(engine, OWNER, ACTOR, frozenset(("fake_write",)), clock=lambda: NOW)


def test_activation_is_exact_reviewed_step_and_does_not_replace_action_approval(pg_engine):
    app = setup(pg_engine)
    repo = Store(pg_engine, OWNER)
    workflow = effect_workflow()
    blocked = repo.start(workflow, "disabled", (), NOW)
    app.runtime.tick(blocked.id)
    assert app.runtime.tick(blocked.id).current == "failed"
    evidence = compare(
        observations()[-1],
        (Transition(step="start", outcome="success"), Transition(step="policy", outcome="allow")),
    )
    digest = content_digest(evidence.model_dump(mode="json"))
    app.activations.set(workflow, "send", "enabled", evidence, digest, 0, NOW)
    with pytest.raises(Conflict):
        app.activations.set(workflow, "send", "disabled", evidence, digest, 0, NOW)
    run = repo.start(workflow, "activated", (), NOW)
    for _ in range(3):
        app.runtime.tick(run.id)
    assert repo.load(run.id).status == "human_wait"
    preview = app.approvals.preview(
        run.id, BusinessIntent(business_object="fake_message", submission="explicit_first"), NOW
    )
    app.approvals.approve(preview, preview.digest, NOW)
    app.activations.set(workflow, "send", "disabled", evidence, digest, 1, NOW)
    assert app.runtime.tick(run.id).failure_code == "denied"
    upgrade = workflow.model_copy(update={"version": 2})
    upgraded = repo.start(upgrade, "upgraded", (), NOW)
    app.runtime.tick(upgraded.id)
    assert app.runtime.tick(upgraded.id).current == "failed"


def test_no_permission_or_changed_evidence_cannot_activate(pg_engine):
    app = setup(pg_engine)
    workflow = effect_workflow()
    evidence = compare(observations()[-1], ())
    digest = content_digest(evidence.model_dump(mode="json"))
    with pytest.raises(Conflict):
        app.activations.set(workflow, "send", "enabled", evidence, "a" * 64, 0, NOW)
    app.permission.revoked = True
    with pytest.raises(ToolError, match="denied"):
        app.activations.set(workflow, "send", "enabled", evidence, digest, 0, NOW)
