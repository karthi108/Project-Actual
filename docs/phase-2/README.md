# Phase 2: Core Contracts usage

This slice supplies validated data boundaries for Career v0.1. Read [the design](design.md) for invariants, [the decision record](../adr/0003-core-contract-boundaries.md) for trade-offs and [the acceptance evidence](acceptance-review.md) for demonstrated results. Phase 0 and Phase 1 remain binding at `4e06cc6` and `5b6116a`.

## Where to read the code

| Module | Responsibility |
| --- | --- |
| `actual.core.primitives` | Closed immutable records, distinct opaque ID types, bounded values, aware UTC timestamps and canonical wire codec |
| `actual.core.references` | Workspace/classification/revision/digest-bound business, evidence and claim references |
| `actual.core.workflow` | Exact-content review and three effect classification values |
| `actual.profile.contracts` | Structured assertions, evidence origin/review/revocation, claims, profile relationships and bounded support checks |
| `actual.career.jobs` | Company, original job, separate job decision and proposed normalized requirement |
| `actual.career.materials` | CV provenance, draft assertion proposals and exact-content draft review |
| `actual.career.applications` | Reported lifecycle/history and explicit external-manual tracking |
| `actual.career.snapshot` | Resolve related current career records, source spans, privacy and causal review histories |
| `actual.core.events` | Shared event attribution, source, time and reference envelope |
| `actual.career.events` | Six closed Career event payloads, reference validation and pure redelivery comparison |
| `actual.careerlab_bridge` | Observable-only synthetic compatibility mapping |

The `__init__.py` files identify package responsibility. They do not re-export every model into a shared namespace. No service, persistence or execution layer is present.

## Construction and validation boundaries

Use typed IDs and tuples in Python construction. ID values are opaque kind-prefixed strings with 32 lowercase hexadecimal characters. The caller must supply trusted workspace/actor attribution; IDs themselves do not authenticate a person or establish access.

An individual record checks its own shape and local invariants. A `Profile` resolves claims against current evidence; a `CareerSnapshot` resolves jobs, materials, applications and requirements against that profile and current source records. A standalone ref, review, CV, draft or event cannot establish relationships that require these records. Resolve these boundaries before using structured support in later application behavior.

This fabricated example records a claim without promoting it to supported evidence:

```python
from actual.core.primitives import ClaimId, ProfileId, WorkspaceId
from actual.profile.contracts import Assertion, Claim, Profile, claim_ref, supports_assertion

workspace_id = WorkspaceId("workspace_" + "1" * 32)
profile_id = ProfileId("profile_" + "2" * 32)
assertion = Assertion(kind="skill", subject="python", unit="skill_level", value=2)
claim = Claim(
    id=ClaimId("claim_" + "3" * 32),
    workspace_id=workspace_id,
    profile_id=profile_id,
    revision=1,
    classification="synthetic",
    assertion=assertion,
    text="Synthetic user reports working Python skill.",
    origin="user_report",
    status="self_reported",
)
profile = Profile(
    id=profile_id,
    workspace_id=workspace_id,
    revision=1,
    classification="synthetic",
    name="Fabricated example",
    claims=(claim,),
)
assert not supports_assertion(profile, assertion, (claim_ref(claim),))
```

Evidence review records preserve source identity, reviewer, method, time and exact reviewed source digest. Human confirmation alone supplies no independent verification. AI/user-report evidence requires explicitly independent review with a distinct source reference to qualify; a field value still cannot authenticate a real source. A reviewed-supported claim additionally needs its own exact-content review and sufficient current scoped sources, checked by `Profile`.

For claim/evidence records, `content_digest` identifies the content their own review binds. `snapshot_digest` includes current status and review. Use `claim_ref` and `evidence_ref` to create dependency refs from the complete snapshot. Updating or withdrawing evidence, changing a claim's status, or changing review provenance makes dependent refs stale. This deliberately requires reconciliation instead of silently retaining earlier support.

Records are frozen; `record.model_copy(update={...})` creates a validated replacement. It does not automatically change revision numbers, update dependent refs or create a review. Those are explicit responsibilities of the future mutation layer. `model_construct`, permissive validation options and string-coercion loading are disabled. Python code executing in the same process remains trusted code.

## Wire contract

