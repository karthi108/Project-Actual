# Phase 27 — Enterprise research and bounded audit export

Status: IMPLEMENTED research decisions, operational guidance, synthetic audit export and fresh-clone evaluator bootstrap. Office checks are provisional; canonical acceptance and enterprise integration remain PENDING. This phase does not make ACTUAL an enterprise deployment.

The problem is identifying which demonstrated controls can support a future enterprise boundary, without treating a synthetic harness as real security infrastructure. The simplest additions are a read-only audit snapshot and explicit readiness decisions. No identity, provisioning, secrets, orchestration or enterprise connector dependency is installed. Major decisions are [ADR 0015](../adr/0015-enterprise-identity-and-isolation.md) and [ADR 0016](../adr/0016-runtime-scaling-and-temporal.md).

## Implemented additions

`actual.workflows.audit_export.export(teams, token, workspace)` requires a current synthetic administrator before and after reading a repeatable-read snapshot of four workspace-scoped audit tables: runtime, effects, activation and team configuration. It returns a closed synthetic contract with timestamps, fixed actions and metadata digests. It does not return run payloads, document text, prompts, credentials or session tokens; actor identifiers are hashed. Hashes are pseudonymous correlation, not guaranteed anonymity or an administrator-proof signature.

The export includes all records in those four tables at the snapshot, up to a combined 1,000 entries. Larger snapshots fail instead of silently truncating; there is no pagination/large-volume export. Session checks occur at the two release boundaries, not as a distributed continuous revocation guarantee. `complete_snapshot=true` describes only those table contents, not completeness of all security events: directory bootstrap/session lifecycle, denied requests, real provider events and external audit remain uncovered. `grants_authority=false`; no export can authorize a workflow or verify professional claims. Identity resolution and detailed provenance inspection remain separate trusted operations. No download/public HTTP endpoint or external file transfer is introduced.

Fresh clones lack intentionally ignored CareerLab evaluator records. `scripts/prepare_evaluator_fixtures.py --materialize` reconstructs only missing evaluator answers for the eight frozen public development identities. It verifies the current manifest/configuration, exact observable membership and hashes, refuses changed existing answers, and writes only to the ignored evaluator directory. It never regenerates observable inputs or materializes validation/locked-test datasets. This is also the provisional CI setup step; evaluator records are not runtime input.

## Readiness and required evidence

All production/integration gates below are PENDING_CANONICAL_VALIDATION or PENDING_REAL_INTEGRATION. A research decision is not an implemented service.

| Area | Current boundary | Evidence needed before real use |
| --- | --- | --- |
| SSO/OIDC | Synthetic operator-issued sessions only; verified context/current membership | Reviewed provider/client, signed token validation and issuer/subject mapping; protected browser session/CSRF, key rotation, logout and cross-tenant attack tests |
| SCIM/provisioning | Trusted directory provisioning; bounded revisioned membership | Organization-authenticated provisioning, duplicate/out-of-order changes, deactivation, group-to-role policy, protected bootstrap and lifecycle audit |
| Tenant isolation | Application owner filters and separate directory contracts | Select separately credentialed databases or complete reviewed RLS; migration, pooled connection, forgotten-filter, backup and administrative access tests |
| Enterprise secrets | Ignored mounted rehearsal files; no model secret access | Platform secret manager, least-privilege access, encryption, rotation, revocation and recovery evidence; credential-free diagnostics |
| Workload identity | Trusted local composition and synthetic actors | Authenticated worker/service identity bound to organization/capability/resource; short-lived credentials and revocation tests |
| Enterprise connectors/NEXUS | Registered fake ports and proposed loopback NEXUS protocol | Actual repository/protocol, resource identity, OAuth scope/expiry, rate limits, idempotency retention, receipt reconciliation and protected audit |
| Policy governance | Revisioned organization/workspace policy, explicit activation and exact shared review | Approved policy authors/reviewers, mandatory dual control where selected, effective-time rules, emergency revocation and change history review |
| Process ingestion/intelligence | Bounded synthetic semantic events and deterministic discovery | Authenticated event sources, stable deduplication, quotas/backpressure, lateness/gap handling, independently designed evaluation and consent/employee privacy review |
| Retention/deletion | Accepted Career withdrawal/deletion controls; new synthetic metadata remains local | Retention schedule for workflow/teach/shadow/directory/audit, dependency-safe deletion, legal-hold policy, off-device backup erasure and deletion reconciliation |
| Privacy | Synthetic classification, capture consent harness, sensitive exclusions and content-free telemetry/export | Authorized real-data purpose/access, native capture consent, redaction adversarial tests, per-object visibility and tested privacy lifecycle |
| Audit/export | Append-oriented relational metadata, database role restrictions and bounded snapshot | Complete administrative/denial/provider lifecycle, protected evidence/identity mapping, retention, privileged access controls and tamper detection |
| Compliance evidence | Contracts, ADRs, failure/debt records and frozen accepted evaluations | Independently reviewed controls mapped to actual requirements, access review and incident/restore evidence; no compliance certification is claimed |
| Durable scaling | Bounded PostgreSQL engine; Temporal decision deferred | Supervised scheduler, load/fairness/recovery benchmark, long-lived behavior requirements and operations comparison |
| Untrusted execution | No arbitrary generated code; validated IR/fixed tools | Only if justified: separate secret-free sandbox and tested egress/resource/filesystem isolation; host-network Compose is insufficient |
| Deployment and operations | Private rehearsal configuration and telemetry contract | Native Docker/TLS/Collector/Terraform/hosted CI checks, protected monitoring, on-call ownership and deployment/rollback evidence |
| Backup/disaster recovery | Whole-database recovery procedure; owned disposable test databases | Encrypted off-device backup, isolated restore exercise, deletion/receipt reconciliation and measured RPO/RTO |
| SLO/SLA | Proposed measurement plan; no numerical service promise | Representative workload, error/latency definitions, observation period, restore/recovery measurements and agreed support responsibilities |

