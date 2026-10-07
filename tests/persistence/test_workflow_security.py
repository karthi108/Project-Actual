"""Synthetic adversarial storage changes must fail before any provider effect."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select, text, update

from actual.core.primitives import ActorId, WorkspaceId
from actual.workflows.approval import (
    ApprovalService,
    BusinessIntent,
    Dispatcher,
    FakeWriter,
    approvals,
    audit,
    provider,
)
from actual.workflows.approval import migrate as migrate_approval
from actual.workflows.connectors import LocalPolicy
from actual.workflows.examples import effect_workflow, text_workflow
from actual.workflows.ir import slot
from actual.workflows.runtime import Runtime
from actual.workflows.state import Value
from actual.workflows.storage import Conflict, Store, definitions, migrate, runs

OWNER = WorkspaceId("workspace_" + "1" * 32)
ACTOR = ActorId("actor_" + "1" * 32)
NOW = datetime(2026, 10, 7, tzinfo=UTC)


@pytest.mark.parametrize("field", ["id", "workspace_id", "revision", "trigger_id", "trigger"])
def test_stored_run_identity_tampering_is_rejected(pg_engine, field):
    migrate(pg_engine)
    repo = Store(pg_engine, OWNER)
    run = repo.start(text_workflow(), "record", (Value(name="text", value="Fabricated"),), NOW)
    payload = run.model_dump(mode="json")
    payload[field] = {
        "id": "run_other",
        "workspace_id": "workspace_" + "2" * 32,
        "revision": 2,
        "trigger_id": "other",
        "trigger": [Value(name="text", value="Changed").model_dump(mode="json")],
    }[field]
    with pg_engine.begin() as connection:
        connection.execute(update(runs).where(runs.c.id == run.id).values(payload=payload))
    with pytest.raises(Conflict, match="identity"):
        repo.load(run.id)
    with pytest.raises(Conflict, match="identity"):
        repo.claim(run.id, NOW)


@pytest.mark.parametrize("field,value", [("name", "changed"), ("version", 2)])
def test_definition_metadata_tampering_is_rejected(pg_engine, field, value):
    migrate(pg_engine)
    repo = Store(pg_engine, OWNER)
    workflow = text_workflow()
    run = repo.start(workflow, "record", (Value(name="text", value="Fabricated"),), NOW)
    with pg_engine.begin() as connection:
        connection.execute(update(definitions).values({field: value}))
    with pytest.raises(Conflict, match="identity"):
        repo.definition(workflow.digest)
    with pytest.raises(Conflict, match="identity"):
        repo.claim(run.id, NOW)


@pytest.mark.parametrize("field", ["approver", "expires_at", "reviewed_digest", "legacy_seal"])
def test_full_approval_record_is_sealed_before_dispatch(pg_engine, field):
    migrate(pg_engine)
    migrate_approval(pg_engine)
    repo = Store(pg_engine, OWNER)
    policy = LocalPolicy(OWNER, ACTOR, frozenset(("fake_write",)))
    service = ApprovalService(repo, ACTOR, policy)
    runtime = Runtime(repo, service, clock=lambda: NOW)
    run = repo.start(effect_workflow(), "record", (), NOW)
    for _ in range(3):
        run = runtime.tick(run.id)
    preview = service.preview(
        run.id, BusinessIntent(business_object="fabricated", submission="explicit_first"), NOW
    )
    approval = service.approve(preview, preview.digest, NOW)
    payload = approval.model_dump(mode="json")
    with pg_engine.begin() as connection:
        if field == "legacy_seal":
            connection.execute(update(audit).values(authority="a" * 64))
        else:
            payload[field] = {
                "approver": "actor_" + "2" * 32,
                "expires_at": (NOW + timedelta(hours=1)).isoformat(),
                "reviewed_digest": "b" * 64,
            }[field]
            connection.execute(update(approvals).values(payload=payload))
    runtime.effects = Dispatcher(service, FakeWriter(pg_engine), clock=lambda: NOW)
    denied = runtime.tick(run.id)
    assert denied.failure_code == "denied"
    with pg_engine.connect() as connection:
        assert connection.execute(select(provider)).all() == []


@pytest.mark.parametrize("drift", ["column", "unique"])
def test_migration_refuses_unknown_table_shapes(pg_engine, drift):
    migrate(pg_engine)
    with pg_engine.begin() as connection:
        if drift == "column":
            connection.execute(
                text(
                    "ALTER TABLE actual_workflow_runs ALTER COLUMN trigger_digest TYPE varchar(65)"
                )
            )
        else:
            connection.execute(
                text(
                    "ALTER TABLE actual_workflow_runs DROP CONSTRAINT "
                    "actual_workflow_runs_owner_workflow_trigger_id_key"
                )
            )
    with pytest.raises(ValueError, match="Unsupported workflow"):
        migrate(pg_engine)


def test_trigger_field_order_is_not_a_new_business_event(pg_engine):
    migrate(pg_engine)
    repo = Store(pg_engine, OWNER)
    workflow = text_workflow().model_copy(
        update={"trigger_schema": (slot("text", "text"), slot("flag", "boolean"))}
    )
    values = (Value(name="text", value="Fabricated"), Value(name="flag", value=True))
    original = repo.start(workflow, "same_event", values, NOW)
    assert repo.start(workflow, "same_event", tuple(reversed(values)), NOW) == original
