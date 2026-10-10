# Phase 7 acceptance review

Status: **IMPLEMENTED / OFFICE VERIFIED / CANONICAL ACCEPTANCE PENDING**, 2026-10-06. Accepted base: Phase 6A `bdc988a`. The original Phase-6 NO-GO remains unchanged. [ADR 0010](../adr/0010-continuous-office-build.md) authorizes provisional continuous development through Phase 27. This document is a provisional review, not user acceptance.

The implementation and the earlier acceptance record below were already present as uncommitted work at handoff. Before committing, this continuation reproduced the engineering, integrity and replay checks on the current laptop and ran the unchanged local Qwen connectivity probe on both supported Python branches. [Laptop verification](migration-verification.md) and its [machine-readable record](migration-verification-v1.json) contain the final reproduced evidence. The earlier Docker/interpreter timings below describe the inherited record, not commands executed on this laptop. No additional agent review or new Job Intelligence accuracy trial was performed during this continuation.

## Delivered behavior

Claims, source review and claim acceptance remain separate. A source review cannot accept a claim. Exact generation/revision/snapshot pins bind separate synthetic-fixture and claim-review operations to server actor/time/method. Withdrawals retain source provenance and existing source-review metadata, rebind all affected references and invalidate dependent claim reviews transactionally. All CV/draft reference dependencies require explicit future reconciliation and return 409.

The deterministic profile view exposes declarations, current eligible support, reviewed sources, optimistic declaration discrepancies, missing review, withdrawals and explicit conflicts. Positive French A2 evidence cannot promote a B2 declaration and does not itself prove B2 impossible. Exact source/claim references preserve traceability. Job Intelligence consumes admitted evidence groups and keeps its five fit states.

Optional versioned source experience context preserves category, source-authored months, relation and honest optional activity dates. No periods are summed or dates invented. Contextual evidence can be source-reviewed but cannot support or refute unscoped generic tenure. This is enforced in the domain, application, profile view and matcher, including the future generic CV-support predicate. Legacy absent-context serialization and digests remain identical. No database schema/migration, dependency, model capability, provider, score, recommendation or AI HTTP route was added.

## Inherited uncommitted engineering report (not rerun here)

The inherited draft reported that `./scripts/verify_phase7.ps1` completed with exit 0. These Docker results and old interpreter timings were not independently reproduced on this office host; the current office checks are in migration-verification.md. It reused the accepted pinned disposable PostgreSQL harness and removed its own labeled container and private test configuration.

| Check | Result |
| --- | --- |
| Python 3.14.7 full regression | 1,456 passed, no skips; 202.56 seconds |
| Python 3.13.1 full regression | 1,456 passed, no skips; 195.50 seconds |
| New focused coverage | 120 cases across profile, application, HTTP, real PostgreSQL and Job Intelligence integration/replay |
| Repository Ruff lint | Passed |
| Repository Ruff formatting | 123 files already formatted |
| Accepted inference/evaluation helper lint/format | Passed |
| New profile replay helper lint/format | Passed |
| Strict mypy | Passed, 80 source files; Python 3.13 and 3.14 targets checked |
| PostgreSQL persistence/migrations | Passed as required real database tests, including head/DDL guard, drift and downgrade/re-upgrade checks; accepted head remains 0001_career_persistence |
| CareerLab integrity | Passed; eight public cases, validation/locked_test unmaterialized |
| Whitespace and final scope review | Passed; no unresolved material finding |

Coverage includes wrong/foreign/stale references, duplicate identities, extra/authority fields, timezone/temporal boundaries, overlapping experience periods without accumulation, unreviewed/withdrawn/user/AI sources, related-technology non-equivalence, explicit contrary sources, separate reviews, pinned intents, backward clocks, atomic rollback and competing reviews. Existing gateway/injection/normalization/evaluator regressions remain mandatory and passed. No SQLite substitution or database-test skip was used.

## Deterministic integration evidence

[Profile replay](profile-replay-v1.json) records 87 retained source selections: three historical trials, 29 observable development/adversarial/semantic cases each. The actual ModelGateway and Job Intelligence pipeline used an in-memory provider double, with no model process or inference. Gold labels were loaded only after runtime calls; the double checked that requests contain only the expected observable source segments.

