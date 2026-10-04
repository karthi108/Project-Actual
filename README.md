# ACTUAL

Local-first work intelligence and controlled automation software.

ACTUAL chooses ordinary software before AI, treats model output as an untrusted proposal, and requires evidence for professional claims. Career work is the first domain; the platform is not an autonomous application bot.

## Current milestone

**Phase 4: FastAPI Boundary.** Accepted milestones are Phase 0 `4e06cc6`, Phase 1 CareerLab `5b6116a`, Phase 2 Core Contracts `fc6d396` and Phase 3 Persistence `d2a7544`. This slice exposes manual Career commands and reads through a typed, versioned HTTP boundary, an application layer and the accepted transactional PostgreSQL repository. It runs only in explicitly isolated synthetic development mode; real-data access requires later local-owner access controls. The complete Career assistant remains to be implemented and measured.

Start with [the engineering contract](docs/phase-0/engineering-contract.md), then [API usage](docs/phase-4/README.md), [the boundary design](docs/phase-4/design.md), [ADR 0005](docs/adr/0005-fastapi-boundary.md) and [Phase-4 acceptance evidence](docs/phase-4/acceptance-review.md). Accepted [Persistence usage](docs/phase-3/README.md), [storage invariants](docs/phase-3/design.md), [Phase-3 evidence](docs/phase-3/acceptance-review.md), [Core usage](docs/phase-2/README.md), [Phase-2 evidence](docs/phase-2/acceptance-review.md), [CareerLab usage](docs/phase-1/README.md) and [Phase-1 evidence](docs/phase-1/acceptance-review.md) remain historical baselines. Validation and locked-test datasets remain unmaterialized. Do not begin Phase 5 without a new request.

## Contract map

| Document | Responsibility |
| --- | --- |
| [Engineering contract](docs/phase-0/engineering-contract.md) | Problem, users, exact v0.1 scope, non-goals, first scenario and journey |
| [Architecture](docs/phase-0/architecture.md) | Components, dependencies, deployment and repository growth |
| [Data and workflow principles](docs/phase-0/data-and-workflows.md) | Claims/evidence, events, future Workflow IR, approvals and duplicate prevention |
| [Threat model](docs/phase-0/threat-model.md) | Trust boundaries, threats, controls and evidence required before exposure |
| [Privacy](docs/phase-0/privacy.md) | Data flows, retention, deletion, logs and local inference |
| [Evaluation strategy](docs/phase-0/evaluation-strategy.md) | Dataset separation, invariants, metrics and release gates |
| [Architecture decisions](docs/adr/0001-phase-0-decisions.md) | Decisions, alternatives, trade-offs and revisiting triggers |
| [Acceptance review](docs/phase-0/acceptance-review.md) | Coverage, challenges, review findings and remaining uncertainty |
| [Phase-1 plan](docs/phase-0/phase-1-plan.md) | First synthetic-world implementation slice and checks |
| [Original specifications](docs/reference/README.md) | Preserved user inputs and interpretation order |

## Working agreement

Build one understandable slice per phase. Define invariants, explain the design, implement, run relevant checks, and record demonstrated results. Keep real profiles, CVs, application materials, credentials and runtime databases outside Git. Do not claim production readiness or measured savings without evidence.

The first product release is single-user and runs on the user's computer. It supports manual job intake, evidence-backed fit/gap analysis, CV recommendations, reviewed draft improvements and manually recorded application status. The user submits outside ACTUAL.

From this repository, with Python 3.13 or 3.14 and uv available:

```powershell
uv sync --locked
./scripts/verify_phase4.ps1
uv run --locked careerlab generate --manifest datasets/manifests/careerlab-api-env-v1.json
uv run --offline --locked careerlab verify --manifest datasets/manifests/careerlab-api-env-v1.json
```

Generation validates eight public cases before writing observable JSON, a separate ignored evaluator directory and a version/hash manifest. The eighth case deliberately contains an invalid transition and is accepted only as a negative fixture with the exact expected rejection reason. Do not give evaluator files or manifests to a future evaluated ACTUAL component.

The Phase-4 verification script reuses the accepted disposable-PostgreSQL harness with current testpaths and dependencies. It requires Docker and installed Python 3.13/3.14 paths, runs the complete checks and removes only its own disposable database. See [Persistence usage](docs/phase-3/README.md) for interpreter overrides, manual test configuration, migration commands and storage/privacy limits. PostgreSQL acceptance tests require an explicit disposable database and do not silently skip.

See [API usage](docs/phase-4/README.md#start-an-isolated-synthetic-development-api) for private database configuration and the loopback-only `actual-api` launcher. The API does not migrate at startup. It enforces server-configured workspace/actor scope, synthetic classifications, bounded JSON, safe error envelopes and request metadata logs. These restrictions do not authenticate local callers or detect real prose mislabeled synthetic. Claims remain self-reported and attached evidence unreviewed; no AI, external submission, frontend, connectors or workflow execution is included.

Always select the current environment manifest explicitly: API dependencies changed project/lockfile hashes. The three earlier manifests remain accepted historical baselines; the unchanged CLI default still points to the Phase-1 manifest. The new manifest preserves all input/oracle record hashes and records the current environment separately. No evaluator record is part of a runtime domain snapshot, storage table or API response.
