# Exact approval and controlled fake effects

IMPLEMENTED; office evidence is recorded separately. Canonical acceptance PENDING.

Problem: a workflow gate, a content review or a successful policy check cannot authorize an unspecified future write. The simplest solution is an immutable preview plus an owner-scoped approval record, durable business intent and explicit dispatch boundary. All effects here are fabricated PostgreSQL provider records; no external accounts, URLs, credentials or real messages exist.

`ApprovalService.preview` shows the exact synthetic payload and creates a digest of its principal, owner, run, workflow version/hash, protected step, capability, destination, canonical arguments, content hash, explicit business object/submission intent, policy version, revision and expiry. `approve` compares the exact reviewed digest with a fresh preview under a run lock, records the trusted server approver and advances only the current human gate. Stale reviews, changed inputs, expiry and policy changes fail. Content review from Phase 9 is a different contract and cannot create an effect approval. `deny` follows the explicit rejection edge; cancellation and revocation invalidate future dispatch.

The dispatcher reserves the stable intent and binds the approval in one transaction. A second locked transaction immediately checks current authorization, exact binding, expiry, revocation, run revision and fencing token before committing `dispatching`. That commit is the cancellation/revocation boundary: requests stopped beforehand cannot dispatch; a later cancellation cannot promise to undo a provider acceptance. Audit records identify actor, workflow, action/intent, approval, authority/context digest and result without duplicating payload text.

Business identity is owner + fabricated provider account + action + destination + business object + explicitly reviewed submission intent. It excludes workflow version. A changed payload under the same identity conflicts. An upgrade cannot manufacture a second send. Deliberate new submission requires a distinct explicit intent and new review.

The fake provider commits a keyed receipt independently to model the remote transaction boundary. Dispatch failures become `outcome_unknown`; no automatic resend occurs. Restart/recovery calls read-only reconciliation, including after revocation, and records a recovered receipt. A previously confirmed receipt cannot be downgraded by a racing recovery. Run leases alone never prove exactly-once effects. There is no exactly-once remote claim.

Explicit operator migration: first `actual.workflows.storage.migrate(engine)`, then `actual.workflows.approval.migrate(engine)`. Neither runtime construction nor the accepted HTTP server migrates or activates anything. Run `python -m pytest tests/persistence/test_effect_approval.py` with the accepted disposable database configuration.

Trade-offs: synthetic single-owner trusted service calls, sequential DAGs and conservative unknown-outcome handling. No user authentication, approval UI, live connector or real-data activation is claimed. Authorizer configuration, clocks and provider ports belong to the trusted application composition, never Workflow IR or model output. Permission storage, real provider expiry/idempotency/compensation and operational recovery need canonical integration evidence.