All 87 input job/profile canonical snapshots stayed unchanged, all 87 exact source-bound profile-view checks passed, and all 87 deterministic source selections matched. All nine group evaluation dictionaries and canonical decisions exactly equal the accepted report, with 54 gold requirement units per historical trial: 24 original, 24 adversarial and six semantic. The original 24/24 canonical fit decisions per trial and adversarial retention remain preserved. Matching is now career-evidence-matching-v3; the unchanged extraction capability is job_requirement_extraction:v2.

This replay is an integration regression, **not fresh live Qwen evidence**. The accepted Phase-6A live trials and model metadata remain in their original artifacts. No new accuracy/F1 or real-world generalization claim is made. The existing extraction false positive remains an unsupported UNKNOWN row and is retained in replay failures; it was neither hidden nor tuned away.

## Preservation and reproducibility

Seventy protected tracked artifacts under earlier phase evidence/dataset/migration paths and uv.lock remain unchanged against `bdc988a`. All eight observable/oracle record hash pairs remain identical, as do seven valid observable domain-profile canonical digests. The eighth CareerLab negative case retains its exact accepted rejection. Neither future split was materialized.

The new environment manifest records only changed pyproject.toml among CareerLab source/configuration hashes. Earlier manifests were preserved, rather than overwritten or regenerated. Its dataset/environment identity is `bb952bea56834061b72b6ff9027eb36fb1c7764ae03fcc4cefb861c2706c02ad`.

| Artifact | SHA-256 |
| --- | --- |
| Original Phase-6A evaluation report | 903990d81e2784e0c2c3fd161c3d97b8159eadedca16a3ca142dea6d45c8e2aa |
| New profile replay report | 776a5bdcd5f0af1fc4f777bf846747e490a64e0891cefdde8095416c2c0fe62f |
| New environment manifest file | 7362bac4d820a0fd336e6fa16760a7e48cddca063133042e24a94a3407e23fb7 |
| New OpenAPI artifact | c88c3152d1c3c105f8cc1ea137337b2abdc369d27a1c7881fd1f726e64e4f386 |
| Byte-preserved Phase-7 request | d8de5b68ff4d5824c57445c81b05285a1ff1cfbec14a1f00c1090dae2c6ab8f7 |

[OpenAPI](openapi-v1.json) documents seven profile HTTP operations, including the four new view/review/withdraw operations. It was generated without contacting a database. [Machine-readable evidence](acceptance-evidence-v1.json), [design](design.md), [usage/file map](README.md), [ADR 0009](../adr/0009-evidence-backed-profile-boundary.md) and the preserved request identify the contract and important decisions. The commit itself identifies the final implementation; no historical evaluation freeze was rewritten.

## Review findings and limits

Before acceptance, review caught a generic-duration promotion path: contextual project/internship sources could accept a generic claim while the view/matcher abstained. Domain generic-support qualification and application eligibility now both prohibit it; all six categories are covered. The symmetric contrary-evidence rule also prevents category-specific evidence from refuting generic tenure. The inherited draft reported a final independent review without a remaining material issue; this continuation did not perform a new independent-agent review. Documentation was corrected to reflect refusal of all CV/draft references and the current-store review-history limitation.

The inherited draft also described a different host where Docker Desktop initially failed on stale inaccessible zero-byte IPC entries. This account is historical, not a procedure used or recommended on this office device. Supported restarts were insufficient. Only verified transient IPC directories were renamed to preserved backups, after stopping Docker; settings, secrets, databases and volumes were not removed or reset. Startup then succeeded and the genuine disposable-PostgreSQL suite ran. These local runtime backups remain outside the repository; no Docker installation or ACTUAL infrastructure change was committed.

This is still unauthenticated local synthetic development. Classification cannot detect real prose mislabeled synthetic; no real-data permission, source authentication or independent verification has been introduced. A separately accepted access/security gate remains necessary before real personal sources. Small public shared-ancestry development fixtures are not held-out performance evidence.

Contextual sources describe their category only; scoped experience claims/matching remain deferred. Authored durations are not checked by calendar arithmetic, summed, deduplicated into independent sources or converted into freshness scores. Unknown dates remain unknown. The store retains current aggregate revisions, not a complete profile revision audit trail. Positive lower language evidence is not a proficiency ceiling. Missing evidence means no recorded support, not lack of skill. Education/certification ontology remains unimplemented at this checkpoint. UI and application preparation follow in their separately authorized roadmap phases.

The provisional implementation closes with a Phase-7 WIP checkpoint. Canonical acceptance remains pending; later development continues under ADR 0010. No acceptance tag is created.
