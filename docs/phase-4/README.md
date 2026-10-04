# Phase 4: synthetic Career HTTP boundary

This phase exposes a small local FastAPI boundary over accepted Career contracts and
PostgreSQL persistence. It supports manual job intake, unreviewed profile input and
reported application tracking. It does not complete the Career assistant. See
[the design](design.md), [ADR 0005](../adr/0005-fastapi-boundary.md) and
[acceptance evidence](acceptance-review.md) for decisions, demonstrated checks and limits.

## Run the checks

From the repository with uv, Docker and Python 3.13/3.14 available:

```powershell
uv sync --locked
./scripts/verify_phase4.ps1
```

The Phase-4 script delegates to the accepted Phase-3 harness with the current testpaths
and dependencies. That harness starts its own disposable, loopback-published PostgreSQL,
runs static checks and all existing and new tests on both supported interpreters,
then removes only its own test database. It is a verification harness, not an API
deployment or a persistent data service. Interpreter overrides and the corresponding
manual PostgreSQL test configuration follow the [Phase-3 instructions](../phase-3/README.md).

CareerLab generation remains offline and separate from the runtime API. Select the
current environment manifest explicitly:

```powershell
uv run --locked careerlab generate --manifest datasets/manifests/careerlab-api-env-v1.json
uv run --offline --locked careerlab verify --manifest datasets/manifests/careerlab-api-env-v1.json
```

The original three environment manifests remain historical baselines. The unchanged
CLI default still selects the Phase-1 manifest. Evaluator answers, lineage, manifests
and future outcomes are never runtime API inputs. The eight public development cases
are shared-ancestry fixtures, not independent held-out partitions. Validation and
locked-test data remain unmaterialized.

## Start an isolated synthetic development API

Use a dedicated synthetic workspace in a protected local PostgreSQL database, with
its schema explicitly migrated according to [Persistence usage](../phase-3/README.md).
The API neither creates tables nor runs migrations at startup. Supply the existing
`ACTUAL_DATABASE_URL` privately; keep credentials outside Git and shell history.

Set these non-secret settings in the process that launches ACTUAL:

```powershell
$env:ACTUAL_API_MODE = 'synthetic-development'
$env:ACTUAL_API_WORKSPACE_ID = 'workspace_11111111111111111111111111111111'
$env:ACTUAL_API_ACTOR_ID = 'actor_22222222222222222222222222222222'
$env:ACTUAL_API_PORT = '8765'
uv run --locked actual-api
```

`actual-api` binds `127.0.0.1` only. Use `http://127.0.0.1:8765` or the configured
port; proxy headers are disabled. Direct peers must be loopback addresses. Host must
be exactly an allowed local hostname and port; supplied Origin must be the exact
allowed HTTP origin. Foreign/cross-site requests are rejected. A request without
Origin may be accepted, so these checks do not authenticate a local caller.

This is an explicitly isolated **unauthenticated synthetic-development mode** allowed
by the accepted threat model. Personal/sensitive snapshots and events fail closed.
Labels cannot detect real personal prose deliberately or accidentally marked synthetic:
the trusted operator must keep real material out of this workspace and process.
Real-data API access stays blocked until a later local-owner access design and its
tests are accepted. There is no login, session, pairing secret or production authentication.

## API surface

All commands use JSON and typed prefixed IDs. `schema_version` is `actual-api-v1`
for HTTP command/envelope records; embedded accepted domain records retain
`actual-core-v1`. The generated schema is available at `/api/v1/openapi.json`.
Swagger/ReDoc pages are disabled, so startup adds no browser interface or remote
documentation assets.

| Method and path | Purpose |
| --- | --- |
| `GET /health/live` | Confirm the HTTP process is alive without contacting PostgreSQL |
| `GET /health/ready` | Check database access, exact migration head and configured synthetic workspace; an empty migrated database may initialize |
| `POST /api/v1/career` | Initialize an absent configured workspace with one profile, company and first manual job |
| `GET /api/v1/career` | Read its current complete Career snapshot, including profile/evidence, CVs and histories |
| `POST /api/v1/jobs` | Add a pasted manual job; reuse a company only when its supplied name/context match |
| `GET /api/v1/jobs` | List jobs by typed ID |
| `GET /api/v1/jobs/{job_id}` | Read one scoped job |
| `GET /api/v1/profile` | Read the configured profile, claim status and evidence provenance |
| `POST /api/v1/profile/claims` | Record a self-reported claim |
| `POST /api/v1/profile/evidence` | Attach unreviewed evidence to an eligible unreviewed claim |
| `POST /api/v1/applications` | Start a new preparing application |
| `GET /api/v1/applications` | List applications by typed ID |
| `GET /api/v1/applications/{application_id}` | Read one scoped application and history |
| `POST /api/v1/applications/{application_id}/status` | Append one valid reported lifecycle observation |
| `GET /api/v1/events` | Read retained semantic observations |