Use `canonical_bytes(record)` and `load_contract(RecordType, payload)` from `actual.core.primitives` for canonical serialization/deserialization. Every nested wire record must explicitly declare `schema_version="actual-core-v1"`. Unknown versions/fields and duplicate JSON keys are rejected. The loader accepts at most 2,000,000 bytes; the canonical serializer enforces the same bound.

Timestamp text requires an ISO date/time with explicit `Z` or `±HH:MM` offset, at most six fractional digits, and a representable UTC instant. Aware Python datetimes are also accepted. Naive time, Unix-number coercion and precision-truncating text are rejected. Canonical output uses UTC, exactly six fractional digits, sorted keys, compact UTF-8 JSON and one trailing LF. Collection order remains significant unless a specific comparison declares it unordered.

There is no best-effort future-version parsing or migration here. A future schema change needs an explicit compatibility/migration decision and tests before accepting another version. Digests identify data; they do not sign or authenticate it.

## CareerLab compatibility

Only public observable inputs are accepted. For example, after `uv sync --locked`, run this Python code in the repository environment:

```python
from pathlib import Path

from actual.career.snapshot import CareerSnapshot
from actual.careerlab_bridge import ImportContext, load_observable
from actual.core.primitives import ActorId, WorkspaceId, canonical_bytes, load_contract

context = ImportContext(
    workspace_id=WorkspaceId("workspace_" + "1" * 32),
    actor_id=ActorId("actor_" + "2" * 32),
)
payload = Path("datasets/development/inputs/CAREER-DEV-001.json").read_bytes()
snapshot = load_observable(payload, context)
assert load_contract(CareerSnapshot, canonical_bytes(snapshot)) == snapshot
assert snapshot.requirements == ()
assert all(draft.review is None for draft in snapshot.drafts)
```

The adapter uses deterministic IDs scoped by workspace, scenario, object kind and source identity. Cases 001–007 map; case 008 remains an invalid transition and fails ordinary input validation. No evaluator annotation is consulted to repair it.

All mapped records remain synthetic. Fixture source reviews become `synthetic_review`; recorded supported claims use explicitly marked `synthetic_fixture_import` review bookkeeping. Missing assertion/source actors or assertion dates remain unknown. Application history attributes the import context rather than claiming to recover an unknown original actor. Requirements stay empty because extraction answers are evaluator-only. Recruiter messages are outside the minimal Core snapshot; mapping is not a lossless export of the whole fixture.

Do not pass authoring bundles, oracle files or manifests as runtime input. Tests use `generate_inputs`, which constructs observable records without invoking the annotation author. Filesystem/package separation is not a hostile-code sandbox.

## Checks and artifact identity

Run from the repository root:

```powershell
uv sync --locked
uv run --locked ruff check src tests
uv run --locked ruff format --check src tests
uv run --locked mypy
uv run --locked pytest -q --tb=short
uv run --isolated --python C:\Python313\python.exe --locked pytest -q --tb=short --basetemp=.pytest-tmp-careerlab-313
uv run --locked careerlab generate --manifest datasets/manifests/careerlab-core-env-v1.json
uv run --offline --locked careerlab verify --manifest datasets/manifests/careerlab-core-env-v1.json
uv run --offline --isolated --python C:\Python313\python.exe --locked careerlab verify --manifest datasets/manifests/careerlab-core-env-v1.json
```

Select an installed Python 3.13 path appropriate for your machine. Pytest owns and may replace its base temp directory; use a resolved path inside this workspace. The current Windows checks used dedicated `.pytest-tmp-careerlab` and `.pytest-tmp-careerlab-313` directories.

The accepted Phase-1 [manifest](../../datasets/manifests/careerlab-dev-v1.json) remains unchanged. Pydantic changes `pyproject.toml`/`uv.lock` source hashes, so the current [environment manifest](../../datasets/manifests/careerlab-core-env-v1.json) is separate. Always specify that path: the unchanged CareerLab CLI default still targets the baseline. It inventories CareerLab/configuration identity, not all new Core modules. Use the Phase-2 Git commit plus lockfile and acceptance record for Core reproducibility.

These checks demonstrate executable contract consistency and synthetic compatibility. They do not prove unrestricted prose truth, extraction/recommendation quality, document authenticity, authentication, durable deduplication, delivery or hiring outcomes. Validation and locked-test data remain unmaterialized. Phase 2 stops before infrastructure or Phase 3.
