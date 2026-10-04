# ACTUAL

Local-first work intelligence and controlled automation software.

ACTUAL chooses ordinary software before AI, treats model output as an untrusted proposal, and requires evidence for professional claims. Career work is the first domain; the platform is not an autonomous application bot.

## Current milestone

**Phase 1: CareerLab development fixtures.** Phase 0 was accepted by the user at commit `4e06cc6`. CareerLab now supplies eight reproducible synthetic cases, strict fixture contracts, separately packaged evaluator annotations and integrity checks. This is an offline evaluation environment; ACTUAL application behavior remains to be implemented and measured.

Start with [the engineering contract](docs/phase-0/engineering-contract.md), then [CareerLab usage and file map](docs/phase-1/README.md) and [Phase-1 acceptance evidence](docs/phase-1/acceptance-review.md). The accepted [Phase-1 plan](docs/phase-0/phase-1-plan.md) limits this release to public development data. Validation and locked testing are deferred; Phase 2 requires a new request.

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
uv run --locked careerlab generate
uv run --locked careerlab verify
uv run --locked pytest -q
```

Generation validates eight public cases before writing observable JSON, a separate ignored evaluator directory and a version/hash manifest. The eighth case deliberately contains an invalid transition and is accepted only as a negative fixture with the exact expected rejection reason. Do not give evaluator files or the manifest to a future ACTUAL component. See [the usage guide](docs/phase-1/README.md) for boundaries, checks and reproducibility details.
