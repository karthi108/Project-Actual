from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select, update

from actual.core.primitives import ActorId, WorkspaceId
from actual.workflows.approval import (
    ApprovalService,
    BusinessIntent,
    Dispatcher,
    FakeWriter,
    provider,
)
from actual.workflows.approval import (
    migrate as migrate_approval,
)
from actual.workflows.connectors import FakeReader, LocalPolicy, ReadConnector, ToolError
from actual.workflows.examples import effect_workflow, read_workflow, text_workflow
from actual.workflows.ir import Retry
from actual.workflows.runtime import Runtime
from actual.workflows.state import Value
from actual.workflows.storage import Store, dead_letters, metadata, migrate, runs, version

OWNER = WorkspaceId("workspace_" + "1" * 32)
ACTOR = ActorId("actor_" + "1" * 32)
NOW = datetime(2026, 10, 7, tzinfo=UTC)


def repository(engine):
    migrate(engine)
    return Store(engine, OWNER)


@pytest.mark.parametrize(
    "code", ["rate_limited", "unavailable", "expired_credentials", "invalid_output"]
)
def test_connector_faults_retry_only_safe_reads_and_dead_letter_terminal_failures(pg_engine, code):
    repo = repository(pg_engine)
    original = read_workflow()
    workflow = original.model_copy(
        update={
            "steps": tuple(
                s.model_copy(update={"retry": Retry(attempts=2)}) if s.id == "read" else s
                for s in original.steps
            )
        }
    )

    class Flaky:
        calls = 0

        def read(self, request):
            self.calls += 1
            if self.calls == 1:
                raise ToolError(code)
            return FakeReader().read(request)

    faulty = Flaky()
    port = ReadConnector(faulty, ACTOR, LocalPolicy(OWNER, ACTOR, frozenset(("fake_read",))))
    run = repo.start(workflow, "fault", (Value(name="resource", value="synthetic_record"),), NOW)
    runtime = Runtime(repo, clock=lambda: NOW, connector=port)
    runtime.tick(run.id)
    result = runtime.tick(run.id)
    if code in ("rate_limited", "unavailable"):
        assert result.status == "waiting" and result.attempts == 1
        later = Runtime(
            Store(pg_engine, OWNER), clock=lambda: NOW + timedelta(seconds=1), connector=port
        )
        assert later.tick(run.id).failure_code is None
        assert later.tick(run.id).status == "succeeded" and faulty.calls == 2
    else:
        assert result.current == "failed"
        assert runtime.tick(run.id).status == "failed" and faulty.calls == 1
        with pg_engine.connect() as connection:
            assert connection.execute(select(dead_letters.c.code)).scalar_one() == code


def test_deadline_wakes_waits_reconnect_and_migration_upgrade_preserve_data(pg_engine):
    with pg_engine.begin() as connection:
        metadata.create_all(
            connection,
            tables=[table for table in metadata.sorted_tables if table is not dead_letters],
        )
        connection.execute(version.insert().values(version=1))
    repo = Store(pg_engine, OWNER)
    run = repo.start(text_workflow(), "restart", (Value(name="text", value="Fabricated"),), NOW)
    with pg_engine.begin() as connection:
        # Simulates a pending wait extending past the run deadline.
        changed = run.model_copy(
            update={"status": "waiting", "due_at": NOW + timedelta(seconds=2000)}
        )
        connection.execute(
            update(runs).where(runs.c.id == run.id).values(payload=changed.model_dump(mode="json"))
        )
    migrate(pg_engine)
    pg_engine.dispose()
    later = Runtime(Store(pg_engine, OWNER), clock=lambda: NOW + timedelta(seconds=901))
    assert later.tick(run.id).failure_code == "deadline_exceeded"
    assert later.tick(run.id).status == "failed"
    with pg_engine.connect() as connection:
        assert connection.execute(select(version.c.version)).scalar_one() == 2
        assert connection.execute(select(dead_letters.c.run)).scalar_one() == run.id


def test_worker_crash_after_dispatch_marker_never_resends_unaccepted_intent(pg_engine):
    repo = repository(pg_engine)
    migrate_approval(pg_engine)
    policy = LocalPolicy(OWNER, ACTOR, frozenset(("fake_write",)))
    service = ApprovalService(repo, ACTOR, policy)
    run = repo.start(effect_workflow(), "crash", (), NOW)
    runtime = Runtime(repo, service, clock=lambda: NOW)
    for _ in range(3):
        runtime.tick(run.id)
    preview = service.preview(
        run.id, BusinessIntent(business_object="fake_object", submission="explicit_first"), NOW
    )
    approval = service.approve(preview, preview.digest, NOW)

    class Crash:
        writes = 0

        def write(self, request, key):
            self.writes += 1
            raise SystemExit("Synthetic worker crash")

        def reconcile(self, key):
            return None

    crash = Crash()
    dispatcher = Dispatcher(service, crash, clock=lambda: NOW)
    with pytest.raises(SystemExit):
        Runtime(repo, service, clock=lambda: NOW, effects=dispatcher).tick(run.id)
    assert crash.writes == 1
    recovery = Dispatcher(service, FakeWriter(pg_engine), clock=lambda: NOW)
    assert recovery.reconcile(approval.id) is None
    with pg_engine.connect() as connection:
        assert connection.execute(select(provider)).all() == []


def test_provider_acceptance_survives_crash_before_local_progress(pg_engine):
    repo = repository(pg_engine)
    migrate_approval(pg_engine)
    service = ApprovalService(repo, ACTOR, LocalPolicy(OWNER, ACTOR, frozenset(("fake_write",))))
    run = repo.start(effect_workflow(), "accepted", (), NOW)
    runtime = Runtime(repo, service, clock=lambda: NOW)
    for _ in range(3):
        runtime.tick(run.id)
    preview = service.preview(
        run.id, BusinessIntent(business_object="fake_object", submission="explicit_first"), NOW
    )
    service.approve(preview, preview.digest, NOW)

    class AcceptedThenCrash(FakeWriter):
        def write(self, request, key):
            super().write(request, key)
            raise SystemExit("Synthetic acknowledgement crash")

    with pytest.raises(SystemExit):
        Runtime(
            repo,
            service,
            clock=lambda: NOW,
            effects=Dispatcher(service, AcceptedThenCrash(pg_engine), clock=lambda: NOW),
        ).tick(run.id)
    # This synthetic gate has a short expiry. The provider receipt can be reconciled,
    # while an expired approval cannot authorize a resend or advance this run.
    with pg_engine.connect() as connection:
        assert len(connection.execute(select(provider)).all()) == 1
