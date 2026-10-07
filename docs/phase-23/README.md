# Reliability hardening

IMPLEMENTED synthetic reliability hardening; canonical acceptance PENDING.

Workflow migration 2 adds metadata-only dead letters without changing accepted Career migration/history. Failed terminal runs append one owner/run failure record atomically with state and audit. No failure is reset into a new write automatically. Current run deadlines can wake an overdue wait; successful safe-read retry clears the earlier error. Backoff has stable per-run/step/attempt jitter, bounded at 300 seconds, and the IR budgets its maximum delay.

Fault coverage uses real disposable PostgreSQL and fake providers: duplicate triggers/concurrent intents, stale fences, worker restart/cancellation, DB pool reconnect, read 429/500-like errors, expired-credential abstention, malformed output, retry exhaustion, stale/revoked approval, crash after dispatch marker, and acceptance before acknowledgement loss. Uncertain writes reconcile without resend. Known provider receipts survive racing unknown recovery. No communication can be unsent, so automatic compensation is unavailable; any compensating action needs a distinct reviewed intent.

Accepted ModelGateway timeout/malformed-output/adversarial checks are rerun separately; Workflow IR AI declarations remain unavailable and no new live inference is claimed. Cycles and unbounded execution fail graph validation. Fake credential expiry is an error case, not working OAuth integration.

Run workflow/persistence tests with the explicit disposable URL and `python -m pytest tests/models` for accepted model faults. Canonical process-kill/network-partition/long-lived DB, real provider retention/idempotency/rate limits, operational recovery and compensation remain pending. Synthetic fixtures do not prove production reliability.
