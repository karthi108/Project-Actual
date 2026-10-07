# ADR 0016 — Retain the bounded PostgreSQL runtime until a measured requirement changes it

Date: 2026-10-07. Status: provisional research decision; scaling and canonical acceptance pending.

## Problem and simplest solution

ACTUAL already persists a validated DAG, fenced lease, one bounded step per tick, durable waits, exact approvals, effect intents and dead letters. The office examples need this small engine. They do not demonstrate large queues, high throughput, multi-region recovery or a need for a new orchestration service. Retain PostgreSQL as the authority and the existing runtime; do not add Temporal, Redis, Kubernetes or vector storage during Phase 27.

The implemented IR limits remain 64 steps, 192 edges, 320 step executions, 16 declared model calls and a one-day run budget. AI declarations remain unavailable to workflow execution. There is no production scheduler or supervisor. Lease fencing and deterministic tests demonstrate local progress rules, not a distributed availability or throughput claim.

## Temporal evaluation

Temporal's durable event history and worker replay provide an orchestration model worth evaluating when long-running coordination exceeds this engine's scope. Its workflow code must obey deterministic execution constraints; adopting it would require new operational and versioning decisions. [Temporal workflow execution](https://docs.temporal.io/workflow-execution)

Revisit when an authorized use case requires long-lived workflows beyond current budgets, parallel child work, a measured queue/service deadline that the bounded engine cannot meet, or recovery/versioning complexity that repeatedly causes incidents. First write the failing requirement and reproduce it synthetically. Compare the current engine and an isolated Temporal spike against the same restart, signal/human-wait, version upgrade, cancellation, database outage and ambiguous-provider scenarios. Measure developer/operations burden, latency and recovery effort. No service or dependency is installed solely for this comparison document.

A replacement must preserve business-action identity across workflow versions, principal/resource authority, exact reviewed arguments and policy, current revocation checks, separate durable dispatch/receipt evidence and conservative unknown-outcome recovery. An orchestration retry must not resend an uncertain external action. Temporal cannot substitute for provider idempotency/reconciliation or authenticate approval. Migration would require its own ADR and rollback plan before moving accepted storage or audit.

## Scaling and ingestion plan

The next justified improvement is a supervised, bounded scheduler around the existing store. Queue selection, fairness, stale lease recovery, per-organization limits and shutdown must be measured before multiple workers are enabled. Add a due-work index or a queue only when query plans/load show the need; never bypass the current fenced claim/finish operation.

For a future ingestion pilot, authenticate the source, derive tenant/principal server-side and validate a bounded versioned semantic event. Deduplicate by organization/source/stable event identity and reject changed duplicates. Enforce payload/time/retention quotas, quarantine malformed batches and record gaps. Provider lineage, evaluator labels and future outcomes remain outside observable inputs. The existing Teach/WorkLab fixtures are public development examples and cannot establish enterprise process coverage or independent held-out accuracy.

A benchmark must include queue depth/age, due-to-claim delay, lease conflicts, database latency, terminal outcomes, intervention, memory and restore behavior, across several explicitly recorded synthetic load levels. Results need hardware/configuration/sample sizes and failure traces. No throughput capacity, savings or SLA is claimed in this checkpoint.

## Optional components and execution isolation

Redis remains deferred until a measured cache, rate-limit or coordination requirement exists. Any future cache is disposable and cannot hold the only approval/intent authority. Semantic retrieval is deferred until a concrete use case and evaluated retrieval baseline exist; evaluate PostgreSQL plus pgvector first, without treating retrieved text as evidence or authority.

Workflow IR and fixed typed handlers remain the execution boundary. Arbitrary generated Python/shell is unsupported. If a later task truly needs it, use a separately reviewed sandbox without secrets, host mounts, Docker socket or default network, with a non-root user, read-only inputs and CPU/RAM/PID/time/output limits. Phase-25 host-network containers are for trusted application code and do not meet this sandbox requirement.

## Consequences

The current design is understandable and has fewer moving parts, but deliberately lacks enterprise scheduling, long-lived workflow features and demonstrated capacity. [Operational research and gates](../phase-27/README.md) record those limits. Defer technology adoption until a concrete failing requirement makes its benefit reviewable.
