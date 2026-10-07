from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from actual.core.primitives import ActorId, WorkspaceId
from actual.workflows.approval import (
    ApprovalService,
    BusinessIntent,
    Dispatcher,
    FakeWriter,
    audit,
    intents,
    migrate,
    provider,
)
from actual.workflows.connectors import LocalPolicy
from actual.workflows.examples import effect_workflow
from actual.workflows.runtime import Runtime
from actual.workflows.storage import Conflict, Store
from actual.workflows.storage import migrate as migrate_runtime

OWNER = WorkspaceId("workspace_" + "1" * 32)
ACTOR = ActorId("actor_" + "1" * 32)
NOW = datetime(2026, 10, 7, tzinfo=UTC)
BUSINESS = BusinessIntent(business_object="fabricated_message", submission="explicit_first")


def setup(engine):
    migrate_runtime(engine)
    migrate(engine)
    repo = Store(engine, OWNER)
    policy = LocalPolicy(OWNER, ACTOR, frozenset(("fake_write",)))
    service = ApprovalService(repo, ACTOR, policy)
    dispatcher = Dispatcher(service, FakeWriter(engine), clock=lambda: NOW)
    return repo, policy, service, dispatcher


def waiting(repo, service, trigger="first", workflow=None):
    run = repo.start(workflow or effect_workflow(), trigger, (), NOW)
    runtime = Runtime(repo, service, clock=lambda: NOW)
    for _ in range(3):
        run = runtime.tick(run.id)
    assert run.status == "human_wait"
    return run


def approve(service, run, business=BUSINESS):
    preview = service.preview(run.id, business, NOW)
    return service.approve(preview, preview.digest, NOW)


def count(engine, table):
    with engine.connect() as connection:
        return len(connection.execute(select(table)).all())


def test_exact_approval_durable_fake_write_and_audit(pg_engine):
    repo, policy, service, dispatcher = setup(pg_engine)
    run = waiting(repo, service)
    approval = approve(service, run)
    runtime = Runtime(repo, service, clock=lambda: NOW, effects=dispatcher)
    completed = runtime.tick(run.id)
    assert completed.current == "done" and completed.outputs[0].values[0].name == "receipt"
    assert runtime.tick(run.id).status == "succeeded"
    assert count(pg_engine, provider) == 1
    with pg_engine.connect() as connection:
        assert set(connection.execute(select(audit.c.state)).scalars()) == {
            "approved",
            "reserved",
            "dispatching",
            "succeeded",
        }
        assert set(connection.execute(select(audit.c.approval)).scalars()) == {approval.id}
    migrate(pg_engine)


def test_stale_review_tampering_and_expiry(pg_engine):
    repo, policy, service, dispatcher = setup(pg_engine)
    run = waiting(repo, service)
    preview = service.preview(run.id, BUSINESS, NOW)
    changed = preview.model_copy(
        update={"payload": preview.payload.model_copy(update={"text": "Changed"})}
    )
    with pytest.raises(Conflict, match="Reviewed action changed"):
        service.approve(changed, changed.digest, NOW)
    approve(service, run)
    with pytest.raises(Conflict):
        service.approve(preview, preview.digest, NOW)
    dispatcher.clock = lambda: NOW + timedelta(seconds=31)
    runtime = Runtime(repo, service, clock=dispatcher.clock, effects=dispatcher)
    denied = runtime.tick(run.id)
    assert denied.failure_code == "denied" and count(pg_engine, provider) == 0


@pytest.mark.parametrize("revocation", ["permission", "approval", "policy"])
def test_immediate_predispatch_revocation(pg_engine, revocation):
    repo, policy, service, dispatcher = setup(pg_engine)
    run = waiting(repo, service)
    approval = approve(service, run)

    def revoke():
        if revocation == "permission":
            policy.revoked = True
        elif revocation == "approval":
            service.revoke(approval.id, NOW)
        else:
            policy.policy_version = 2

    dispatcher.before_dispatch = revoke
    result = Runtime(repo, service, clock=lambda: NOW, effects=dispatcher).tick(run.id)
    assert result.failure_code == "denied" and count(pg_engine, provider) == 0


