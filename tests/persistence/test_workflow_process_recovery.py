"""Kill only owned spawned workers at synthetic transaction/dispatch boundaries."""

import multiprocessing
import os
import re
from datetime import UTC, datetime, timedelta
from multiprocessing.connection import Connection

import pytest
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.engine import URL
from sqlalchemy.pool import NullPool

from actual.core.primitives import ActorId, WorkspaceId
from actual.workflows.approval import (
    ApprovalService,
    BusinessIntent,
    Dispatcher,
    FakeWriter,
    intents,
    provider,
)
from actual.workflows.approval import migrate as migrate_approval
from actual.workflows.connectors import LocalPolicy
from actual.workflows.examples import effect_workflow, text_workflow
from actual.workflows.runtime import Runtime
from actual.workflows.state import Value
from actual.workflows.storage import Conflict, Store, dead_letters, migrate
from actual.workflows.storage import audit as run_audit

OWNER = WorkspaceId("workspace_" + "1" * 32)
ACTOR = ActorId("actor_" + "1" * 32)
NOW = datetime(2026, 10, 8, tzinfo=UTC)
AFTER_LEASE = NOW + timedelta(seconds=31)


def _worker(url: URL, schema: str, identifier: str, stage: str, control: Connection) -> None:
    # Spawn a fresh interpreter/engine; never inherit a pool or use a caller-selected schema.
    if (
        url.host not in ("localhost", "127.0.0.1", "::1")
        or re.fullmatch(r"actual_test_[0-9a-f]{32}", schema) is None
    ):
        os._exit(2)
    engine = create_engine(
        url,
        echo=False,
        hide_parameters=True,
        poolclass=NullPool,
        connect_args={
            "options": f"-c search_path={schema},pg_catalog,public,pg_temp -c timezone=UTC"
        },
    )

    def checkpoint() -> None:
        control.send(stage)
        if not control.poll(45):
            raise RuntimeError("Owned worker control deadline")
        control.recv()
        raise RuntimeError("Stopped worker must never resume")

    try:
        repo = Store(engine, OWNER)
        if stage == "claimed":
            assert repo.claim(identifier, NOW) is not None
            checkpoint()
        elif stage == "inflight_finish":
            commits = 0

            def before_commit(_connection) -> None:
                nonlocal commits
                commits += 1
                # claim commits first; finish's state+audit are still uncommitted here.
                if commits == 2:
                    checkpoint()

            event.listen(engine, "commit", before_commit)
            Runtime(repo, clock=lambda: NOW).tick(identifier)
        else:
            service = ApprovalService(
                repo, ACTOR, LocalPolicy(OWNER, ACTOR, frozenset(("fake_write",)))
            )

            class PausedWriter(FakeWriter):
                def write(self, payload, key):
                    if stage == "dispatching":
                        checkpoint()
                    result = super().write(payload, key)
                    if stage == "accepted":
                        checkpoint()
                    return result

            dispatcher = Dispatcher(
                service,
                PausedWriter(engine),
                clock=lambda: NOW,
                before_dispatch=checkpoint if stage == "reserved" else lambda: None,
            )
            Runtime(repo, service, clock=lambda: NOW, effects=dispatcher).tick(identifier)
        # A missing checkpoint is a failed test, never an inferred crash result.
        control.send("checkpoint_missing")
    except BaseException:
        # Fixed diagnostic only: no URL, credentials, raw provider payload or traceback.
        control.send("worker_failed")
    finally:
        engine.dispose()
        control.close()


def _kill_worker(engine, identifier, stage):
    with engine.connect() as connection:
        schema = connection.exec_driver_sql("SELECT current_schema()").scalar_one()
    assert re.fullmatch(r"actual_test_[0-9a-f]{32}", schema)
    context = multiprocessing.get_context("spawn")
    parent, child = context.Pipe()
    process = context.Process(target=_worker, args=(engine.url, schema, identifier, stage, child))
    try:
        process.start()
        child.close()
        assert parent.poll(30), "Owned worker did not reach its checkpoint"
        assert parent.recv() == stage, "Owned worker failed before its checkpoint"
        process.kill()
        process.join(10)
        assert not process.is_alive(), "Owned killed worker has not exited"
        assert process.exitcode not in (None, 0)
    finally:
        # Only this Process object is controlled; no PID enumeration/shared-service shutdown.
        if process.pid is not None and process.is_alive():
            process.kill()
            process.join(10)
        assert not process.is_alive(), "Preserve the owned database if cleanup is uncertain"
        parent.close()
        child.close()
        process.close()


def _count(engine, table):
    with engine.connect() as connection:
        return connection.execute(select(func.count()).select_from(table)).scalar_one()


