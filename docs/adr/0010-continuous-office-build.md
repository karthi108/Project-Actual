# ADR 0010: provisional continuous office development

Status: authorized development contract, 2026-10-06; canonical acceptance pending.

The latest [user instruction](../reference/office-continuous-build.md) supersedes the earlier stop-before-Phase-8 and acceptance-at-each-checkpoint rules. Accepted history remains Phases 0–6A at `bdc988a`; original Phase 6 remains NO-GO. The office device is a synthetic development environment. Its successful checks establish office verification, never canonical acceptance.

Develop Phases 7–27 incrementally on `office/continuous-build`, with one coherent `wip(phase-N)` checkpoint per phase and no acceptance tags. Preserve the existing Phase-7 implementation and verification. Continue between checkpoints without approval; stop for the user's stated hard blockers, including unsafe design, private-data/secret requirements or destruction of evaluation isolation.

The Phase-0 release contract and accepted phase records remain historical. The current scope adds the requested later capabilities progressively; it does not authorize real office systems, private accounts, unrestricted generated-code execution, paid runtime inference or production deployment. Keep deterministic authorization, exact approvals, provenance, audit and duplicate prevention at each affected boundary. Unavailable external integrations use contracts and synthetic harnesses, with real interoperability explicitly pending.

Maintain [office checkpoints and validation debt](../office-build/README.md). Run available meaningful checks, preserve failures and record unavailable environment gates. Canonical acceptance is performed later on the personal laptop, phase by phase. No corporate restrictions may be bypassed. Push only an already configured private remote with existing permitted credentials; the repository currently has no configured remote.

This approach preserves reviewable history and avoids misrepresenting office checks as acceptance. The cost is explicit validation debt and a second validation pass on the canonical environment. Optional infrastructure still requires a demonstrated need; the roadmap does not justify a generic framework in advance.
