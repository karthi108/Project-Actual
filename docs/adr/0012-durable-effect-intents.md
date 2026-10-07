# ADR 0012 — Exact approval and durable effect identity

Status: provisional office implementation; canonical validation pending.

The accepted contract requires approval of an exact action and duplicate prevention across workflow upgrades. Run ID, workflow digest and an outbox alone cannot identify a business submission or prove remote delivery. Retrying after a lost response may duplicate a successful effect.

Use closed previews and owner-scoped immutable approvals. Reserve a stable business intent independently of workflow version and bind approval atomically. Recheck current authorization, exact arguments/content, policy, expiry, revocation and worker fence immediately before a committed dispatch marker. This marker defines the cancellation boundary. Append metadata-only audit in each local state transaction.

Use a separate keyed fake provider to exercise receipt loss and restart. Once dispatch is uncertain, reconcile without automatic resend. Preserve confirmed results against racing unknown recoveries. Real provider ports must establish idempotency/reconciliation semantics before activation; a local unique constraint cannot do that for them.

Keep PostgreSQL and the small explicit runtime. Neither Temporal nor a queue service is required by the demonstrated bounded DAG slice. This choice remains reviewable as reliability and scale requirements accumulate.