def test_cancellation_before_dispatch_fences_effect(pg_engine):
    repo, policy, service, dispatcher = setup(pg_engine)
    run = waiting(repo, service)
    approve(service, run)
    dispatcher.before_dispatch = lambda: repo.cancel(run.id, repo.load(run.id).revision, NOW)
    with pytest.raises(Conflict):
        Runtime(repo, service, clock=lambda: NOW, effects=dispatcher).tick(run.id)
    assert repo.load(run.id).status == "cancelled" and count(pg_engine, provider) == 0


def test_concurrent_intents_and_upgrade_do_not_duplicate_effect(pg_engine):
    repo, policy, service, dispatcher = setup(pg_engine)
    first = waiting(repo, service, "first")
    second = waiting(repo, service, "upgraded", effect_workflow().model_copy(update={"version": 2}))
    approve(service, first)
    approve(service, second)
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(
            pool.map(
                lambda run: Runtime(repo, service, clock=lambda: NOW, effects=dispatcher).tick(
                    run.id
                ),
                (first, second),
            )
        )
    assert count(pg_engine, provider) == 1 and count(pg_engine, intents) == 1
    with pg_engine.connect() as connection:
        assert connection.execute(select(intents.c.status)).scalar_one() == "succeeded"


def test_lost_acknowledgement_restart_reconcile_never_resends(pg_engine):
    repo, policy, service, dispatcher = setup(pg_engine)
    dispatcher.provider = FakeWriter(pg_engine, lose_response=True)
    first = waiting(repo, service)
    approval = approve(service, first)
    result = Runtime(repo, service, clock=lambda: NOW, effects=dispatcher).tick(first.id)
    assert result.failure_code == "unknown_outcome" and count(pg_engine, provider) == 1
    restarted = Dispatcher(
        ApprovalService(Store(pg_engine, OWNER), ACTOR, policy),
        FakeWriter(pg_engine),
        clock=lambda: NOW,
    )
    policy.revoked = True
    assert restarted.reconcile(approval.id).receipt.startswith("receipt_")
    policy.revoked = False
    second = waiting(repo, service, "second", effect_workflow().model_copy(update={"version": 2}))
    approve(service, second)
    assert (
        Runtime(repo, service, clock=lambda: NOW, effects=restarted).tick(second.id).current
        == "done"
    )
    assert count(pg_engine, provider) == 1


def test_same_intent_changed_payload_conflicts(pg_engine):
    repo, policy, service, dispatcher = setup(pg_engine)
    first = waiting(repo, service)
    approve(service, first)
    Runtime(repo, service, clock=lambda: NOW, effects=dispatcher).tick(first.id)
    original = effect_workflow()
    send = next(s for s in original.steps if s.id == "send")
    changed_send = send.model_copy(
        update={
            "inputs": (
                send.inputs[0],
                send.inputs[1].model_copy(update={"value": "Changed fabricated message"}),
            )
        }
    )
    changed = original.model_copy(
        update={
            "version": 2,
            "steps": tuple(changed_send if s.id == "send" else s for s in original.steps),
        }
    )
    second = waiting(repo, service, "changed", changed)
    approve(service, second)
    result = Runtime(repo, service, clock=lambda: NOW, effects=dispatcher).tick(second.id)
    assert result.failure_code == "denied" and count(pg_engine, provider) == 1


def test_human_denial_and_no_permission_do_not_dispatch(pg_engine):
    repo, policy, service, dispatcher = setup(pg_engine)
    run = waiting(repo, service)
    assert service.deny(run.id, run.revision, NOW).current == "failed"
    policy.revoked = True
    other = repo.start(effect_workflow(), "denied", (), NOW)
    runtime = Runtime(repo, service, clock=lambda: NOW, effects=dispatcher)
    runtime.tick(other.id)
    assert runtime.tick(other.id).current == "failed"
    assert count(pg_engine, provider) == 0


def test_missing_approval_cannot_be_bypassed_by_a_buggy_worker(pg_engine):
    repo, policy, service, dispatcher = setup(pg_engine)
    run = repo.start(effect_workflow(), "buggy_worker", (), NOW)
    old, fence = repo.claim(run.id, NOW)
    repo.finish(old, fence, old.model_copy(update={"current": "send", "revision": 2}), NOW)
    result = Runtime(repo, service, clock=lambda: NOW, effects=dispatcher).tick(run.id)
    assert result.failure_code == "denied" and count(pg_engine, provider) == 0
