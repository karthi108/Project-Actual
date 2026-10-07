from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import event, select, text
from sqlalchemy.exc import NoResultFound

from actual.core.primitives import WorkspaceId
from actual.workflows.examples import effect_workflow, text_workflow
from actual.workflows.ir import Binding, Edge, Retry, Step, Workflow
from actual.workflows.runtime import Runtime
from actual.workflows.state import Value
from actual.workflows.storage import Conflict, Store, audit, migrate

OWNER = WorkspaceId("workspace_" + "1" * 32)
NOW = datetime(2026, 10, 7, tzinfo=UTC)


def store(engine):
    migrate(engine)
    return Store(engine, OWNER)


def test_restart_and_duplicate_trigger(pg_engine):
    first = store(pg_engine)
    run = first.start(text_workflow(), "trigger_one", (Value(name="text", value="Synthetic"),), NOW)
    assert first.start(text_workflow(), "trigger_one", run.trigger, NOW).id == run.id
    with pytest.raises(Conflict):
        first.start(text_workflow(), "trigger_one", (Value(name="text", value="Changed"),), NOW)
    runtime = Runtime(first, clock=lambda: NOW)
    assert runtime.tick(run.id).current == "copy"
    restarted = Runtime(Store(pg_engine, OWNER), clock=lambda: NOW)
    assert restarted.tick(run.id).outputs[0].values[0].value == "Synthetic"
    assert restarted.tick(run.id).status == "succeeded"
    assert restarted.tick(run.id).revision == 4
    migrate(pg_engine)
    with pg_engine.connect() as connection:
        assert len(connection.execute(select(audit)).all()) == 3


def test_concurrent_reservation_lease_fencing_and_cancel(pg_engine):
    repo = store(pg_engine)
    with ThreadPoolExecutor(max_workers=2) as pool:
        ids = list(
            pool.map(
                lambda _: (
                    repo.start(
                        text_workflow(), "same", (Value(name="text", value="Synthetic"),), NOW
                    ).id
                ),
                range(2),
            )
        )
    assert ids[0] == ids[1]
    old, fence = repo.claim(ids[0], NOW)
    assert repo.claim(ids[0], NOW) is None
    replacement = repo.claim(ids[0], NOW + timedelta(seconds=31))
    assert replacement[1] > fence
    with pytest.raises(Conflict):
        repo.finish(old, fence, old.model_copy(update={"revision": 2}), NOW + timedelta(seconds=31))
    assert repo.load(old.id).revision == 1
    cancelled = repo.cancel(old.id, 1, NOW)
    assert cancelled.status == "cancelled"
    with pytest.raises(Conflict):
        repo.finish(old, replacement[1], old.model_copy(update={"revision": 2}), NOW)
    assert repo.claim(old.id, NOW) is None


def test_wait_survives_restart_and_no_early_progress(pg_engine):
    workflow = Workflow(
        id="wait_example",
        version=1,
        steps=(
            Step(id="start", kind="trigger"),
            Step(id="pause", kind="wait", wait_seconds=5),
            Step(id="done", kind="terminate"),
        ),
        edges=(
            Edge(source="start", outcome="success", target="pause"),
            Edge(source="pause", outcome="success", target="done"),
        ),
    )
    repo = store(pg_engine)
    run = repo.start(workflow, "wait_trigger", (), NOW)
    runtime = Runtime(repo, clock=lambda: NOW)
    runtime.tick(run.id)
    waiting = runtime.tick(run.id)
    assert waiting.status == "waiting"
    assert Runtime(repo, clock=lambda: NOW + timedelta(seconds=4)).tick(run.id) == waiting
    assert Runtime(repo, clock=lambda: NOW + timedelta(seconds=5)).tick(run.id).current == "done"


