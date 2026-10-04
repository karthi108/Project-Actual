# Phase 3 acceptance evidence: Persistence

Status: Phase-3 engineering gates satisfied on 2026-10-04. User acceptance is separate. Binding accepted milestones are Phase 0 `4e06cc6`, Phase 1 `5b6116a` and Phase 2 `fc6d396`. The focused Phase-3 source commit is identified in Git history rather than embedded in its own content. No Phase-4 work is included.

## Delivered boundary

The [design](design.md), [usage](README.md) and [ADR 0004](../adr/0004-career-persistence.md) describe one workspace-scoped `CareerStore` over the accepted immutable `CareerSnapshot`. SQLAlchemy Core maps nine concrete record kinds to relational current state and ordered provenance links. Canonical versioned payloads preserve domain information; reads revalidate domain relationships, hashes, order and every relational projection. There are 18 tables plus Alembic's version table, seven guard functions and 29 triggers in a frozen initial migration.

Transactions combine complete state replacement with required observations. Expected aggregate generation, workspace advisory/row locks and exact next record revisions prevent stale overwrites. Application history preserves its prior prefix and appends one valid observation with its matching event. Evidence/claim origin and stable job/application identities cannot be rewritten. Current dependency hashes and explicit reconciliation prevent a withdrawn or changed source from quietly preserving reviewed support.

Five Career observations persist against actual records and reviews. `fit_assessment_recorded` fails closed because Phase 2 defines its wire payload but no Assessment entity. This concrete contract gap is documented without changing accepted Core contracts or inventing a placeholder. Source-event duplicates are suppressed while retained; conflicting identity reuse and invalid batches fail atomically.

Workspace deletion explicitly purges source/current/link/event content and retains only an immutable workspace/time tombstone. Retention pruning is explicit, bounded by recorded time and the PostgreSQL clock. A separately preserved deletion record must be applied before restored reads; an older full backup without that record is not protected by an in-database ledger alone.

## Design challenges resolved

Code review and real PostgreSQL testing exposed concrete failure paths that were corrected before the final matrix:

- A current-record DELETE followed by INSERT could bypass update-only provenance/history guards. Protected DELETE now requires an explicit workspace tombstone; ordinary replacement still cannot remove records.
- Trigger lookups must use their actual schema. Ledger/event lookups are schema-qualified with bound values, and a temporary ledger shadow cannot resurrect a deleted workspace.
- An old duplicate status event cannot authorize a new transition. Required semantic observations are validated against the replacement snapshot before duplicate handling.
- An accepted draft event must cite its exact qualifying bound positive evidence. Unrelated reviewed evidence, unreviewed sources and extraneous references are rejected, with full rollback of the attempted review.
- A valid historical application may be bootstrapped, but a later ordinary update cannot use that import exception to bypass intermediate observation requirements.
- PostgreSQL treats a NULL CHECK result as passing unless the expression requires truth. Required checks use `IS TRUE`; complete domain and projection validation remains necessary on read.
- Alembic's normal drift comparison does not cover every database behavior. Tests additionally inspect selected constraints, all enabled triggers and the exact installed bodies/security settings of all seven frozen guard functions.
- Accepted CareerLab manifests bind the old project/lockfile hashes. Both historical manifests were preserved, and a separate persistence-environment manifest records the dependency change with identical fixture membership and all 16 record hashes.

Initial test/type/lint failures were resolved before the final checks. Two added-test expectations were corrected to follow accepted behavior: invalid source dependencies fail during validated construction, and a synthetic profile can retain a `project_artifact` source kind. Neither correction weakened the persistence or Core contracts. These are assistant engineering reviews, not independent validation of real documents or employers.

## Checks actually run

Host: Windows/PowerShell, uv 0.11.7, Python 3.14.7 and Python 3.13.1. PostgreSQL 18.6 ran in an isolated official Linux container published only on an ephemeral loopback port. Credentials were generated outside tracked configuration and were not printed. Each integration test migrated its own validated disposable schema. DML-role tests used a separately created role without ownership, DDL or TRUNCATE privileges.

The final `scripts/verify_phase3.ps1` run started a fresh temporary database, ran all static checks and both complete suites, then removed its own identity/label-checked container and ignored credential file. Its storage was temporary. The separate database used during implementation and CLI/example verification was also removed after those checks. Other project containers were left untouched.

