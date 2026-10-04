# Phase 2 acceptance evidence: Core Contracts

Status: Phase-2 engineering gates satisfied on 2026-10-04. User acceptance is separate. Phase 0 and Phase 1 are accepted at `4e06cc6` and `5b6116a`. The focused Phase-2 source commit is identified in Git history; it is not embedded in its own content. No Phase-3 work is included.

## Delivered result and gate assessment

The smallest used domain layer now has closed, immutable contracts for typed identities/references, structured assertions and provenance, profiles, companies/jobs/requirement proposals, CV/draft provenance, application history and the six Career Work Events. Shared Core event metadata has no Career dependency. Workflow primitives contain only exact-content review and effect classification.

Individual records enforce local shape and invariants; `Profile`, `CareerSnapshot` and event catalog resolution enforce supplied current relationships. Supported claims require explicit exact-content review and sufficient active scoped reviewed evidence. Human confirmation or an AI/user report cannot silently become that evidence. Complete source snapshot refs make review changes, revocation and changed status stale downstream dependencies. Accepted structured draft units require current support that existed by review time.

Tests cover valid/invalid construction, closed fields and schema versions, strict numeric/ID types, frozen validated replacement, JSON duplicate keys, wire bounds/nesting, timezone/precision boundaries, serialization, source/review digests, foreign/stale/missing refs, privacy dominance, conflicting/withdrawn evidence, requirement spans/aliases, duplicate applications, causal timelines and the lifecycle transition space. Event tests cover all six payloads, evidence absence, metadata scope, current catalog validation and source duplicate/conflict classification. Properties use bounded combinations and offset/seed loops where they exercise real invariants; no extra property-testing dependency was needed.

The observable-only adapter maps seven valid public CareerLab cases and rejects the eighth through ordinary invalid-transition validation. It never fills requirements from evaluator labels, never promotes proposed drafts to reviewed artifacts and never reads oracle files to establish compatibility. All imported data remains explicitly synthetic. Tests reject authoring/oracle objects and check the adapter's observable construction path. The original CareerLab suite remains passing.

## Design challenges and corrections

The [design](design.md) and [ADR 0003](../adr/0003-core-contract-boundaries.md) record scope and choices explained before implementation. Independent task reviews and integration checks led to concrete corrections:

- Evidence relation and selected claim source refs bind their own reviews; complete snapshot hashes additionally bind current status and review provenance. Revoking either of two selected sources invalidates earlier dependencies instead of leaving incidental support valid.
- Derived CV/draft/claim/requirement classification cannot understate source privacy. Resolution checks actual current source classification, not only claimed reference tags.
- Canonical opportunity aliases cannot admit conflicting job text, duplicate normalized subjects or duplicate applications without a defined reapplication contract.
- Current support and source review must precede accepted draft review. Historical application status does not substitute for exact artifact review.
- Shared event metadata was separated from Career payloads. Unknown-only assessments remain representable; event evidence does not itself certify an assessment or artifact review.
- JSON entry points now share duplicate/version/size/nesting guards; overly precise timestamp text and UTC overflow fail predictably instead of truncating precision or leaking an overflow exception.
- Adding Pydantic conflicted with the accepted manifest's project/lockfile hashes. The accepted manifest and fixture bytes were preserved; a separately named environment manifest records the new configuration.

Initial lint/type/test failures were fixed before these final checks. Windows pytest temporary-directory access was handled with dedicated workspace temp roots. There are no skipped tests or known failing checks in the final suites. These reviews are assistant engineering reviews, not independent validation of real-world documents or employers.

## Checks actually run

Host: Windows/PowerShell, uv 0.11.7. Pydantic 2.13.5 with pydantic-core 2.46.5 is locked; pytest 9.1.1, Ruff 0.16.10, mypy 2.4.0 and setuptools 84.0.0 remain pinned. Both installed supported Python branches were exercised. Temp-directory paths were resolved and checked to remain inside the workspace before pytest could replace them.

| Command/check | Final result |
| --- | --- |
| `uv sync --locked` | Locked environment installed successfully |
| `uv run --locked ruff check src tests` | All checks passed |
| `uv run --locked ruff format --check src tests` | 34 Python files already formatted |
| `uv run --locked mypy` | Strict check passed for 24 source files |
| `uv run --locked pytest -q --tb=short` | **492 passed**, Python 3.14.7, 9.07 seconds |
| `uv run --isolated --python C:\Python313\python.exe --locked pytest -q --tb=short --basetemp=.pytest-tmp-careerlab-313` | **492 passed**, Python 3.13.1, 10.63 seconds |
| `uv run --locked careerlab generate --manifest datasets/manifests/careerlab-core-env-v1.json` | Same 8 public inputs and 8 separate evaluator files; current environment manifest generated after validation |
| `uv run --offline --locked careerlab verify --manifest datasets/manifests/careerlab-core-env-v1.json` | Current source identity, all record hashes and paired invariants verified on Python 3.14.7 |
| `uv run --offline --isolated --python C:\Python313\python.exe --locked careerlab verify --manifest datasets/manifests/careerlab-core-env-v1.json` | Same bytes/manifest verified on Python 3.13.1 |
| Seven observable cases mapped/canonically serialized in fresh processes on both interpreters | Identical 138,554-byte bundle and SHA-256 below |
| Accepted baseline preservation audit | All 42 files outside the four authorized root/configuration edits match the accepted Git blobs; all 16 input/oracle hashes match both manifests |
| Local documentation audit | 31 local links resolve; all 3 Python examples execute successfully |
| Source import audit | Standard library, ACTUAL modules and Pydantic only; no excluded infrastructure imports |
| `git diff --check` and staged equivalent; staged source/artifact hash audit | No whitespace errors; current manifest matches staged source hashes and preserved input hashes; no evaluator/private/held-out/environment files staged |

