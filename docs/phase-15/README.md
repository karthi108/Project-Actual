# Shadow mode

IMPLEMENTED; canonical acceptance PENDING.

Shadow runs the same isolated simulator against a live-like synthetic observation and compares its transitions with an explicit registered human path. Human observations are data, never permission. Invalid paths fail validation. The comparison records mismatched steps, completion/escalation and per-step `unobserved`, `shadow`, `candidate` or `human` readiness. A matching development trace is candidate evidence only; it cannot activate anything. Approval and consequential steps stay human.

Explicit `actual.worklab.shadow.migrate(engine)` adds owner-scoped observation storage. Event identity is deduplicated; changed content under the same event conflicts. Records contain input/definition hashes and transition metadata, without raw case text. The accepted HTTP API and Career migrations remain unchanged.

Checks: pure comparison/mismatch/path/isolation tests plus real-PostgreSQL persistence, restart, deduplication and owner separation. Canonical real observation capture, readiness calibration and security review remain pending. No real workplace feed, accuracy claim or consequential shadow write is enabled.