| Command/check | Final result |
| --- | --- |
| Locked dependency resolution/sync | SQLAlchemy 2.1.3, Alembic 1.20.0, psycopg/psycopg-binary 3.3.6; 25 locked packages installed under both supported interpreters |
| `uv run --locked ruff check src tests migrations` | All checks passed |
| `uv run --locked ruff format --check src tests migrations` | 48 Python files already formatted |
| `uv run --locked mypy` | Strict typing passed for 33 source/migration files |
| Full locked suite on Python 3.14.7 against PostgreSQL | **620 passed**, 124.29 seconds |
| Full locked suite on Python 3.13.1 against PostgreSQL | **620 passed**, 120.47 seconds |
| Environment-configured `alembic upgrade head`, repeated upgrade, `alembic current`, `alembic check` on a clean disposable database | Bootstrap/repeat succeeded; head `0001_career_persistence`; no new upgrade operations detected |
| `alembic heads`, offline upgrade and explicit revision-to-base downgrade compilation | One ordered initial head; both PostgreSQL SQL directions compiled |
| Fresh/repeated upgrade, disposable downgrade/re-upgrade, metadata drift and installed-guard checks | Passed in both complete suites |
| Public observable CareerLab ↔ domain ↔ PostgreSQL ↔ domain | All seven valid cases preserved exact canonical bytes on both interpreters; the existing invalid-transition rejection remained passing |
| Normalized requirements, review events, ordered CV recommendations, draft source rejection, full source withdrawal reconciliation | Real PostgreSQL positive/negative tests passed; no evaluator extraction answers used |
| Invalid FKs/closed values/revisions, immutable provenance/history, stale generations, corruption detection and transaction rollback | Passed; failures left no partial state/event writes |
| Concurrent state updates and source delivery | One state winner; retained source delivery durably deduplicated |
| DML-role guards, temporary-ledger shadow, 90-day boundary, workspace purge and separately retained deletion-record restore | Passed; unrelated workspace content preserved |
| Documented initial-store Python example | Executed against the environment-configured migrated PostgreSQL database; exact canonical export |
| Fresh Python 3.13 process reading the Python 3.14 example's persisted record | Exact same canonical bytes and SHA-256 |
| `careerlab generate --manifest datasets/manifests/careerlab-persistence-env-v1.json` and offline verify | Eight public cases validated; current environment identity recorded |
| Offline verify with an isolated locked Python 3.13 environment | Same manifest/source/record identity verified after compatible wheels were cached |
| Accepted baseline audit | All 67 files outside four authorized root/configuration edits match accepted Git blobs; all 16 input/evaluator hashes remain identical |
| Runtime source import audit | Persistence depends on Career/Core/Profile and storage libraries; no evaluator/authoring/oracle imports or excluded infrastructure |
| Documentation links, `git diff --check`, staged equivalent and source/artifact audit | Targets resolve; no whitespace errors; manifest matches staged source/input bytes; no private/evaluator/held-out files staged |

The complete suites contain the unchanged 492 Phase-1/Phase-2 checks and 128 Phase-3 checks. Of the latter, 83 use real PostgreSQL and 45 validate engine/configuration/schema-head failure boundaries. No test was skipped. Integration tests fail when their explicit PostgreSQL configuration is missing; SQLite is not used as a substitute.

## Reproducibility identity

| Identity | Value |
| --- | --- |
| Domain wire version | `actual-core-v1` |
| Migration head | `0001_career_persistence` |
| Frozen migration file SHA-256 | `b5c452fd509dc70134c1a0d7c362c152ea7c5125179ecb4927249d6d51dbd0d1` |
| PostgreSQL official image | `postgres@sha256:5a5a84b19854a9ffaa54082c166ff4ec27473a361e496e5ea167f298f2da9722` |
| CareerLab dataset/generator | `careerlab-development-v1` / `careerlab-generator-v1` |
| CareerLab input/oracle/rubric | `careerlab-input-v1` / `careerlab-oracle-v1` / `careerlab-support-v1` |
| CareerLab seed | `20261004` |
| Preserved Phase-1 dataset identity | `a7d59618b371c0e51a5d6b09798eec1b48e82dbe37c5fe307a20f1bd0e8f40a4` |
| Preserved Phase-2 environment identity | `c663a2591dbcc9270d027fc55c863c700eeabc40bce8ff3830d0bd1de53f01d0` |
| Phase-3 environment dataset identity | `415247bee9fdff3c495b85703f574bd0565d109322e47ea25d5eaf3f0edd8c06` |
| Phase-3 manifest file SHA-256 | `6cab2c5ebdbbe5459dea7228d50841e74988440db2bb08a6a300385a8c93d88e` |
| Persisted case-001 example canonical SHA-256 on both Python versions | `548bb069dcbd41242dc5613dd62bd19d69b61f418f5e0e0dcda481a906fec443` |

The example uses `generate_inputs(20261004)[0]`, the unchanged observable bridge, workspace `workspace_` followed by 32 `1` digits and actor `actor_` followed by 32 `2` digits. Its export includes the accepted trailing LF. This is a public compatibility check, not a held-out evaluation result.

The new [environment manifest](../../datasets/manifests/careerlab-persistence-env-v1.json) changes only project/lockfile source hashes and the resulting aggregate identity. The [Phase-1](../../datasets/manifests/careerlab-dev-v1.json) and [Phase-2](../../datasets/manifests/careerlab-core-env-v1.json) manifests and all accepted domain/CareerLab code, tests, inputs and historical documentation remain unchanged. Git LF normalization was used for the source preservation audit. The current environment manifest inventories CareerLab/configuration rather than every persistence file; Git, the frozen migration and `uv.lock` identify this additional source.

## Limits and deferred work

This phase proves durable, deterministic contract behavior and controlled transaction failure handling within the tested local PostgreSQL boundary. It does not prove source authenticity, unrestricted prose truth, extraction/recommendation quality, hiring outcomes, authenticated user access or production deployment readiness. Synthetic reviews remain fixture assumptions. Public fixtures share ancestry; validation and locked-test datasets remain unmaterialized and were not inspected or tuned against.

Workspace/actor attribution and supplied engines are trusted caller inputs. Parameter-safe storage and DML guards do not protect against a database/host administrator who owns the schema, alters triggers or changes application code. Runtime role/secret provisioning, schema drift repair, backup scheduling, durable off-database deletion-ledger retention, disk encryption and automatic retention invocation are deployment/application responsibilities, not delivered subsystems. Sensitive real data remains gated by the accepted privacy prerequisites.

Current payloads have no full revision archive. Historical events retain old digests as observations, not current support. Deduplication expires with event retention. Only whole-workspace deletion is supported; individual-object deletion needs an accepted dependency/history policy. No pagination or enterprise/high-volume performance claim is introduced. Downgrade was tested only on a disposable empty schema and is destructive, not a safe real-data recovery policy. There is one initial migration; an invented second revision is not evidence of a future upgrade design.

Assessment persistence, APIs, UI, inference, connectors, browser automation, voice, workflow execution, NEXUS, Redis, Temporal and cloud deployment remain outside this slice. Phase 4 requires a new user request.
