# Canonical validation debt

All office checkpoints remain CANONICAL ACCEPTANCE PENDING. Passing office checks does not change this status. Validate each phase before accepting dependent phases.

## Phase 7 — Verified Career Profile

- Implementation commit: `e23d24d67f709fbf7e40e0d91a306c3af9d6a997` on `office/continuous-build`.
- Implementation: IMPLEMENTED; existing reviewed changes preserved.
- Checks run here: Python 3.13.13 and 3.14.4, 1,456 passed each, zero skipped, real native PostgreSQL 18.6; Ruff lint/format; strict mypy both targets; CareerLab integrity; 87/87 retained-source replay; exact OpenAPI/snapshot and accepted artifact preservation; cloud-disabled owned-loopback Qwen smoke on both interpreters. Exact results in [verification record](../phase-7/migration-verification-v1.json).
- Checks not run here: canonical personal-laptop suite, Docker harness, new live Job Intelligence accuracy evaluation, real-source authentication/security acceptance.
- Environment dependency: supported Python branches, disposable PostgreSQL, Docker for the documented default harness; accepted Ollama/model for live evaluations.
- Security validation pending: canonical adversarial review; synthetic-only unauthenticated local boundary cannot authorize real data.
- Live integration pending: canonical Qwen evaluations; synthetic source review never verifies a real person.
- Canonical acceptance: PENDING.

## Phase 8 — Career workflow interface

- Implementation commit: unique subject `wip(phase-8): add career workflow interface` on `office/continuous-build`.
- Implementation: IMPLEMENTED / OFFICE VERIFIED, 2026-10-07.
- Checks run here: generated TypeScript from unchanged OpenAPI; strict TypeScript; 22 Vitest transport/client tests; Prettier; Next production build; Ruff and strict mypy (3.13/3.14 targets) for browser API helper; CareerLab integrity and protected artifact audit; two real headless Edge tests through Next bridge, FastAPI and an owned disposable native PostgreSQL 18.6 cluster. Review/withdraw/status transitions and cross-site rejection passed. Owned services/cluster were stopped/removed. Synthetic screenshot visually inspected.
- Checks not run: full Python suite repeated at this checkpoint (product Python sources unchanged), canonical browser matrix/accessibility audit, Docker/browser runtime on personal laptop, dedicated frontend lint/security scanner.
- Environment dependency: Node 24.19.0, pnpm 11.19.0, Edge and existing Python/PostgreSQL; no global installs or browser download. Strict seven-day release-age resolution, exact pins/integrity hashes and lifecycle scripts disabled.
- Security validation pending: canonical adversarial/CSRF/host/proxy review, CSP nonce policy (inline framework scripts/styles currently allowed), accessibility and additional browser/viewport cases. The serializer's generic EvidenceRecord output schema remains a contract precision limitation; UI display fields are narrowed from unknown values instead of inventing a second schema.
- Live integration pending: personal canonical FastAPI/PostgreSQL/browser validation; no real-data permission or external-account integration. No fresh Qwen accuracy claim.
- Known office findings: exact comparison to Next's normalized internal URL rejected legitimate browser reads; admitted local URL aliases with exact browser Host/Origin binding fixed it. Evidence detail expansion closed during a generation refresh; explicit UI expansion state fixed it. Source content/provenance is visible before review. Failed attempts remain recorded as findings; the final real journey passed.
- Canonical acceptance: PENDING.

## Phase 9 — Application Preparation

- Implementation commit: unique `wip(phase-9): add evidence-backed application preparation` checkpoint.
- Implementation: IMPLEMENTED. Controlled source-linked CV adaptation, messages and letters; transient CV comparison; exact content review and revision invalidation.
- Checks run here: Python 3.13.13 and 3.14.4, 1,467 tests passed each against a fresh native PostgreSQL 18.6 database; strict mypy; Ruff; 22 frontend unit tests, TypeScript, formatting and production build; 3 real Edge/bridge/API/PostgreSQL journeys; 46 accepted and 2 frozen Phase-7 artifacts preserved.
- Failed attempts preserved: JSON arrays initially rejected by strict command tuples; review initially violated the accepted record revision rule; timestamp-tied event ordering made an assertion nondeterministic; tracking form selection raced an aggregate refresh. Fixed at the respective boundary, without weakening the contract. Final full dual-Python and browser reruns passed. Sandboxed initdb could not create a restricted token; existing permitted native harness ran outside the sandbox and removed its own disposable cluster.
- Checks not run / environment dependency: Docker, canonical personal environment, additional browsers and accessibility review.
- Security validation pending: canonical authority, stale-content, origin and adversarial review. No real-data intake, external submission or effect approval introduced.
- Live integration pending: canonical browser/API/PostgreSQL validation. Templates are sparse and deterministic; no new Qwen inference or accuracy claim.
- Known limitations: UI comparison accepts one quote, API up to eight; dependency-changing edits require explicit reconciliation and are rejected while prepared references depend on them. Content review is not external-action approval.
- Canonical acceptance: PENDING.

## Phases 10–27

Implementation and check records are added as each phase is developed. No unavailable integration is represented as working. No final green command accepts the entire roadmap.