def test_default_policy_denies_and_human_timeout_persists(pg_engine):
    repo = store(pg_engine)
    run = repo.start(effect_workflow(), "denied", (), NOW)
    runtime = Runtime(repo, clock=lambda: NOW)
    runtime.tick(run.id)
    assert runtime.tick(run.id).current == "failed"

    class SyntheticPolicy:
        def allows(self, run, workflow, step):
            return True

    run = repo.start(effect_workflow(), "human_wait", (), NOW)
    runtime = Runtime(repo, SyntheticPolicy(), clock=lambda: NOW)
    runtime.tick(run.id)
    runtime.tick(run.id)
    waiting = runtime.tick(run.id)
    assert waiting.status == "human_wait"
    assert Runtime(repo, clock=lambda: NOW + timedelta(seconds=29)).tick(run.id) == waiting
    assert Runtime(repo, clock=lambda: NOW + timedelta(seconds=30)).tick(run.id).current == "failed"


def test_definition_version_and_owner_isolation(pg_engine):
    repo = store(pg_engine)
    run = repo.start(text_workflow(), "immutable", (Value(name="text", value="Synthetic"),), NOW)
    with pytest.raises(Conflict):
        repo.start(
            text_workflow().model_copy(update={"max_steps": 65}), "changed", run.trigger, NOW
        )
    other = Store(pg_engine, WorkspaceId("workspace_" + "2" * 32))
    with pytest.raises(NoResultFound):
        other.load(run.id)


def test_unavailable_tool_retry_is_durable_and_bounded(pg_engine):
    workflow = Workflow(
        id="retry_example",
        version=1,
        steps=(
            Step(id="start", kind="trigger"),
            Step(
                id="read",
                kind="tool",
                capability="fake_read",
                permissions=("fake_read",),
                inputs=(Binding(name="resource", source="literal", value="synthetic_record"),),
                retry=Retry(attempts=3),
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
    repo = store(pg_engine)
    run = repo.start(workflow, "retry", (), NOW)
    runtime = Runtime(repo, clock=lambda: NOW)
    runtime.tick(run.id)
    waiting = runtime.tick(run.id)
    assert waiting.attempts == 1 and waiting.due_at == NOW + timedelta(seconds=1)
    waiting = Runtime(Store(pg_engine, OWNER), clock=lambda: NOW + timedelta(seconds=1)).tick(
        run.id
    )
    assert waiting.attempts == 2 and waiting.due_at == NOW + timedelta(seconds=3)
    exhausted = Runtime(repo, clock=lambda: NOW + timedelta(seconds=3)).tick(run.id)
    assert exhausted.current == "failed" and exhausted.progress[-1].attempt == 3
    assert Runtime(repo, clock=lambda: NOW + timedelta(seconds=3)).tick(run.id).status == "failed"


def test_timeout_recovery_and_atomic_audit_rollback(pg_engine):
    repo = store(pg_engine)
    run = repo.start(text_workflow(), "timeout", (Value(name="text", value="Synthetic"),), NOW)
    times = iter((NOW, NOW + timedelta(seconds=30)))
    assert Runtime(repo, clock=lambda: next(times)).tick(run.id) == run
    assert Runtime(repo, clock=lambda: NOW + timedelta(seconds=31)).tick(run.id).current == "copy"

    def fail_audit(connection, cursor, statement, parameters, context, executemany):
        if statement.startswith("INSERT INTO actual_workflow_audit"):
            raise RuntimeError("Synthetic audit failure")

    before = repo.load(run.id)
    event.listen(pg_engine, "before_cursor_execute", fail_audit)
    try:
        with pytest.raises(RuntimeError, match="Synthetic audit failure"):
            Runtime(repo, clock=lambda: NOW + timedelta(seconds=31)).tick(run.id)
    finally:
        event.remove(pg_engine, "before_cursor_execute", fail_audit)
    assert repo.load(run.id) == before
    with pg_engine.connect() as connection:
        assert connection.execute(select(audit)).rowcount == 1
        assert (
            connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            == "0001_career_persistence"
        )
    assert Runtime(repo, clock=lambda: NOW + timedelta(seconds=62)).tick(run.id).current == "done"
