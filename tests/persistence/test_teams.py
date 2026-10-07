"""Two fabricated organizations, pre-issued fake sessions, no network identity provider."""

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import SecretStr
from sqlalchemy import select, text, update

from actual.core.primitives import ActorId, WorkspaceId, content_digest
from actual.workflows.activation import audit as activation_audit
from actual.workflows.activation import migrate as migrate_activation
from actual.workflows.approval import BusinessIntent, provider
from actual.workflows.approval import audit as effect_audit
from actual.workflows.approval import migrate as migrate_approval
from actual.workflows.connectors import ToolError
from actual.workflows.examples import effect_workflow, text_workflow
from actual.workflows.state import Value
from actual.workflows.storage import Conflict, Store, runs, version
from actual.workflows.storage import migrate as migrate_runtime
from actual.workflows.teams import (
    ConnectorReference,
    Directory,
    Member,
    Organization,
    Teams,
    Workspace,
    migrate,
    sessions,
)
from actual.worklab.replay import Case
from actual.worklab.shadow import Transition, compare

NOW = datetime(2026, 10, 7, tzinfo=UTC)
OWNER = WorkspaceId("workspace_" + "1" * 32)
OTHER = WorkspaceId("workspace_" + "2" * 32)
ADMIN, OPERATOR, REVIEWER, VIEWER, FOREIGN = (ActorId("actor_" + str(i) * 32) for i in range(1, 6))
TOKENS = {
    actor.root: SecretStr("synthetic_session_" + str(i) * 64)
    for i, actor in enumerate((ADMIN, OPERATOR, REVIEWER, VIEWER, FOREIGN), start=1)
}
BUSINESS = BusinessIntent(business_object="fabricated_message", submission="first_explicit")


def setup(engine):
    for migration in (migrate_runtime, migrate_approval, migrate_activation, migrate):
        migration(engine)
    directory = Directory(engine)
    organization = Organization(
        id="synthetic_org", capabilities=("fake_write",), administrators=(ADMIN,)
    )
    connectors = (
        ConnectorReference(id="fake_inbox", capability="fake_write", resource="synthetic_inbox"),
    )
    workspace = Workspace(
        id=OWNER,
        organization=organization.id,
        members=(
            Member(principal=ADMIN, role="admin"),
            Member(principal=OPERATOR, role="operator"),
            Member(principal=REVIEWER, role="reviewer"),
            Member(principal=VIEWER, role="viewer"),
        ),
        connectors=connectors,
    )
    directory.provision(organization, workspace)
    directory.provision(
        Organization(id="other_org", capabilities=("fake_write",), administrators=(FOREIGN,)),
        Workspace(
            id=OTHER,
            organization="other_org",
            members=(Member(principal=FOREIGN, role="admin"),),
            connectors=connectors,
        ),
    )
    for actor in (ADMIN, OPERATOR, REVIEWER, VIEWER, FOREIGN):
        directory.issue(TOKENS[actor.root], actor, NOW + timedelta(hours=1))
    return Teams(directory, clock=lambda: NOW), directory, organization, workspace


def waiting(teams, owner=OWNER, actor=OPERATOR, administrator=ADMIN):
    workflow = effect_workflow()
    token = TOKENS[actor.root]
    teams.publish(token, owner, workflow)
    observation = compare(
        Case(id="synthetic_shadow", workflow=workflow, observed_policy="allow"),
        (Transition(step="start", outcome="success"), Transition(step="policy", outcome="allow")),
    )
    teams.activate(
        TOKENS[administrator.root],
        owner,
        workflow.digest,
        "send",
        actor,
        observation,
        content_digest(observation.model_dump(mode="json")),
        0,
    )
    run = teams.start(token, owner, workflow.digest, "same_event", ())
    for _ in range(3):
        run = teams.tick(token, owner, run.id)
    assert run.status == "human_wait"
    return run


def approved(teams):
    run = waiting(teams)
    preview = teams.preview(TOKENS[REVIEWER.root], OWNER, run.id, BUSINESS)
    approval = teams.approve(TOKENS[REVIEWER.root], OWNER, preview, preview.digest)
    return teams.load(TOKENS[OPERATOR.root], OWNER, run.id), approval


def test_shared_review_binds_execution_principal_and_preserves_actual_audit_actors(pg_engine):
    teams, directory, organization, workspace = setup(pg_engine)
    run, approval = approved(teams)
    assert approval.approver == REVIEWER and approval.binding.principal_id == OPERATOR
    assert teams.tick(TOKENS[OPERATOR.root], OWNER, run.id).current == "done"
    assert teams.tick(TOKENS[OPERATOR.root], OWNER, run.id).status == "succeeded"
    assert (
        teams.start(TOKENS[OPERATOR.root], OWNER, effect_workflow().digest, "same_event", ()).id
        == run.id
    )
    with pg_engine.connect() as connection:
        assert len(connection.execute(select(provider)).all()) == 1
        assert connection.execute(select(activation_audit.c.actor)).scalar_one() == ADMIN.root
        assert (REVIEWER.root, "approved") in connection.execute(
            select(effect_audit.c.actor, effect_audit.c.state)
        ).all()
        assert (OPERATOR.root, "dispatching") in connection.execute(
            select(effect_audit.c.actor, effect_audit.c.state)
        ).all()
        assert TOKENS[OPERATOR.root].get_secret_value() not in str(
            connection.execute(select(sessions)).all()
        )


