from datetime import UTC, datetime, timedelta

import pytest
from pydantic import SecretStr
from sqlalchemy import select

from actual.core.primitives import ActorId, WorkspaceId
from actual.workflows.audit_export import export
from actual.workflows.connectors import ToolError
from actual.workflows.examples import text_workflow
from actual.workflows.state import Value
from actual.workflows.storage import Conflict
from actual.workflows.teams import Directory, Member, Organization, Teams, Workspace, audit

NOW = datetime(2026, 10, 7, tzinfo=UTC)
OWNER = WorkspaceId("workspace_" + "1" * 32)
OTHER = WorkspaceId("workspace_" + "2" * 32)
ADMIN = ActorId("actor_" + "1" * 32)
VIEWER = ActorId("actor_" + "2" * 32)
TOKEN = SecretStr("synthetic_session_" + "1" * 64)
VIEWER_TOKEN = SecretStr("synthetic_session_" + "2" * 64)


def setup(engine, monkeypatch):
    from actual.deployment import __main__ as deployment

    monkeypatch.setattr(deployment, "database_url", lambda: "Synthetic stub")
    monkeypatch.setattr(deployment, "create_database_engine", lambda _: engine)
    deployment.run("migrate")
    directory = Directory(engine)
    directory.provision(
        Organization(id="synthetic_org"),
        Workspace(
            id=OWNER,
            organization="synthetic_org",
            members=(
                Member(principal=ADMIN, role="admin"),
                Member(principal=VIEWER, role="viewer"),
            ),
        ),
    )
    directory.issue(TOKEN, ADMIN, NOW + timedelta(hours=1))
    directory.issue(VIEWER_TOKEN, VIEWER, NOW + timedelta(hours=1))
    return Teams(directory, clock=lambda: NOW)


def test_audit_export_is_scoped_complete_content_free_and_grants_nothing(pg_engine, monkeypatch):
    teams = setup(pg_engine, monkeypatch)
    workflow = text_workflow()
    teams.publish(TOKEN, OWNER, workflow)
    run = teams.start(
        TOKEN,
        OWNER,
        workflow.digest,
        "event",
        (Value(name="text", value="Fabricated private content"),),
    )
    teams.tick(TOKEN, OWNER, run.id)
    report = export(teams, TOKEN, OWNER)
    assert report == export(teams, TOKEN, OWNER)
    assert report.complete_snapshot and not report.grants_authority
    assert {e.source for e in report.entries} == {"runtime", "team"}
    assert "Fabricated private" not in report.model_dump_json()
    assert TOKEN.get_secret_value() not in report.model_dump_json()
    assert ADMIN.root not in report.model_dump_json()
    with pytest.raises(ToolError, match="denied"):
        export(teams, VIEWER_TOKEN, OWNER)
    with pytest.raises(ToolError, match="denied"):
        export(teams, TOKEN, OTHER)
    with pg_engine.connect() as connection:
        assert len(connection.execute(select(audit)).all()) == 1


def test_audit_export_refuses_a_partial_snapshot(pg_engine, monkeypatch):
    teams = setup(pg_engine, monkeypatch)
    with pg_engine.begin() as connection:
        connection.execute(
            audit.insert(),
            [
                dict(
                    owner=OWNER.root,
                    id=f"audit_{i}",
                    actor=ADMIN.root,
                    at=NOW,
                    action="publish",
                    digest="a" * 64,
                    revision=1,
                )
                for i in range(1001)
            ],
        )
    with pytest.raises(Conflict, match="no complete export"):
        export(teams, TOKEN, OWNER)
