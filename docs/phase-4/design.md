# Phase 4 design: a bounded synthetic Career API

Status: implementation design under the user's Phase-4 request. Accepted baselines
are Phase 0 `4e06cc6`, Phase 1 `5b6116a`, Phase 2 `fc6d396` and Phase 3 `d2a7544`.
The [acceptance record](acceptance-review.md) records executed checks separately.
Binding references include [architecture](../phase-0/architecture.md),
[threat model](../phase-0/threat-model.md), [privacy](../phase-0/privacy.md),
[Core invariants](../phase-2/design.md), [persistence design](../phase-3/design.md)
and [ADR 0005](../adr/0005-fastapi-boundary.md).

## Problem and minimum boundary

Accepted contracts and persistence can store a valid Career aggregate, but they do
not give an HTTP caller bounded intent commands, safe error semantics or a configured
owner boundary. Phase 4 adds thin FastAPI routes, a framework-independent Career
service and the exact aggregate repository port it needs. It preserves Phase-3
transactions, migrations and domain serialization.

The exposed use cases are manual job intake, self-reported claim creation, unreviewed
evidence attachment and reported application lifecycle tracking, plus scoped reads
and health. A bootstrap command creates the first complete valid snapshot rather
than loosening the accepted nonempty Career invariants. Existing CV/requirements/draft
metadata can be read through the snapshot; corresponding mutation/review workflows
are deferred until their accepted phases.

There is no automatic table-to-CRUD mapping. Companies enter only with manual jobs;
an existing company ID is reusable only with identical name/context. Job edits would
invalidate pinned requirement references and need explicit reconciliation, so no edit
endpoint is added. Arbitrary snapshot write/import, deletion, review/verification,
assessment, material generation and direct event submission remain internal or absent.

## Dependencies and important files

```text
api/app.py: typed routes and error mapping
        ↓
application/service.py: closed Career intent use cases
        ↓
career/, profile/, core/: accepted immutable meaning and invariants
application/ports.py: aggregate load/save/event-read protocol
        ↓
api/wiring.py: StoreAdapter → accepted persistence/CareerStore
        ↓
PostgreSQL: Phase-3 constraints and one transactional save
```

| File | Responsibility |
| --- | --- |
| `application/commands.py` | Closed immutable intent DTOs; omit owner, classification, review and history authority |
| `application/service.py` | Domain construction, reference resolution, conflicts, synthetic gate and generated observations |
| `application/ports.py` | Only the three repository operations these use cases need; no generic unit of work |
| `application/errors.py` | Safe semantic failure codes independent of HTTP |
| `api/contracts.py` | HTTP response, pagination, health and error envelopes |
| `api/config.py` | Explicit synthetic mode, configured workspace/actor and exact local authorities |
| `api/wiring.py` | FastAPI dependency composition and the existing store adapter |
| `api/transport.py` | ASGI local request checks, bounded JSON input, correlation, response headers and metadata logs |
| `api/app.py`, `api/__main__.py` | App factory/lifespan, thin routes and fixed loopback launcher |

Application code imports neither FastAPI nor SQLAlchemy. Accepted domain code remains
unchanged and unaware of HTTP. Endpoint handlers pass typed commands to use cases;
they do not manipulate a SQLAlchemy session or mutate rows. Readiness is an explicit
infrastructure probe in the composition boundary.

