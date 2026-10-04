# Phase 3: Persistence usage

This slice stores the accepted Career v0.1 contracts in local PostgreSQL. It adds transactional current state, exact provenance links, retained observation events and explicit deletion. Phase 0 (`4e06cc6`), Phase 1 (`5b6116a`) and Phase 2 (`fc6d396`) remain the binding baselines. Read [the design](design.md), [ADR 0004](../adr/0004-career-persistence.md) and [the acceptance record](acceptance-review.md) for decisions, checks and limits.

The public interface is one workspace-scoped `CareerStore` over a complete validated `CareerSnapshot`. There are no HTTP endpoints, authentication service, mutable ORM domain models, inference, connectors or workflow execution. A workspace ID supplies scope; the trusted caller supplies its attribution. This storage interface does not authenticate a user or authorize an external action.

## Important files

| File | Responsibility |
| --- | --- |
| `src/actual/persistence/database.py` | Lazy local engine configuration, private connection defaults and exact migration-head check |
| `src/actual/persistence/schema.py` | SQLAlchemy Core tables and relational constraints for the nine concrete record kinds |
| `src/actual/persistence/mapping.py` | Canonical payloads, full-record SHA-256, ordered relational projections and fail-closed snapshot reconstruction |
| `src/actual/persistence/event_mapping.py` | Resolve a new event against actual current records; reconstruct retained historical events without treating their refs as current |
| `src/actual/persistence/repository.py` | Workspace transaction, expected generation, atomic state/events, retained-event pruning and explicit deletion |
| `src/actual/persistence/errors.py` | Metadata-only persistence error categories |
| `migrations/versions/0001_career_persistence.py` | Frozen initial PostgreSQL DDL and database guard functions/triggers |
| `migrations/env.py`, `alembic.ini` | Explicit Alembic execution; no tracked URL and no automatic migration on store creation |
| `tests/persistence/` | Real PostgreSQL round trips, constraints, rollback, concurrency, migration/drift, retention and deletion checks |
| `scripts/verify_phase3.ps1` | Disposable PostgreSQL plus lint, format, typing and both supported Python test runs |

The accepted [Core usage](../phase-2/README.md) explains how to construct and resolve the domain records. Preserve that boundary before calling storage.

## Configure and migrate

Use Python 3.13 or 3.14 and the locked dependencies:

```powershell
uv sync --locked
```

Configure `ACTUAL_DATABASE_URL` privately in the process environment before migration or store creation. Its driver must be `postgresql+psycopg`, with explicit username, password and database. Allowed destinations are `localhost`, `127.0.0.1`, `::1` and the private Docker service name `postgres`; URL query parameters and libpq address/service override variables are rejected. Host/Docker DNS and the local operator remain trusted. Keep runtime database files and credentials outside Git and the source checkout. Never print the URL or put it into a shell command argument, tracked configuration or development prompt.

For a dedicated local database, the trusted schema owner runs:

```powershell
uv run --locked alembic upgrade head
uv run --locked alembic current
uv run --locked alembic check
```

`upgrade head` creates the schema through the committed migration. The engine factory and store do not create tables or migrate. The store requires exactly `0001_career_persistence` before operations. This runtime head check is not a complete drift audit: the migration tests also inspect the installed constraints, enabled triggers and frozen function bodies. Review schema changes as new migrations rather than editing an applied revision.

Use a separate DML role for runtime operations: schema usage; SELECT/INSERT/UPDATE/DELETE on current/event tables; SELECT/INSERT on `deletion_ledger`; and SELECT on `alembic_version`. Do not grant schema ownership, DDL or TRUNCATE. The tests exercise this boundary using a disposable role. This phase does not provision a production role or manage credentials. A PostgreSQL/host administrator can change or bypass database guards; those administrators are trusted by v0.1.

## Store and replace current state

This example receives an already constructed snapshot rather than inventing a profile or promoting a user claim:

```python
from actual.career.snapshot import CareerSnapshot
from actual.persistence.database import create_database_engine
from actual.persistence.repository import CareerStore


def store_initial_snapshot(snapshot: CareerSnapshot) -> bytes:
    engine = create_database_engine()  # Reads the private process environment.
    try:
        store = CareerStore(engine, snapshot.workspace_id)
        saved = store.save(snapshot, expected_generation=0)
        assert saved.generation == 1
        assert store.load().snapshot == snapshot
        return store.export()
    finally:
        engine.dispose()
```

Generation zero is bootstrap into an absent, non-deleted workspace. Bootstrap can import a valid historical application history; it does not assert that storage observed each historical transition. Subsequent `save` calls use the generation returned by `load` or `save`. Concurrent stale writers receive `ConflictError`. A byte-identical replacement retains its generation; a changed complete snapshot advances it once. Each changed domain record must advance its own revision by exactly one. Reordering an unchanged collection does not change those records' revisions.

Ordinary replacement cannot remove existing records, rewrite evidence/claim origin, change stable job/application identity, or rewrite application history. Update the whole dependency graph explicitly after changing evidence, claims or a job source: stale refs and stale reviews fail validation. Storage does not quietly repair support or preserve an old review over changed content. Workspace deletion is the explicit removal operation in this slice; individual-object deletion is deferred until its dependent-record policy is defined.

## State and observations commit together

