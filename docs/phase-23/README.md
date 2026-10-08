# Reliability hardening

IMPLEMENTED synthetic reliability hardening; canonical acceptance PENDING.

Workflow migration 2 adds metadata-only dead letters without changing accepted Career migration/history. Failed terminal runs append one owner/run failure record atomically with state and audit. No failure is reset into a new write automatically. Current run deadlines can wake an overdue wait; successful safe-read retry clears the earlier error. Backoff has stable per-run/step/attempt jitter, bounded at 300 seconds, and the IR budgets its maximum delay.

Fault coverage uses real disposable PostgreSQL and fake providers: duplicate triggers/concurrent intents, stale fences, worker restart/cancellation, DB pool reconnect, read 429/500-like errors, expired-credential abstention, malformed output, retry exhaustion, stale/revoked approval, crash after dispatch marker, and acceptance before acknowledgement loss. Uncertain writes reconcile without resend. Known provider receipts survive racing unknown recovery. No communication can be unsent, so automatic compensation is unavailable; any compensating action needs a distinct reviewed intent.

Accepted ModelGateway timeout/malformed-output/adversarial checks are rerun separately; Workflow IR AI declarations remain unavailable and no new live inference is claimed. Cycles and unbounded execution fail graph validation. Fake credential expiry is an error case, not working OAuth integration.

Run workflow/persistence tests with the explicit disposable URL and `python -m pytest tests/models` for accepted model faults. Canonical process-kill acceptance, network partitions/long-lived database outages, real provider retention/idempotency/rate limits, operational recovery and compensation remain pending. Synthetic fixtures do not prove production reliability.

## Follow-up: abrupt worker termination

`tests/persistence/test_workflow_process_recovery.py` starts a fresh Python interpreter with its own database engine in the fixture's verified disposable schema. The parent waits for a fixed checkpoint, kills only the Process object it created, joins it with bounded cleanup, then creates a fresh runtime/dispatcher. No shared process is enumerated or stopped. Test synchronization pipes are discarded after termination, with no queue/lock recovery assumption. The explicit spawn context avoids inheriting a database pool. [Python process lifecycle](https://docs.python.org/3.14/library/multiprocessing.html#process-and-exceptions)

| Boundary | Required behavior |
| --- | --- |
| Claimed lease, no progress | Before lease expiry, another worker makes no progress; afterward, bounded work resumes |
| Run state/audit updated, transaction not committed | Abrupt disconnection rolls back both; recovery produces one committed progress/audit history |
| Intent reserved, dispatch marker absent | A still-valid exact approval permits the first fake write once |
| Dispatch marker committed, no provider receipt | Recovery performs a read-only lookup, records an unknown outcome and fails safely without resend |
| Fake provider accepted, acknowledgement absent | Recovery reads the durable receipt, records success and resumes local progress without another write |
| Exact approval revoked after each effect-boundary crash | Runtime dispatch/progress is denied; read-only receipt reconciliation cannot reactivate the failed run |

The uncommitted-progress checkpoint uses the existing SQLAlchemy connection commit event; the test then verifies rollback against actual PostgreSQL. [SQLAlchemy connection events](https://docs.sqlalchemy.org/en/21/core/events.html#sqlalchemy.events.ConnectionEvents.commit)

The effect fixture gives its synthetic review a 120-second deadline so the 30-second step lease can expire while exact approval is still valid. Virtual time selects recovery boundaries; reported test duration is not workflow latency or a throughput benchmark. The original example definition, runtime, migrations, gateway and provider contracts remain unchanged. The fake provider uses a separate committed transaction in the same disposable database, rather than an actual external system. This campaign exercises worker loss, not database-server failure, power loss, arbitrary network partitions or real provider guarantees.

Checks and follow-up checkpoint are recorded in the [office debt register](../office-build/canonical-validation-pending.md#post-handoff-reliability-follow-up). Reproduce with an explicitly configured owned disposable PostgreSQL database, on each supported Python version:

```powershell
uv run --isolated --python $actualPy313 --locked python -m pytest -q tests/persistence/test_workflow_process_recovery.py
uv run --isolated --python $actualPy314 --locked python -m pytest -q tests/persistence/test_workflow_process_recovery.py
```

Use the interpreter paths/private database setup in the [handoff](../office-build/handoff.md#personal-laptop-validation-commands). Office verification does not replace canonical Windows/Linux and operational fault acceptance.