Initialization is necessary because the accepted Career snapshot requires a profile,
company and job. It is not arbitrary snapshot import. A second initialization
conflicts. It uses `expected_generation: 0`; later commands require the current
positive generation returned by a read or successful command. Reload after `409`
before deciding whether to try a changed command.

For example, after starting the server against an empty migrated synthetic workspace:

```powershell
$career = @{
    schema_version = 'actual-api-v1'
    expected_generation = 0
    profile = @{
        id = 'profile_33333333333333333333333333333333'
        name = 'Synthetic Candidate'
    }
    job = @{
        id = 'job_44444444444444444444444444444444'
        opportunity_id = 'opportunity_55555555555555555555555555555555'
        company = @{
            id = 'company_66666666666666666666666666666666'
            name = 'Synthetic Example Company'
            context = 'Fabricated development company.'
        }
        title = 'Synthetic Backend Engineer'
        text = 'Fabricated posting: Python experience is required.'
        source_reference = 'manual:synthetic-example'
        posted_at = '2026-10-01T09:00:00Z'
    }
} | ConvertTo-Json -Depth 8
Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8765/api/v1/career' `
    -ContentType 'application/json' -Body $career
```

Source references are bounded opaque metadata, even when they resemble a path or URL.
ACTUAL does not fetch, scrape or open them. This sample contains only fabricated data.

## Reading, mutation and retry limits

Lists accept `offset` from 0 to 1,000,000 and `limit` from 1 to 100, default 20.
An offset beyond the end returns empty items and no next offset. Job/application
pages include the snapshot generation: compare it across pages and restart a traversal
if it changes. Event pages are ordered by occurrence time and event ID but use a
separate retained-history read; they do not claim one atomic snapshot generation.

Profile commands cannot set ownership, classification, review, verified state or
origin attribution. A new claim remains `self_reported`; attached evidence remains
unreviewed. Evidence cannot be attached through this endpoint when the claim is
reviewed or already referenced by a CV/draft. Such a change requires an explicit
future reconciliation/review use case; this API will not silently rewrite dependents.

An application's `reviewed` status records reported tracking history. It is not a
`ContentReview`, a current draft approval or proof of submission. `external_manual`
records the accepted narrow report of an outside manual submission. ACTUAL performs
no external action. Duplicate application intent for the same profile/opportunity
and invalid lifecycle transitions conflict.

One repository save atomically commits the changed aggregate and its generated
job/application event. Rejected commands and failed transactions do not partially
persist. A commit can succeed before an HTTP response is lost; no generic idempotency
key or exactly-once delivery promise is introduced. Stable client resource IDs,
aggregate generations and reads let a caller inspect the result before retrying.

## Errors, logs and retained limits

Errors have an `actual-api-v1` envelope with `error.code`, a fixed safe message and
server-generated `request_id`; the same ID appears in `X-Request-ID`. They contain no
validation input, SQL details, credentials, internal paths or stack trace. See the
[design error map](design.md#error-semantics) for status categories. Every response
has `Cache-Control: no-store` and `X-Content-Type-Options: nosniff`.

The launcher emits structured request metadata to its console stream: generated
request ID, allowlisted method, matched route template, status, duration and error
code. It records neither raw paths/query strings nor request/response bodies. Uvicorn
access logs are disabled. No file logger, telemetry exporter or automatic log rotation
is configured; a caller capturing console output owns retention. The accepted
seven-day diagnostic default is not an implemented purge job.

POST bodies require `application/json`, at most 262,144 actual bytes, and completion
within five seconds. Compressed input, duplicate JSON keys, non-finite values,
invalid Unicode and excessive nesting are rejected. Other methods accept no body.
These limits bound request parsing; they are not a load, denial-of-service or
multi-user availability certification.

There is no HTTP deletion/export/import, company CRUD, claim verification, requirement
review, draft editing/review, CV generation/ranking, assessment or arbitrary event
submission. Accepted Phase-3 retention/deletion remain explicit internal primitives;
no scheduler is added. No AI, frontend, connectors, workflow execution, deployment
or Phase-5 implementation is included.
