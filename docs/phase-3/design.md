# Phase 3 design: transactional Career persistence

Status: implementation design under the user's Phase-3 request. Accepted baselines are Phase 0 `4e06cc6`, Phase 1 `5b6116a` and Phase 2 `fc6d396`. Passing results and the local source commit belong in [the acceptance record](acceptance-review.md).

Binding references are [the engineering contract](../phase-0/engineering-contract.md), [architecture](../phase-0/architecture.md), [data/workflow principles](../phase-0/data-and-workflows.md), [privacy](../phase-0/privacy.md), [evaluation strategy](../phase-0/evaluation-strategy.md) and [the Core invariants](../phase-2/design.md). [ADR 0004](../adr/0004-career-persistence.md) records this phase's storage decisions.

## Problem and smallest solution

Phase 2 validates a supplied snapshot but cannot establish a sequence of durable changes, prevent a stale concurrent write or atomically record the observation accompanying a state transition. Phase 3 adds one workspace-scoped aggregate store, SQLAlchemy Core mappings, explicit PostgreSQL constraints and a frozen Alembic migration. Accepted immutable domain records remain the source of meaning. There is no separate ORM entity model with another lifecycle or verification rule.

Persist only the concrete current Career records, their ordered dependencies, five resolvable Career observations and minimal deletion metadata. Complete snapshot replacement is intentional for the bounded single-user slice: it makes graph reconciliation and atomic validation visible without introducing a speculative repository framework, patch API or general unit-of-work abstraction. Serialization and full aggregate validation impose a bounded-size cost; this is not a high-volume history/event platform.

## Relational contract map

Every current record stores canonical `actual-core-v1` JSON text, its SHA-256 and explicitly derived relational identity/scope/revision/classification/ordering columns. Domain JSON preserves every accepted field and its exact serialization; relational keys expose the relationships PostgreSQL must enforce. Both representations are checked on read rather than assuming either alone is sufficient.

| Tables | Domain meaning and principal invariants |
| --- | --- |
| `career_workspaces` | Current snapshot classification/time/hash and positive storage generation; one aggregate per workspace |
| `object_identities` | Stable identity anchor for only the nine used kinds; exact current revision/classification/hash must match its concrete record |
| `companies`, `jobs` | Companies and original job sources; workspace-scoped company FK; stable job company/opportunity/posting/source identity |
| `profiles` | Exactly one profile per workspace; its canonical nested evidence/claims must equal their separately persisted ordered rows |
| `evidence`, `claims` | Scoped current evidence and claims; immutable source/origin attribution, current status and full dependency digest |
| `cvs`, `drafts` | Current structured materials with profile ownership and explicit claim links; reviews remain exact-content internal states |
| `applications` | Profile/job/canonical-opportunity identity, one intent per profile/opportunity, current state and append-only accepted observation history |
| `requirements` | Proposed normalized subject, priority/origin/source span in canonical payload; exact job revision/hash FK and one subject per canonical opportunity |
| `claim_evidence_links` | Ordered exact current evidence snapshots bound to a scoped claim |
| `cv_claim_links`, `draft_claim_links` | Ordered exact current claim snapshots; draft links also retain assertion position |
| `work_events` | Immutable retained event envelopes/payloads; unique event identity and nullable source-event identity per workspace/source |
| `event_object_refs`, `event_evidence_refs` | Ordered historical refs to stable identities; retain the observed revision/hash without a current-snapshot FK |
| `deletion_ledger` | Immutable workspace ID and deletion time only; independent of the deleted root and containing no source prose or content hash |

There are 18 domain/storage tables, plus Alembic's version table. `object_identities` is a constrained anchor for these concrete records, not an arbitrary enterprise object store. No Assessment, recruiter-outcome, evaluator-label, workflow-execution or model-response table is introduced.

Composite keys and foreign keys include workspace and, where required, profile. Exact dependency FKs include revision and digest; a valid ID alone cannot preserve withdrawn support. FKs use `NO ACTION`, deferred to the transaction boundary so a complete valid replacement can reconcile sources and dependents together. Collection-position uniqueness is also deferred for reorder operations; FK target uniqueness remains immediate. Application intent and normalized-subject uniqueness follow accepted Phase-2 constraints.

All required CHECK expressions use `IS TRUE` so SQL NULL cannot evade an invariant. PostgreSQL verifies closed ID/kind/classification/state values, version/metadata correspondence, bounded payloads and SHA-256 of the exact stored UTF-8 text. These checks deliberately do not reproduce every recursive domain validator in SQL. Loading still applies strict versioned contracts, exact canonical byte/hash comparison, contiguous order, whole-snapshot relationships and every derived projection.