Synthetic labels cannot detect real personal/company prose. Workspace-wide sharing, admin self-review and one enabled principal per step remain explicit Phase-26 limits. Do not enable real data while treating the table above as an already satisfied checklist.

## Operational runbooks

For suspicious authority or an unexpected effect, stop the owned worker processes and disable the affected activation/organization capability through trusted operator control. There is no production daemon or global emergency-stop service in this build. Preserve content-free audit, exact workflow/approval/intent identities and provider receipt evidence in protected local storage. Remove sessions/member authority as appropriate, distinguish reserved from committed dispatch, and reconcile an unknown outcome without resending. A changed policy or backup cannot prove the original effect did not occur.

For database loss/outage, keep workers and connector dispatch disabled. Use the [Phase-25 backup/restore procedure](../phase-25/README.md#backup-and-recovery); restore into a separate isolated database, verify accepted Career migrations and all provisional schema guards, reconcile newer deletion/dispatch/receipt evidence, and require a reviewed recovery decision before execution. An old snapshot is insufficient to decide that an external write is safe to repeat. Archive corruption or uncertain ownership blocks cleanup/restart until resolved. Encrypted storage, restore exercises and RPO/RTO are pending.

For deployment/upgrade, use a dedicated synthetic environment, back up before explicit migration, review role grants and artifact/configuration identities, then run read-only readiness and synthetic journeys. Preserve a compatible application version and database backup; additive metadata migration is not an automatic downgrade/rollback guarantee. Do not expose the existing unauthenticated Career API through a public proxy. OVH, domain TLS and real accounts require their own validated contracts before activation.

For telemetry failure, execution remains governed by durable state/audit; bounded export failure must not retry a business effect or change its result. Preserve exporter failure counts without secret/content diagnostics. The manual OTLP JSON exporter is not a full tracing SDK or guaranteed audit sink. Collector interoperability and operational alert routing remain pending.

## Measurement strategy

Measure successful terminal outcomes, due-work age, claim/lease conflicts, database and connector latency, failures, human intervention and unknown-effect reconciliation. Report denominators and distinguish deliberate policy denials from service faults. Separate workflow completion from the completion of human work; elapsed wall time is not active time or ROI. Telemetry contains no employee ranking or productivity score.

An initial synthetic rehearsal should define its workload, latency/error targets and observation period before measurement. Only after representative personal/integration and recovery runs may an operator agree numerical SLOs, support response, RPO/RTO or an SLA. No office test timing is a capacity guarantee. Record incidents and validation failures without rewriting the frozen original Phase-6 NO-GO or claiming replay as new live/held-out accuracy.

The final checkpoint and reproduction instructions are in the [office handoff](../office-build/handoff.md). The first full regression attempt in this phase failed during collection because a new database test shared the accepted API test's filename. The new module was renamed, preserving both test bodies and the failed log; final results are recorded in the handoff and validation-debt register.