The source/artifact, documentation and staged checks verify that the deliverable contains only this authorized slice alongside unchanged baseline data. No validation/locked-test case was created or inspected.

## Reproducibility identity

| Identity | Value |
| --- | --- |
| Accepted Phase-1 source | `5b6116a8b375029f5a60a40f2cc2082cae8b6b6c` |
| Domain wire schema | `actual-core-v1` |
| CareerLab dataset/generator | `careerlab-development-v1` / `careerlab-generator-v1` |
| CareerLab input/oracle/rubric | `careerlab-input-v1` / `careerlab-oracle-v1` / `careerlab-support-v1` |
| CareerLab seed | `20261004` |
| Preserved baseline dataset SHA-256 | `a7d59618b371c0e51a5d6b09798eec1b48e82dbe37c5fe307a20f1bd0e8f40a4` |
| Current environment dataset SHA-256 | `c663a2591dbcc9270d027fc55c863c700eeabc40bce8ff3830d0bd1de53f01d0` |
| Seven mapped Core snapshots SHA-256 | `f80b5390ebffd204abd9d63ec612c60a12ca8602ec9bcffcdbd9059aff16f1f5` |

The [baseline manifest](../../datasets/manifests/careerlab-dev-v1.json) and [current environment manifest](../../datasets/manifests/careerlab-core-env-v1.json) have identical membership and all 16 input/oracle record hashes. Only `pyproject.toml` and `uv.lock` differ in their source inventories. The accepted CareerLab source/tests, Phase-0/Phase-1 docs, original specifications and eight committed input files remain unchanged. Generated evaluator files remain ignored. Validation/locked-test status stays unmaterialized.

The Core bundle is the concatenation, in generator order, of `canonical_bytes(map_observable(case, context))` for `generate_inputs(20261004)[:7]`, with workspace `workspace_` followed by 32 `1` digits and actor `actor_` followed by 32 `2` digits. Each snapshot includes its own trailing LF. This identifies observable compatibility output, not a new evaluation dataset. To reproduce in each interpreter's locked environment:

```python
import hashlib

from actual.careerlab.generator import generate_inputs
from actual.careerlab_bridge import ImportContext, map_observable
from actual.core.primitives import ActorId, WorkspaceId, canonical_bytes

context = ImportContext(
    workspace_id=WorkspaceId("workspace_" + "1" * 32),
    actor_id=ActorId("actor_" + "2" * 32),
)
bundle = b"".join(
    canonical_bytes(map_observable(case, context)) for case in generate_inputs(20261004)[:7]
)
print(len(bundle), hashlib.sha256(bundle).hexdigest())
```

The environment manifest inventories accepted CareerLab modules/methodology/rubric and current configuration, not every new Core source file. The Phase-2 Git commit and locked environment identify that source. Fixed LF attributes preserve cross-checkout source/artifact hashes. No identity claims a signature or annotation correctness.

## Limits and deferred work

This phase proves executable data-boundary consistency for controlled records. It does not prove semantic job extraction, unrestricted prose support, real source authenticity, CV recommendation quality, model quality, labor-market generalization or hiring outcomes. Synthetic reviews remain fixture assumptions. The eight public fixtures share ancestry and form one development component; held-out evaluation remains future work.

Mutable-history enforcement, monotonic revisions, authentication, real access control, transactionality, persisted event deduplication and external-effect approval remain future application/storage responsibilities. Catalogs and owner/actor attribution are supplied by trusted callers. Classification labels cannot discover every secret in arbitrary text or implement retention/deletion. Events observe facts; accepted event metadata alone does not validate a corresponding artifact's semantics or grant execution authority.

The bridge is intentionally partial: requirements are absent, proposals are unreviewed, recruiter messages are outside the Core snapshot, and unknown original actor/time fields are not fabricated. Imported application attribution and reconstructed synthetic claim review are documented bookkeeping.

No PostgreSQL, SQLAlchemy, Alembic, FastAPI, UI, Qwen/Ollama, model abstraction, connector, browser automation, voice, NEXUS, Temporal, workflow runtime or cloud infrastructure was added. There are no runtime network calls. Phase 2 ends with its focused local commit; Phase 3 requires a new request.
