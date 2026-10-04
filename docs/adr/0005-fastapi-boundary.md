# ADR 0005: Synthetic-only Career intent API

Status: implemented within the user's Phase-4 request. Phases 0 (`4e06cc6`),
1 (`5b6116a`), 2 (`fc6d396`) and 3 (`d2a7544`) are accepted baselines. This
decision adds a bounded HTTP interface; it does not authorize Phase 5 or real-data API use.

## Decision

Expose `/api/v1` Career intent operations through thin FastAPI routes and a
framework-independent application service. Define one minimal aggregate repository
protocol and adapt the accepted PostgreSQL `CareerStore` at the composition root.
Preserve domain meaning, whole-snapshot invariants, persistence transaction ownership,
schema/migration history and provenance. Do not expose each relational table as CRUD.

Add manual job intake, self-reported claims, unreviewed evidence attachment, preparing
application creation and valid reported lifecycle transitions. A narrowly typed
bootstrap creates the first profile/company/job because the accepted aggregate is
nonempty. Expose scoped record/list/snapshot reads and retained events; generate job
and application observations internally rather than accepting arbitrary event requests.
Companies enter only with jobs, and supplied existing company attributes must match.

Use strict closed `actual-api-v1` intent/envelope records. Reuse safe accepted
`actual-core-v1` domain records in responses and structured assertions where justified;
never expose persistence projections or permit clients to choose authority fields.
Derive actor/workspace from server settings and classification from the restricted mode.
New claims remain self-reported and evidence unreviewed. Attachment to reviewed or
CV/draft-dependent claims fails until an explicit reconciliation workflow exists.

Mutation commands carry expected aggregate generation. One accepted repository save
commits state and required observations atomically; the API adds no intermediate
commits or automatic conflict retry. Responses follow commit, but lost network responses
remain uncertain outcomes for the caller. Stable resource IDs/generation inspection
support reconciliation; a generic HTTP idempotency subsystem is not added.

Pin FastAPI 0.142.2, Uvicorn 0.53.0 and development HTTPX2 2.13.1 after compatibility
review, and preserve existing dependency pins. FastAPI's mandatory OpenTelemetry API
dependency is not an ACTUAL exporter/instrumentation implementation. Generate local
OpenAPI JSON while disabling documentation UI/remote assets.

## Authentication scope resolution

Phase 0 requires local-owner authentication before personal API use. The Phase-4 user
request excludes authentication, while the accepted threat model explicitly allows
isolated unauthenticated synthetic development. Use only that mode: require explicit
`synthetic-development` settings and a dedicated configured synthetic workspace/actor;
reject personal/sensitive state and non-synthetic events. This is a bounded use of the
accepted exception, not replacement of the real-data access requirement.

The supported launcher binds `127.0.0.1`, disables proxy headers/access logging and
enforces loopback peer, exact Host/port, supplied Origin and Fetch Metadata at the
ASGI boundary. Bound JSON bytes, total body-read time and nesting; reject duplicate
keys, non-finite numbers, invalid Unicode and compressed input. Safe fixed-message
errors and server correlation IDs hide validation values, credentials and SQL details.
Structured request logs contain metadata only, with no durable log backend/exporter.

These checks do not authenticate a local caller or recognize real prose mislabeled
synthetic. The trusted database/OS operator must keep actual personal material outside
the exposed workspace. Real-data API access remains blocked until an accepted
local-owner access design and its evidence exist. No full authentication system,
cookies or CSRF-token mechanism is introduced in this synthetic phase.

## Alternatives and consequences

Full table CRUD would expose authority-bearing fields and create unsupported mutation
paths. Full snapshot import over HTTP would let callers manufacture history/review state.
Duplicating domain models as another semantic layer would invite drift. A DI framework
or session-scoped unit of work would duplicate transaction ownership already chosen
in Phase 3. Full authentication would contradict this request; serving real data without
it would contradict the accepted privacy/threat contract.

Use simple offset/limit lists with stable typed-ID ordering and generation per current
state page. A traversal can change between pages; clients compare generations and
restart. Event history uses a separate occurrence/event-ID-ordered read and makes no
atomic shared-generation claim. No generic query language or history pagination
infrastructure is introduced.

Liveness needs no database. Readiness checks database access, exact migration head and
configured synthetic state without auto-migration. Neither probe is a comprehensive
production health claim. Console-capture retention is operator-owned; no automatic
seven-day rotation or event-retention scheduler is added.

Job editing, verification/review, dependency reconciliation, assessments, material
generation/ranking, arbitrary event submission and HTTP deletion/export/import are
deferred. Reported application `reviewed` is tracking history, never content approval
or external delivery proof. Current-source references and internal deletion/retention
rules remain the accepted Phase-2/3 contracts.

## Verification and revisiting triggers

Require real FastAPI/API and real PostgreSQL checks on Python 3.13/3.14, all accepted
regressions and migration guards, invalid/provenance/lifecycle/conflict/rollback/security
cases, schema generation, lint/formatting/strict typing and preserved CareerLab hashes.
Record current dependency hashes in a new API environment manifest, preserving the
three accepted historical manifests. The [Phase-4 acceptance record](../phase-4/acceptance-review.md)
reports actual evidence; synthetic tests cannot establish hiring quality or real-data
security. Validation/locked-test cases remain unmaterialized.

Revisit this decision before real-data API use, an external write, new mutation/review
workflow, job/source reconciliation, authentication, larger-scale pagination or remote
deployment. Preserve server-derived authority, domain invariants and the rule that
user/model reports never automatically become verified evidence.
