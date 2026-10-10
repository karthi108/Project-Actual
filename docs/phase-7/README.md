# Phase 7 usage and file map

This slice adds a synthetic evidence-backed profile; it does not certify a real person. Read [design and gates](design.md), [ADR 0009](../adr/0009-evidence-backed-profile-boundary.md) and [acceptance evidence](acceptance-review.md).

[Laptop verification and module commands](migration-verification.md) record the reproduced checks using fresh Python 3.13/3.14 environments and native disposable PostgreSQL. Docker and the default interpreter paths are unavailable on that host; generated Windows console launchers also returned access-denied errors. The verified Python module commands provide the same application and test entry points.

| File | Responsibility |
| --- | --- |
| src/actual/profile/contracts.py | Existing claim/source rules; optional context and generic-support gate |
| src/actual/profile/experience.py | Closed category/version and honest optional activity times |
| src/actual/profile/projection.py | Exact graph admission, immutable groups, public support/provenance view |
| src/actual/application/profile_commands.py | Exact generation/revision/snapshot pins; no supplied authority |
| src/actual/application/service.py | Separate synthetic reviews, withdrawal and atomic dependency reconciliation |
| src/actual/api/app.py and contracts.py | Thin use-case routes and typed evidence-view envelope |
| src/actual/job_intelligence/matching.py | Deterministic comparisons through admitted groups; matching v3 |
| tests/profile | Domain, temporal, provenance, deterministic view and legacy-byte boundaries |
| tests/application/test_profile_service.py | Review/withdraw rules and unchanged-state rejection |
| tests/persistence/test_profile_integration.py | Real PostgreSQL/API round trips, rollback and concurrency |
| tests/api/test_profile_boundary.py | Closed authority fields, safe errors, origins and OpenAPI |
| scripts/verify_phase7_profile.py | Retained Phase-6A source-selection replay, not model inference |

Run the complete disposable PostgreSQL checks on both supported interpreters:

```powershell
./scripts/verify_phase7.ps1
uv run --offline --locked careerlab verify --manifest datasets/manifests/careerlab-profile-env-v1.json
uv run --offline --locked python scripts/verify_phase7_profile.py
```

The API launcher and private database configuration remain those documented in [Phase 4](../phase-4/README.md). Initialize an explicitly fabricated career, create a self-reported claim, attach an unreviewed synthetic_fixture source, then review the exact source and exact claim separately. Each mutation advances generation; reload returned records and bind the next command to the current record's revision and snapshot_digest. The API exposes these records without fetching source_reference.

GET /api/v1/profile/evidence returns generation and the derived profile view. `reviewed_source_refs` means a source was reviewed, not that a claim was accepted. `eligible_claim_refs`/`eligible_evidence_refs` appear only for supported rows. `declaration_exceeds_support` makes an optimistic declaration visible. Explicit contrary evidence yields conflict; unknown/unverified do not mean the candidate lacks the capability.

Contextual experience remains individual source facts. Even a reviewed professional_employment source cannot accept an unscoped generic-month claim: category-specific claim semantics are not yet accepted. Unknown dates remain null, and months are never derived or accumulated. Existing context-free CareerLab semantics remain unchanged.

Synthetic fixture reviews are explicit development operations. No independent-verification endpoint, real-data mode, authentication claim or Qwen profile interpretation is provided. API logs exclude source content. All claims referenced by CV/draft metadata require future reconciliation and return 409 instead of silently invalidating reviewed CV/draft content.