FastAPI's own dependency mechanism composes a configured store/service per request;
the lifespan owns the shared engine only when the app factory creates it. The engine
is lazy: construction does not connect, create schema or migrate. Tests can inject an
engine and clock without changing domain behavior. [FastAPI dependencies](https://fastapi.tiangolo.com/tutorial/dependencies/)

The implementation locks [FastAPI 0.142.2](https://pypi.org/project/fastapi/0.142.2/)
and [Uvicorn 0.53.0](https://pypi.org/project/uvicorn/0.53.0/) with HTTPX2 2.13.1 for
development tests. Accepted Pydantic, PostgreSQL driver, SQLAlchemy and Alembic pins
remain unchanged. FastAPI's mandatory `opentelemetry-api` transitive dependency is an
API contract package; ACTUAL adds no instrumentation, exporter or full telemetry stack.

## Command and response contracts

HTTP commands describe intent using strict fields, typed IDs, bounded text and aware
timestamps. They carry `actual-api-v1`; nested assertions reuse the safe accepted
Core contract. Unknown fields and unsupported schema versions fail validation. An
HTTP request cannot choose workspace/actor, privacy classification, verification,
review, claim origin, material revision or arbitrary application history.

Responses wrap safe accepted domain records in `actual-api-v1` envelopes with storage
generation where relevant. Embedded records retain `actual-core-v1`. This deliberate
reuse preserves accepted provenance/UTC serialization without exposing persistence
columns or creating another semantic model. The complete snapshot contains only
runtime records; evaluator labels/outcomes are not members of that contract. HTTP
envelope serialization is not the canonical database/export byte format.

Resource IDs are caller-supplied typed stable IDs, scoped under the configured workspace.
Actor identity is server configured and records attribution only; it is not an
authenticated user assertion. Occurrence/collection times are supplied observations;
recording time comes from the server clock. A backwards clock relative to current
snapshot time fails rather than silently inventing a later timestamp.

## Provenance and lifecycle invariants

Claims created here always have `origin=user_report`, configured actor/time and
`status=self_reported`. Attaching an allowed source kind retains its source reference,
excerpt, relation and collection time; it creates no evidence review and does not
promote claim status. `ai_proposal` remains untrusted provenance, not an inference
capability. `user_report` records the configured source actor; document/artifact source
strings are metadata, never fetched or authenticated.

Attachment changes the claim snapshot and profile revision. To preserve exact claim
refs, the use case rejects reviewed claims and claims already referenced by CV/draft
materials. There is no silent review reset, stale-reference repair or dependent-material
rewrite. Later explicit reconciliation can define those changes when needed. Accepted
whole-snapshot validation remains the final relationship/invariant gate.

New applications contain one `preparing` observation. Each transition consults the
accepted domain transition map, records one strictly later occurrence and appends at
most one observation. The accepted `external_manual` exception reports an outside
manual submission without manufacturing an internal content review. A reported
`reviewed` state neither supplies current `ContentReview` nor proves submission.
Duplicate canonical profile/opportunity intent is rejected.

Job intake and application commands generate their exact accepted semantic Work
Events internally with fresh event IDs and full current record digests. Clients cannot
submit arbitrary observations, actor IDs or business-object catalogs. Profile input
has no invented semantic event type. Retained old events preserve historical references
under accepted Phase-3 behavior; no evaluator outcome becomes an event.

## Transaction and retry boundary

Reads resolve the configured current aggregate. Each mutation checks its supplied
generation, builds a new immutable domain snapshot, validates it and calls the port's
single `save(snapshot, expected_generation, events)` operation. The accepted store
owns the database transaction, workspace advisory/row locks, final concurrency check,
source reconciliation, event validation and commit. HTTP introduces no intermediate
commit or a second transaction manager.

There is a deliberate load-to-save interval: two commands may read the same generation,
but PostgreSQL serializes their saves and rejects the stale writer. No conflicting
command is automatically retried. Atomic save failure rolls back state and observations.
A successful use case returns only after store commit, but network delivery can fail
after commit. A caller must inspect the stable resource/current generation before
retrying; there is no generic HTTP idempotency ledger or exactly-once claim.

## Error semantics

All failures use a fixed-message `ErrorResponse` with an error code and generated
request ID. Safe messages disclose neither raw validation values nor SQL, paths,
credentials, stack traces or hidden evaluator records.

| HTTP status | Meaning and representative codes |
| --- | --- |
| `400` | Invalid/ambiguous destination headers or declared body length |
| `403` | Non-loopback/foreign-origin request or non-synthetic configured runtime state |
| `404` | Missing scoped resource or unavailable route |
| `405` | Unsupported method |
| `408` | Total request-body deadline exceeded |
| `409` | Stale generation, duplicate intent, invalid lifecycle, state conflict or required dependency reconciliation |
| `410` | Configured workspace has a deletion tombstone |
| `413` | Actual or declared body exceeds the limit |
| `415` | Non-JSON command or compressed input |
| `422` | Malformed bounded JSON, invalid request contract or domain input |
| `500` | Stored integrity failure or unexpected internal failure |
| `503` | Database/schema/readiness unavailable |

Malformed JSON and DTO validation are distinct stable categories. Error details are
intentionally sparse: clients use the generated schema and current state to correct
commands rather than receiving potentially sensitive validation excerpts. Response
headers include `no-store`, `nosniff` and the generated correlation ID. Client-supplied
request IDs confer no authority and are not adopted for logs.

## Local transport, health and logging

The launcher binds `127.0.0.1` with proxy headers/access logging disabled. The ASGI
boundary additionally checks direct loopback peer, exact local Host/port, supplied
Origin and Fetch Metadata. POST requires JSON. It reads at most 262,144 actual bytes
within a five-second total deadline and rejects compressed input, duplicate keys,
non-finite numbers, invalid Unicode, non-object roots and nesting deeper than 32.
Other methods reject bodies. Destination checks happen before body parsing/use cases.

`/health/live` confirms process response without the database. `/health/ready` performs
`SELECT 1`, checks the exact accepted migration head and loads/validates the configured
workspace's synthetic classification if present. A correctly migrated empty database
is ready for bootstrap. Missing/wrong schema, deleted/corrupt/non-synthetic workspace
or database failure yields a safe not-ready response. Readiness does not establish
complete production health or check every DDL definition; migration/regression tests
continue to cover frozen guards and drift.

Generated OpenAPI is local at `/api/v1/openapi.json`. Swagger/ReDoc UI is disabled.
Structured console logs contain only server request ID, allowlisted method, matched
route template, status, duration and error code. No raw path/query, user-agent, peer,
body, source text, database URL or external exporter is logged by this boundary.
The process configures no durable file/rotation policy; console capture retention
belongs to its operator. Do not claim the Phase-0 seven-day purge default is automated.

## Authentication contradiction and privacy limits

Phase 0 describes authenticated real-data API operations; this request explicitly
excludes authentication. The accepted threat model also permits explicitly isolated
unauthenticated synthetic development. Phase 4 uses that permitted mode, requiring
`ACTUAL_API_MODE=synthetic-development`, configured actor/workspace and a dedicated
synthetic dataset. Every state read/mutation checks the snapshot's synthetic class;
event reads separately check event workspace/class. A known personal/sensitive aggregate
does not become synthetic merely because the API settings choose development mode.

These controls do not identify a local owner, protect against an authorized OS/DB
administrator or detect actual personal text falsely labeled synthetic. There are
no cookies/sessions, so no cookie-session CSRF mechanism is claimed. No-Origin local
clients can still call this service. Exact origins/Host and loopback are restrictions,
not authentication. Real personal API access remains blocked until later local-owner
access controls and relevant privacy/network/deletion checks are accepted.

The database operator and OS account remain trusted. A dedicated synthetic workspace
and disciplined input handling are operating prerequisites. The full snapshot GET is
appropriate only under this explicit scope; future real-data access must revisit exposure
and authorization rather than weakening the gate. Parameterized accepted persistence
continues unchanged. There is no outbound fetch, arbitrary file intake or hidden-data
loader in the runtime API/application modules.

## Acceptance gates and deferred evidence

Acceptance requires real FastAPI startup, schema generation and intended routes;
typed successful/invalid commands; safe errors; server-derived attribution; synthetic
and local destination guards; lifecycle/provenance preservation; deterministic list
behavior; duplicate/conflict/concurrency and atomic rollback checks against real
PostgreSQL; all prior CareerLab/Core/persistence tests; frozen migration checks; lint,
formatting and strict typing; and Python 3.13/3.14 runs. The current environment manifest
must preserve prior input/oracle hashes without modifying accepted manifests or datasets.
Executed commands/results and known limitations belong in the acceptance record.

Synthetic API tests prove software boundary behavior against controlled records. They
do not prove real-world evidence truth, hiring quality, end-to-end application assistance,
production authentication, load resilience or enterprise security. There is no local
inference, semantic extraction, ranking, material editing, connector, external write,
workflow runtime, telemetry stack, UI or deployment. Phase 5 requires a new request.