For an existing workspace, provide matching `events=(event, ...)` to `save` when adding a job, creating an application's initial observation, appending an application transition, adding/changing a draft review or accepting a requirement review. A later new application begins with one initial history entry; full historical imports are confined to bootstrap. The store checks a required event against the new snapshot before accepting it, so redelivery of an old event cannot authorize a different transition or review.

The store accepts at most 128 events per transaction. It resolves exact current business/evidence refs, validates the payload against stored reviews/history, then writes state and observations in one transaction. A bad event or failed constraint rolls back the complete operation. `append_events` records observations without a state replacement when they describe current state.

Five accepted event payloads are supported: `job_added`, `requirements_reviewed`, `cv_recommended`, `draft_reviewed` and `application_status_recorded`. `fit_assessment_recorded` remains part of the accepted Phase-2 wire language, but storage rejects it with `UnsupportedEventError`: there is no accepted Assessment record to resolve. No placeholder assessment or evaluator answer is persisted.

Exact event or source-event redelivery is a no-op; the same identity with different semantic content or attribution is a conflict. This applies while the event is retained. Events are observations, and CV recommendations are recorded choices rather than a ranking algorithm. An accepted structured draft review cites exactly its qualifying bound evidence; it does not certify arbitrary prose or authorize submission.

`load_events` returns retained observations in deterministic occurrence-time/event-ID order. Historical refs retain the revision/digest originally observed and resolve stable object identity, rather than pretending old refs match today's changed record.

## Export, retention and deletion

`export` returns canonical snapshot bytes, including explicit wire versions and ordered collections. Export is personal data when its source is personal data; the caller owns private destination handling. This phase provides no backup scheduler or automatic cloud backup.

Current state replaces superseded content immediately. The store does not retain previous full job/profile/CV/draft payloads. Application observation history remains part of the current application contract, and retained Work Events preserve only their closed metadata/payloads and refs. `prune_events(now)` explicitly deletes events whose recording time is strictly older than 90 days. The exact boundary is retained. Database guards independently reject deletion of recent events according to the PostgreSQL clock. There is no background pruning scheduler; a future caller must invoke and verify this policy before admitting real data. Deduplication does not promise an indefinite delivery ledger after event retention expires.

`delete(deleted_at)` atomically writes a minimal immutable workspace/time tombstone and explicitly purges the workspace's current records, links and events. It does not affect other workspaces. Subsequent loads, saves and event replays fail closed. `deletion_record()` returns the tombstone and `apply_deletion_record(record)` applies a retained deletion to a restore destination.

The deletion ledger must be retained separately from any backup that predates deletion and applied **before any restored load or service access**. An in-database ledger alone cannot prevent resurrection from an older complete backup. The caller must preserve the latest deletion records privately, apply them to a restored database and expire/purge backups under the accepted [privacy policy](../phase-0/privacy.md). These methods establish a restoration precondition, not a backup product or a claim of physical erasure from an SSD or offline copies.

Before sensitive real records, verify private local storage, access configuration, deletion/retention invocation, protected exports/backups and owner-confirmed disk encryption. The acceptance checks use fabricated/synthetic records only and do not certify real-data deployment.

## Reproduce the acceptance checks

From the repository root on Windows, with Docker running and both installed interpreters:

```powershell
./scripts/verify_phase3.ps1
```

The script's defaults select `C:\Python314\python.exe` and `C:\Python313\python.exe`. Override `-PythonExecutables` with the installed paths on your machine; Phase-3 acceptance requires both supported Python branches. The script starts an isolated PostgreSQL container from an immutable image digest, generates temporary ignored credentials, publishes only an ephemeral loopback port and uses temporary database storage. It runs Ruff lint/format, strict mypy and the complete test suite under each selected interpreter. It checks the created container's identity/label before cleanup and restores the previous test environment variable. It does not manage another project's database.

For a manually provisioned **disposable** local PostgreSQL database, configure `ACTUAL_TEST_DATABASE_URL` privately and run `uv run --locked pytest -q --tb=short`. The fixtures require this variable and fail when it is absent; PostgreSQL tests do not silently skip or substitute SQLite. Each test uses a freshly generated, validated schema name, applies real Alembic migrations and removes only that schema. Some checks create an isolated runtime role, so the disposable test owner needs the corresponding administrative capability. Do not point acceptance tests at a runtime database.

For the observable CareerLab environment, explicitly select the new manifest:

```powershell
uv run --locked careerlab generate --manifest datasets/manifests/careerlab-persistence-env-v1.json
uv run --offline --locked careerlab verify --manifest datasets/manifests/careerlab-persistence-env-v1.json
```

The accepted Phase-1 and Phase-2 manifests remain historical baselines. The new manifest records changed project/lockfile hashes without changing observable inputs or evaluator record hashes. It inventories CareerLab/configuration rather than every persistence module; the Phase-3 commit, frozen migration, lockfile and acceptance record supply the additional identity. Observable compatibility uses cases 001–007. Case 008 remains an invalid transition. Requirements remain empty in that adapter because fixture extraction answers are evaluator-only; normalized requirements are exercised with separately fabricated contract records. Validation and locked-test datasets remain unmaterialized.

Phase 3 proves controlled durable contract behavior within the tested local PostgreSQL boundary. It does not prove document authenticity, professional truth beyond the structured contract, fit/recommendation quality, hiring outcomes, authenticated API access or external delivery. It stops before Phase 4.
