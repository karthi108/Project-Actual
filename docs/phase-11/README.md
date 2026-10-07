# Persisted workflow runtime

IMPLEMENTED; office checks are recorded in the validation debt register. Canonical acceptance PENDING.

Problem: a workflow must retain progress across process restarts without replaying consequential effects. The smallest solution is separate PostgreSQL definition/run/audit tables, immutable definition hashes, trigger deduplication and fenced short leases. Explicit operator migration `actual.workflows.storage.migrate(engine)` is additive and versioned separately; accepted Career migration `0001` remains frozen. Runtime construction never runs DDL.

One `tick` performs one bounded registered step. Deterministic copy/predicate, branch, durable wait, policy denial and terminal states execute locally. AI/tool declarations route to explicit unavailable/error outcomes with bounded exponential retry waits. No arbitrary function/code or external effect is dispatched. A server-supplied policy port defaults to deny; policy success alone still cannot execute writes.

Human waits persist until timeout or explicit run cancellation. Positive effect approval arrives in Phase 13. Restart reconstructs state from PostgreSQL; an expired lease is recoverable with a new fencing token. Cancellation invalidates leases. State and metadata-only audit append commit atomically.

Trade-offs: sequential DAG execution, no daemon, queue framework, Temporal or real connector. Lease expiry does not promise exactly-once pure computation; stale workers cannot commit. Effect recovery needs a distinct business-intent boundary, not this run lease. Synthetic scalar inputs are bounded but synthetic labels cannot detect secretly supplied private prose.

Run `python -m pytest tests/workflows tests/persistence/test_workflow_runtime.py` with the accepted explicit disposable `ACTUAL_TEST_DATABASE_URL`. Checks cover concurrent trigger reservation, immutable versions, owner isolation, restart, leases, cancellation, waits, unavailable-tool retry exhaustion, late-computation recovery and audit rollback. Explicit migration is repeated and the accepted Career Alembic head remains `0001_career_persistence`.

Use `python -m actual.careerlab verify --manifest docs/office-build/careerlab-environment.json` for the current office configuration. This separate manifest preserves all eight accepted input/oracle identities; historical manifests remain unchanged. Updating project testpaths changes configuration identity, never fixture contents. `scripts/refresh_office_manifest.py` refuses changed record identities before writing only the office manifest.