## Identity, bytes, time and versions

`checksum(record)` is SHA-256 over the accepted `canonical_bytes(record)`, including its trailing newline. Stable IDs identify a record across changes; positive domain revisions identify its current replacement. A changed record advances exactly one revision; an unchanged record keeps its revision. Storage generation identifies the complete aggregate for optimistic concurrency and is independent of each domain revision.

The persistence business-object catalog uses the **full canonical record digest** for all nine kinds, including a draft or requirement's review/status. This is the explicit caller-supplied catalog convention allowed by Phase 2. A draft/requirement's own review still binds its own-review digest, which excludes its review to avoid a circular hash. Claim/evidence dependency helpers continue to use complete snapshot digests. Storage never substitutes a review-content hash for a current dependency hash.

Canonical exports preserve declared schema versions and collection order; PostgreSQL result ordering is never used implicitly. Stored timestamptz columns retain aware instants and connections use UTC. Domain validation rejects naive times and chronology violations. Snapshot time cannot move backwards. Events retain occurrence and recording time separately; retention uses recording time.

Unknown/missing wire versions fail closed. Runtime operations require the exact committed migration head, not an opportunistic migration or compatibility coercion. A future contract version requires an explicit contract/migration decision and backfill/compatibility tests. The frozen initial migration contains its own reviewed DDL and does not import today's `schema.metadata` to reconstruct old history.

## Transaction and concurrency behavior

Each operation begins one PostgreSQL transaction, verifies the migration head and takes a transaction-scoped advisory lock derived from workspace identity. This covers creation/deletion before a workspace row exists. Existing state is read under a row lock. Workspace-level serialization is simple and appropriate for the current single-user aggregate; it does not claim throughput for a multi-user system.

`save` validates the complete input, checks the caller's expected generation, compares old/new records, writes the reconciled current state, validates/appends observations and reloads the complete snapshot before commit. Constraint, event or reconstruction failure rolls back all changes. A no-op replacement retains storage generation. A stale expected generation conflicts even when the new snapshot's individual records look valid. Transaction timeout/error messages are sanitized and do not include source payloads or connection credentials.

Bootstrap with expected generation zero accepts a valid supplied history without inventing imported transition events. Later added jobs require an exact `job_added` event. Later new applications contain one initial preparing observation and its matching event; historical imports cannot bypass the subsequent-change boundary. An existing application's update appends at most one valid observation and requires its exact `application_status_recorded` event. The accepted lifecycle and external-manual tracking exception remain in the unchanged domain layer.

New/changed draft reviews and newly accepted requirement reviews require matching atomic observations. Event checks use the actual new records, reviews, actor/timestamps and history. Required semantic events are checked before duplicate handling, so a prior event cannot satisfy a new transition merely because its identity is retained. Ordinary replacement cannot remove existing provenance records or change stable job/application/source identity.

Cross-object source changes require explicit full reconciliation. Evidence withdrawal must update dependent claims, materials, reviews and full-snapshot refs as needed. Storage does not convert a user/AI claim into independently verified evidence, silently normalize a job or regenerate a review. It rejects an inconsistent graph instead.

## Observations and duplicate prevention

New event refs are resolved against the actual current catalog and scoped evidence. The event payload is also checked against actual state: requirement review decision/reviewer/time, material ownership, draft review/provenance or the application's exact last history entry. Accepted structured draft observations cite exactly the qualifying bound evidence from reviewed-supported claims that cover the proposed structured assertions. Unrelated, withdrawn or merely self-reported sources cannot satisfy that event gate. Arbitrary prose is not thereby certified.

The five supported event types are job intake, requirement review, CV recommendation, draft review and application status. `fit_assessment_recorded` is deliberately rejected because the accepted language names an Assessment reference but no Assessment contract exists. Persisting an unresolved or invented Assessment would weaken the cross-object boundary. This is a concrete scope limit, not permission to add Phase-6 analysis early.

Event IDs and source-event identities enforce durable duplicate/conflict handling while retained. Exact/semantically equivalent redelivery is a no-op even after the underlying current record changes; different content/attribution under the same identity conflicts. A batch failure cannot leave partial delivery. Historical reads reconstruct closed retained event payloads and exact projections; they do not revalidate old digests as if old events described today's record.

No event executes an action, verifies an external submission or grants authority. CV recommendations have no scoring/ranking implementation. Deletion removes events; the 90-day policy can expire source deduplication metadata. No indefinite action reservation or uncertain external-outcome policy is claimed, because external writes remain excluded.

