# ACTUAL

Local-first work intelligence and controlled automation software.

ACTUAL chooses ordinary software before AI, treats model output as an untrusted proposal, and requires evidence for professional claims. Career work is the first domain; the platform is not an autonomous application bot.

## Current milestone

**Phase 2: Core Contracts.** Phase 0 was accepted at `4e06cc6` and Phase 1 CareerLab at `5b6116a`. The current slice adds strict domain records, scoped evidence/claim provenance, career relationships, application histories and six observation events. This is a Python contract layer; ACTUAL application behavior remains to be implemented and measured.

Start with [the engineering contract](docs/phase-0/engineering-contract.md), then [Core usage](docs/phase-2/README.md), [the design and invariants](docs/phase-2/design.md) and [Phase-2 acceptance evidence](docs/phase-2/acceptance-review.md). The accepted [CareerLab usage](docs/phase-1/README.md) and [Phase-1 evidence](docs/phase-1/acceptance-review.md) remain historical baseline documents. Validation and locked-test datasets remain unmaterialized. Phase 3 requires a new request.

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
uv run --locked careerlab generate --manifest datasets/manifests/careerlab-core-env-v1.json
uv run --offline --locked careerlab verify --manifest datasets/manifests/careerlab-core-env-v1.json
uv run --locked pytest -q
uv run --locked ruff check src tests
uv run --locked ruff format --check src tests
uv run --locked mypy
```

Generation validates eight public cases before writing observable JSON, a separate ignored evaluator directory and a version/hash manifest. The eighth case deliberately contains an invalid transition and is accepted only as a negative fixture with the exact expected rejection reason. Do not give evaluator files or manifests to a future evaluated ACTUAL component.

Always select the current environment manifest explicitly: adding the Core dependency changed project/lockfile hashes. The original `careerlab-dev-v1.json` remains the accepted Phase-1 baseline; the unchanged CLI default still points to it. The new manifest preserves all input/oracle record hashes and records the current environment separately.