@pytest.mark.parametrize("stage", ["claimed", "inflight_finish"])
def test_killed_worker_recovers_lease_and_rolls_back_uncommitted_progress(pg_engine, stage):
    migrate(pg_engine)
    repo = Store(pg_engine, OWNER)
    run = repo.start(text_workflow(), stage, (Value(name="text", value="Fabricated"),), NOW)
    before = Runtime(repo, clock=lambda: NOW).tick(run.id)
    _kill_worker(pg_engine, run.id, stage)
    assert repo.load(run.id) == before and _count(pg_engine, run_audit) == 1
    assert Runtime(repo, clock=lambda: NOW).tick(run.id) == before
    recovered = Runtime(Store(pg_engine, OWNER), clock=lambda: AFTER_LEASE)
    result = recovered.tick(run.id)
    assert result.current == "done"
    assert result.outputs[0].values == (Value(name="text", value="Fabricated"),)
    assert recovered.tick(run.id).status == "succeeded"
    assert _count(pg_engine, run_audit) == 3 and _count(pg_engine, dead_letters) == 0


@pytest.mark.parametrize("stage", ["reserved", "dispatching", "accepted"])
@pytest.mark.parametrize("revoke", [False, True])
def test_killed_effect_worker_reconciles_without_unsafe_resend(pg_engine, stage, revoke):
    migrate(pg_engine)
    migrate_approval(pg_engine)
    repo = Store(pg_engine, OWNER)
    service = ApprovalService(repo, ACTOR, LocalPolicy(OWNER, ACTOR, frozenset(("fake_write",))))
    original = effect_workflow()
    workflow = original.model_copy(
        update={
            "steps": tuple(
                step.model_copy(update={"timeout_seconds": 120}) if step.id == "review" else step
                for step in original.steps
            )
        }
    )
    run = repo.start(workflow, stage, (), NOW)
    runtime = Runtime(repo, service, clock=lambda: NOW)
    for _ in range(3):
        runtime.tick(run.id)
    preview = service.preview(
        run.id, BusinessIntent(business_object="fake_message", submission="explicit_first"), NOW
    )
    approval = service.approve(preview, preview.digest, NOW)
    before = repo.load(run.id)
    _kill_worker(pg_engine, run.id, stage)
    assert repo.load(run.id) == before
    with pg_engine.connect() as connection:
        intent = connection.execute(select(intents)).mappings().one()
    assert intent["status"] == ("reserved" if stage == "reserved" else "dispatching")
    assert intent["receipt"] is None
    assert _count(pg_engine, provider) == (1 if stage == "accepted" else 0)

    class RecoveryWriter(FakeWriter):
        writes = 0
        lookups = 0

        def write(self, payload, key):
            self.writes += 1
            return super().write(payload, key)

        def reconcile(self, key):
            self.lookups += 1
            return super().reconcile(key)

    port = RecoveryWriter(pg_engine)
    restarted_service = ApprovalService(
        Store(pg_engine, OWNER), ACTOR, LocalPolicy(OWNER, ACTOR, frozenset(("fake_write",)))
    )
    dispatcher = Dispatcher(restarted_service, port, clock=lambda: AFTER_LEASE)
    restarted = Runtime(
        restarted_service.store, restarted_service, clock=lambda: AFTER_LEASE, effects=dispatcher
    )
    assert Runtime(repo, service, clock=lambda: NOW, effects=dispatcher).tick(run.id) == before
    assert port.writes == port.lookups == 0
    if revoke:
        restarted_service.revoke(approval.id, AFTER_LEASE)
    result = restarted.tick(run.id)
    unknown = stage == "dispatching"
    failed = unknown or revoke
    assert result.current == ("failed" if failed else "done")
    assert result.failure_code == ("denied" if revoke else "unknown_outcome" if unknown else None)
    terminal = restarted.tick(run.id)
    assert terminal.status == ("failed" if failed else "succeeded")
    assert restarted.tick(run.id) == terminal
    writes = int(stage == "reserved" and not revoke)
    assert port.writes == writes
    assert port.lookups == int(stage != "reserved" and not revoke)
    assert _count(pg_engine, provider) == int(stage == "accepted" or writes == 1)
    assert _count(pg_engine, dead_letters) == int(failed)
    if stage == "reserved" and revoke:
        with pytest.raises(Conflict, match="not crossed the dispatch boundary"):
            dispatcher.reconcile(approval.id)
        assert port.writes == port.lookups == 0
        return
    receipt = dispatcher.reconcile(approval.id)
    assert (receipt is None) == unknown
    if receipt is not None and not revoke:
        assert result.outputs[0].values == (Value(name="receipt", value=receipt.receipt),)
    # A recovered receipt can record an outcome, never revive a revoked failed run.
    assert repo.load(run.id) == terminal and port.writes == writes
