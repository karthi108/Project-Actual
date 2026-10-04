# Phase 4 acceptance evidence: FastAPI Boundary

Status: Phase-4 engineering gates satisfied on 2026-10-04. User acceptance is separate.
Binding accepted milestones are Phase 0 `4e06cc6`, Phase 1 `5b6116a`, Phase 2
`fc6d396` and Phase 3 `d2a7544`. The focused source commit is identified in Git
history rather than embedded in its own content. No Phase-5 implementation is included.

## Delivered boundary

The [usage](README.md), [design](design.md) and [ADR 0005](../adr/0005-fastapi-boundary.md)
describe 13 Career HTTP operations, two health operations and local generated OpenAPI.
Commands initialize a synthetic career, add a manual job, record a self-reported claim,
attach unreviewed evidence, start an application or append a valid reported status.
Scoped reads cover jobs, profile/evidence, application histories, accepted CV metadata
and retained events. Companies enter only through manual jobs. No table CRUD,
arbitrary snapshot import, generic event submission or authority-setting request exists.

`actual-api-v1` intent/envelope models are strict, closed and versioned. Safe embedded
domain records retain `actual-core-v1`; ORM models are not HTTP contracts.
Application commands/service/ports/errors own intent handling independently of
FastAPI and SQLAlchemy. The HTTP app delegates mutations to that service; wiring
adapts the accepted `CareerStore`. Database access directly in a handler is limited
to the infrastructure readiness probe, never domain mutation.

One accepted repository save owns the state/event transaction and final expected-
generation conflict check. Job and application observations are generated internally.
Claims keep server-derived user-report attribution and self-reported status. Evidence
preserves declared source provenance and remains unreviewed. Reviewed or CV/draft-
dependent claims require a future explicit reconciliation use case before attachment.
Reported application `reviewed` is not a content approval or external submission.

The supported launcher binds only `127.0.0.1`, disables proxy headers/access logs and
requires explicit synthetic-development settings. Request boundaries enforce direct
loopback peer, exact local Host/port and supplied Origin/Fetch Metadata; bounded
strict JSON; safe fixed-message errors; server request IDs; no-store/nosniff headers;
and structured metadata-only console logs. Liveness avoids PostgreSQL; readiness
requires reachable PostgreSQL, the exact accepted migration head and safe configured
workspace state. Startup performs no schema mutation or migration.

## Challenges resolved

- Phase 0 gates real personal API access on local-owner controls; this request excludes
  authentication. The accepted threat model permits isolated unauthenticated synthetic
  development, which is the only implemented mode. Known personal/sensitive snapshots
  and non-synthetic events fail closed. Real-data access remains gated.
- Updating a claim's evidence would invalidate existing exact review/material references.
  Attachment rejects those dependencies instead of silently repairing or rewriting them.
- Generation checked only during a read would permit lost updates. The existing store
  remains the authoritative transaction/concurrency gate; simultaneous HTTP writers
  demonstrate one winner and one conflict.
- A successful commit followed by a lost response is an uncertain delivery result.
  Resource IDs and state/generation reads support inspection before retry; no automatic
  retries, HTTP idempotency ledger or exactly-once guarantee are claimed.
- Safe HTTP exception mapping initially omitted the required `Allow` header on 405.
  The mapper now retains it, and the unsupported-method test checks it.
- Combined regression collection exposed a collision between a new `conftest` module
  and an accepted persistence-test import. New application fixtures were moved into
  their test file; accepted tests stayed unchanged. Collection and both full suites
  then passed. Focused checks alone were not treated as acceptance.
- Starlette's current test client uses HTTPX2; its stable 2.13.1 patch is pinned.
  FastAPI's required OpenTelemetry API package adds no ACTUAL tracing SDK, exporter
  or instrumentation. Swagger/ReDoc UI and remote documentation assets are disabled.

## Checks actually run

Host: Windows/PowerShell, uv 0.11.7, Python 3.14.7 and 3.13.1. Real PostgreSQL 18.6
ran in disposable official Linux containers using the accepted immutable image
`postgres@sha256:5a5a84b19854a9ffaa54082c166ff4ec27473a361e496e5ea167f298f2da9722`.
Ports were published only on loopback; storage was temporary. Credentials stayed
in ignored private configuration and were not printed. Integration tests migrated
separate disposable schemas, including the accepted DML-role/guard checks.

`scripts/verify_phase4.ps1` reuses the unchanged accepted Phase-3 harness with current
testpaths/dependencies. Its final run completed all static checks and both full suites,
then removed its own identity/label-checked container and credential file. The separately
owned database and private files used for implementation, migration commands and live
HTTP verification were also removed. The unrelated existing project container was
left untouched. The live API child process was stopped.