## Database guard boundary

The initial migration installs seven guard functions and 29 triggers. Guards cover stable current-record identities/provenance and exact revisions, application history prefix preservation, stable identity-anchor updates, immutable observations/refs, tombstone-protected workspace creation/change, immutable tombstones and policy-restricted deletion. Current records cannot be deleted and reinserted to bypass their update guards without an explicit workspace tombstone. Recent event/ref deletion is blocked unless workspace deletion applies; expired observations can be pruned.

Dynamic ledger/event lookups are qualified with the trigger's actual schema and bound values. A temporary table with the same name cannot shadow a tombstone lookup. Runtime DML tests exercise these guards using a role without schema ownership, DDL or TRUNCATE. A database owner or host administrator can alter guards or write corrupt state; v0.1 trusts those administrators. Read-time contract/projection validation is additional integrity checking, not authentication or protection against a malicious owner editing both code and database.

The engine restricts local destinations and redirecting libpq configuration, hides SQL parameters, disables SQL echo, bounds connection/statement waits and uses an explicit search path. Caller-provided SQLAlchemy engines remain trusted capabilities. No runtime data, credential URL, profile text or raw model payload belongs in tracked configuration or exception output.

## Privacy, retention and restore

Current replacements immediately discard superseded full source/material payloads rather than retaining a revision archive. This minimizes content sooner than the accepted maximum retention for superseded generated drafts. Current application history preserves its accepted observation sequence. Closed Work Events contain metadata/refs rather than copies of raw job/CV/profile prose.

Explicit `prune_events(now)` removes observations strictly older than 90 days by recording time, with PostgreSQL independently enforcing age against its own clock. There is no scheduler in this phase. A later runtime must invoke and verify retention before admitting real data; a caller cannot claim automatic age-based purge from the existence of this method.

Whole-workspace deletion writes an immutable minimal tombstone first, then explicitly purges all content and dependent links/events in one transaction. A no-cascade policy avoids hidden provenance deletion. Repeating deletion retains the original tombstone. Individual-object deletion is deferred until a policy defines its dependent graph, history and restore semantics.

Exported deletion records must be retained separately from older backups and applied before any restored reads/access. An older full database backup can lack a later tombstone; the in-database ledger alone cannot protect that restore. The tested interface applies a retained record to a separately restored schema and prevents replay of its old snapshot/events. It does not implement backup scheduling, durable off-database ledger distribution, disk encryption or physical secure erasure. Real-data deployment remains subject to the accepted private-storage/access/retention/deletion/backup prerequisites.

## CareerLab and evaluation boundaries

Persistence imports Career/Core/Profile contracts, not CareerLab authoring or evaluator modules. Compatibility tests obtain observable inputs and map the seven valid public worlds through the accepted bridge. The invalid eighth transition is rejected. Evaluator-only normalized requirements, rubric labels and recruiter outcomes never become runtime persistence fields. Normalized requirement persistence tests construct separate fabricated contracts with source spans/reviews; they do not import extraction answers.

The accepted fixture source, eight input files and Phase-1/Phase-2 manifests remain unchanged. `careerlab-persistence-env-v1.json` separately records the project/lockfile dependency change while preserving all record hashes. No validation or locked-test set is generated, inspected or tuned against. These shared-ancestry public fixtures are development compatibility checks, not independent held-out evidence of career intelligence.

## Acceptance gates

Acceptance requires locked dependency compatibility and the complete tests on Python 3.13/3.14 against real PostgreSQL, with no missing-database skips or SQLite substitution. Exercise fresh migration, repeat upgrade, disposable downgrade/re-upgrade, metadata drift and explicit installed trigger/function checks. No artificial second migration is added solely to inflate migration coverage.

Required integrity evidence includes exact canonical/domain round trips, provenance preservation, typed invalid references/status/version/shape rejection, stale revision/generation conflicts, cross-workspace isolation, source withdrawal/reconciliation, atomic state/event rollback, application history and matching observations, source/event duplicate/conflict behavior and concurrent winners. Required privacy evidence includes parameter-safe configuration/errors, DML guard behavior, retention boundary and deletion/restore replay prevention.

Run Ruff lint/format and strict mypy, verify the separate current CareerLab manifest, audit preservation of accepted code/data and inspect the focused staged diff for private/excluded artifacts. Record actual commands/results and known limits before the local commit. Passing these gates establishes the bounded persistence slice, not production security, model quality, hiring prediction or Phase-4 authorization.
