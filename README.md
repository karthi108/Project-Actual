# ACTUAL

Local-first work intelligence and controlled automation software.

ACTUAL chooses ordinary software before AI, treats model output as an untrusted proposal, and requires evidence for professional claims. Career work is the first domain; the platform is not an autonomous application bot.

## Current milestone

**Continuous office development, Phases 7–27 — canonical acceptance pending.** Phase 7 is implemented and office verified; its WIP checkpoint preserves [verification evidence](docs/phase-7/migration-verification.md). See [checkpoint map and validation debt](docs/office-build/README.md). This slice builds a deterministic evidence-backed profile, separate synthetic source/claim reviews, safe withdrawal and typed experience context on existing contracts and storage. It remains synthetic-only. Accepted milestones are Phase 0 `4e06cc6`, Phase 1 `5b6116a`, Phase 2 `fc6d396`, Phase 3 `d2a7544`, Phase 4 `7deff65`, Phase 5 `09d7653` and Phase 6A `bdc988a`. Original Phase-6 NO-GO evidence remains unchanged. The current Phase-7 checkpoint adds no real-data intake, tools, profile model interpretation or CV generation. Subsequent roadmap capabilities are added in separate provisional checkpoints, using synthetic data only.

Start with [the engineering contract](docs/phase-0/engineering-contract.md), [profile usage and file map](docs/phase-7/README.md), [Phase-7 design/gates](docs/phase-7/design.md), [ADR 0009](docs/adr/0009-evidence-backed-profile-boundary.md) and [Phase-7 evidence](docs/phase-7/acceptance-review.md). [Accepted Job Intelligence](docs/phase-6a/README.md), [Phase-6A evidence](docs/phase-6a/acceptance-review.md), the [original Phase-6 NO-GO](docs/phase-6/acceptance-review.md) and its source snapshot remain unchanged. Accepted [Model Gateway](docs/phase-5/README.md), [API](docs/phase-4/README.md), [Persistence](docs/phase-3/README.md), [Core](docs/phase-2/README.md) and [CareerLab](docs/phase-1/README.md) remain historical baselines. Validation and locked-test datasets remain unmaterialized. The [continuous-build authorization](docs/adr/0010-continuous-office-build.md) supersedes the earlier Phase-7 stopping rule. Continue in phase order without per-phase approval; canonical validation occurs later on the personal laptop.

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
./scripts/verify_phase7.ps1
uv run --offline --locked careerlab verify --manifest datasets/manifests/careerlab-profile-env-v1.json
```

The eight public cases are frozen accepted artifacts. Verify their manifest rather than routinely regenerating them. Observable JSON remains separate from ignored evaluator storage and version/hash metadata. The eighth case deliberately contains an invalid transition and is accepted only as a negative fixture with the exact expected rejection reason. Do not give evaluator files or manifests to a future evaluated ACTUAL component.

The Phase-7 verification script reuses the accepted disposable-PostgreSQL harness with current testpaths and dependencies. It requires Docker and installed Python 3.13/3.14 paths, runs the complete deterministic checks and removes only its own disposable database. It does not run a large model. See [Persistence usage](docs/phase-3/README.md) for interpreter overrides, manual test configuration, migration commands and storage/privacy limits. PostgreSQL acceptance tests require an explicit disposable database and do not silently skip.

The separate live acceptance helper uses the installed `qwen3:4b-instruct` by default. It starts and stops its own temporary loopback Ollama process, with cloud/body logging/pruning disabled and existing model weights; it does not change the shared server configuration or download models:

```powershell
$env:ACTUAL_MODEL_MODE = 'synthetic-development'
uv run --locked python scripts/verify_phase5_live.py
```

The direct `actual-model-probe` command uses the configured local server and refuses inference unless cloud-disabled status is confirmed. Supported Ollama compatibility is explicitly 0.34.3; future versions require review. No paid model service, API key, arbitrary prompt argument or HTTP AI endpoint is required. The probe admits only fabricated enum tokens; it has no CareerLab/evaluator input mapping. See [Model Gateway usage](docs/phase-5/README.md) for configuration and limits.

See [API usage](docs/phase-4/README.md#start-an-isolated-synthetic-development-api) for private database configuration and the loopback-only `actual-api` launcher. Its accepted behavior remains unchanged: no startup migrations, server-configured workspace/actor scope, synthetic classifications, bounded JSON, safe errors and request metadata logs. These restrictions do not authenticate local callers or detect real prose mislabeled synthetic. New claims remain self-reported and attached evidence unreviewed. Phase 7 adds explicit separate synthetic reviews and withdrawal, with exact pins and dependency reconciliation; these do not independently verify real sources. No model integration, external submission, frontend, connectors or workflow execution is added to those routes.

Always select the current environment manifest explicitly: Phase-7 testpaths/project metadata changed the project hash. The seven earlier manifests remain accepted historical baselines; the unchanged CLI default still points to the Phase-1 manifest. The new manifest preserves all input/oracle record hashes and records the current environment separately. No evaluator record is part of a runtime domain snapshot, storage table, API response or model request.