| Command/check | Final result |
| --- | --- |
| Locked resolution/sync and interpreter package audit | FastAPI 0.142.2, Uvicorn 0.53.0, Starlette 1.7.0, HTTPX2/HTTPcore2 2.13.1; all accepted direct pins preserved; 38 packages locked, 37 installed on each Windows interpreter |
| `uv run --locked ruff check src tests migrations` | All checks passed |
| `uv run --locked ruff format --check src tests migrations` | 68 Python files already formatted |
| `uv run --locked mypy` | Strict typing passed for 45 source/migration files |
| Full locked suite on Python 3.14.7 against real PostgreSQL | **770 passed**, 179.82 seconds |
| Full locked suite on Python 3.13.1 against real PostgreSQL | **770 passed**, 134.09 seconds |
| Actual Uvicorn TCP process on Python 3.14.7 | Started cleanly; exact child-process ownership and sole `127.0.0.1` listening interface checked |
| Live HTTP health/OpenAPI/documented example | Live/ready returned 200 against migrated PostgreSQL; schema served; actual documented PowerShell initialization created generation 1; snapshot and one generated event read back; foreign Origin rejected with 403 |
| Actual launcher console audit | Seven structured metadata records only; no body, access-log, SQL or credential output |
| Generated OpenAPI on both interpreters | 12 documented paths / 15 operations; identical canonical JSON hash recorded below |
| HTTP and transport invalid cases | Wrong destination/origin, malformed/duplicate/non-finite/invalid-Unicode/deep JSON, byte/time limits, unexpected authority fields, unsupported methods and safe failure envelopes passed |
| Provenance and lifecycle | User claims remained self-reported, evidence unreviewed; server actor scope and source provenance preserved; invalid transitions/review dependencies rejected |
| Real PostgreSQL HTTP rollback | Forced deferred failure at COMMIT returned 409; neither replacement state nor event persisted |
| Concurrent real PostgreSQL HTTP mutation | Both requests read generation 1; exactly one 201 and one 409; generation 2 contained only the winning job/event |
| Privacy/deletion boundaries | Personal/sensitive/deleted configured workspaces refused; non-synthetic retained events refused; safe readiness failure |
| Observable CareerLab → accepted Core → store → API | Public valid snapshot retained exact canonical Core content, including CV metadata and provenance; evaluator information was never an API input |
| Repeated `alembic upgrade head`, `current`, `check`, `heads` | Exact `0001_career_persistence` head; no new upgrade operations |
| Offline upgrade and explicit head-to-base downgrade SQL compilation | Both PostgreSQL directions compiled |
| Existing migration bootstrap/repeat/downgrade/re-upgrade/drift/installed-guard tests | Passed on both interpreters |
| CareerLab generation and offline verification on both interpreters | Eight public development cases validated; same environment identity; validation/locked test unmaterialized |
| Accepted baseline audit | All 88 files outside four authorized root/configuration edits retain accepted Git content; all 16 input/oracle hashes unchanged |
| Runtime import/source audit | Domain excludes HTTP/storage dependencies; application excludes HTTP/storage frameworks; API/application/persistence exclude CareerLab authoring/evaluator modules |
| Documentation links, PowerShell syntax, whitespace and staged artifact audit | Resolved targets; no whitespace/syntax errors; current manifest matches staged source/input content; no private/evaluator/held-out data staged |

The full suites include all 620 unchanged accepted checks plus 70 application checks,
55 API/transport/configuration/architecture checks and 25 real-PostgreSQL HTTP checks.
No test was skipped. In-memory application-port tests do not substitute for the
database tests; no SQLite substitute was used. The suite fails without an explicitly
configured disposable PostgreSQL database.

## Reproducibility and preservation

The [API environment manifest](../../datasets/manifests/careerlab-api-env-v1.json)
has dataset identity:

```text
f9ad49deadb9d20c65d56334c6b809cfc496334a94bc044cd0e90472316cb5fc
```

It records the current project/lock hashes while preserving all eight records,
lineage/category metadata and sixteen input/oracle hashes from Phase 1. The three
accepted historical manifests, public inputs, domain source/tests, migrations,
prior documentation and verification script retain accepted Git content. One existing
profile initializer has local CRLF versus baseline LF; normalized Git content is
identical. No snapshot expectation, evaluator answer or fixture was changed to pass
a test. No individual validation or locked-test case was generated, inspected or tuned.

The generated OpenAPI hash is identical on Python 3.13.1 and 3.14.7:

```text
606138744ce4e57d7b1d953fcded5ef97f602b15feea1ea1588f956654de7980
```

This hashes UTF-8 JSON with sorted keys, compact separators, `ensure_ascii=False`
and no final newline. It is an observed schema identity, not a new multi-version
compatibility framework or canonical domain-export format.

## Known limitations and next-phase boundary

These are controlled software-boundary tests, not evidence of real hiring quality,
truth of documents, end-to-end Career assistance, security certification or load
resilience. The eight shared-ancestry development cases are not independent held-out
validation. No fit extraction, ranking, assessment entity, material editing/generation,
verification/review, HTTP deletion/export/import or company-management API is added.

Loopback/Host/Origin restrictions and server attribution do not authenticate a local
caller. Synthetic labels cannot recognize actual personal prose mislabeled synthetic.
Trusted OS/database operation and isolated fabricated input remain prerequisites;
real-data API access requires later accepted owner controls. There are no cookies,
sessions, login, production authentication or SSO.

One save is atomic, but HTTP response delivery is not exactly-once. Offset pages may
change between requests; clients compare current-state generations and restart.
Events use a separate retained-history read without an atomic shared-generation promise.
Current aggregate reads/replacement are bounded by existing domain/storage contracts,
not optimized or benchmarked for large histories. Readiness checks the exact head and
configured state, not every installed DDL definition or full production health.

Source paths/URLs are opaque metadata and never fetched. Console capture retention
is operator-owned; the seven-day diagnostic default and event pruning are not automated.
Accepted internal deletion/retention primitives remain available without an HTTP
endpoint or scheduler. There is no AI/provider runtime, frontend, connector, browser
automation, external write, workflow execution, NEXUS, Redis, Temporal, cloud deployment
or telemetry exporter. Phase 5 requires a new user request.