def test_cross_tenant_unknown_session_role_escalation_and_cross_object_access_deny(pg_engine):
    teams, directory, organization, workspace = setup(pg_engine)
    run = waiting(teams)
    for token, owner in (
        (TOKENS[FOREIGN.root], OWNER),
        (TOKENS[OPERATOR.root], OTHER),
        (SecretStr("synthetic_session_" + "f" * 64), OWNER),
    ):
        with pytest.raises(ToolError, match="denied"):
            teams.load(token, owner, run.id)
    with pytest.raises(ToolError, match="denied"):
        teams.load(TOKENS[FOREIGN.root], OTHER, run.id)
    assert teams.load(TOKENS[VIEWER.root], OWNER, run.id).id == run.id
    with pytest.raises(ToolError, match="denied"):
        teams.start(TOKENS[VIEWER.root], OWNER, effect_workflow().digest, "forged", ())
    changed = workspace.model_copy(
        update={
            "revision": 2,
            "members": tuple(
                m.model_copy(update={"role": "admin"}) if m.principal == VIEWER else m
                for m in workspace.members
            ),
        }
    )
    with pytest.raises(ToolError, match="denied"):
        teams.update_workspace(TOKENS[VIEWER.root], changed, 1)
    with pytest.raises(ToolError, match="denied"):
        teams.preview(TOKENS[OPERATOR.root], OWNER, run.id, BUSINESS)
    teams.clock = lambda: NOW + timedelta(hours=2)
    with pytest.raises(ToolError, match="denied"):
        teams.load(TOKENS[OPERATOR.root], OWNER, run.id)


@pytest.mark.parametrize("revocation", ["session", "reviewer", "connector", "organization"])
def test_authority_is_rechecked_after_reservation_before_dispatch(pg_engine, revocation):
    teams, directory, organization, workspace = setup(pg_engine)
    run, approval = approved(teams)
    token = TOKENS[OPERATOR.root]
    context = teams.context(token, OWNER, ("operator",))
    runtime, _ = teams._composition(token, context, OPERATOR)

    def revoke():
        if revocation == "session":
            directory.revoke(token)
        elif revocation == "organization":
            teams.update_policy(
                TOKENS[ADMIN.root],
                OWNER,
                organization.model_copy(update={"revision": 2, "capabilities": ()}),
                1,
            )
        else:
            changed = workspace.model_copy(
                update={
                    "revision": 2,
                    **(
                        {"connectors": ()}
                        if revocation == "connector"
                        else {
                            "members": tuple(
                                m.model_copy(update={"active": False})
                                if m.principal == REVIEWER
                                else m
                                for m in workspace.members
                            )
                        }
                    ),
                }
            )
            teams.update_workspace(TOKENS[ADMIN.root], changed, 1)

    runtime.effects.before_dispatch = revoke
    assert runtime.tick(run.id).failure_code == "denied"
    with pg_engine.connect() as connection:
        assert connection.execute(select(provider)).all() == []


def test_execution_principal_cannot_change_on_duplicate_or_stored_payload(pg_engine):
    teams, directory, organization, workspace = setup(pg_engine)
    workflow = text_workflow()
    teams.publish(TOKENS[OPERATOR.root], OWNER, workflow)
    run = teams.start(
        TOKENS[OPERATOR.root],
        OWNER,
        workflow.digest,
        "same",
        (Value(name="text", value="Fabricated"),),
    )
    with pytest.raises(Conflict, match="principal changed"):
        teams.start(TOKENS[ADMIN.root], OWNER, workflow.digest, "same", run.trigger)
    with pytest.raises(ToolError, match="denied"):
        teams.tick(TOKENS[ADMIN.root], OWNER, run.id)
    payload = run.model_copy(update={"initiator": ADMIN}).model_dump(mode="json")
    with pg_engine.begin() as connection:
        connection.execute(update(runs).values(payload=payload))
    with pytest.raises(Conflict, match="identity"):
        teams.load(TOKENS[OPERATOR.root], OWNER, run.id)


def test_legacy_workflow_migration_preserves_unassigned_runs_and_denies_team_intake(pg_engine):
    teams, directory, organization, workspace = setup(pg_engine)
    workflow = text_workflow()
    teams.publish(TOKENS[OPERATOR.root], OWNER, workflow)
    repo = Store(pg_engine, OWNER)
    run = repo.start(workflow, "old", (Value(name="text", value="Fabricated"),), NOW)
    with pg_engine.begin() as connection:
        connection.execute(text("ALTER TABLE actual_workflow_runs DROP COLUMN initiator"))
        connection.execute(update(version).values(version=2))
    migrate_runtime(pg_engine)
    assert repo.load(run.id) == run
    with pytest.raises(ToolError, match="denied"):
        teams.load(TOKENS[OPERATOR.root], OWNER, run.id)
