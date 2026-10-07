# Continuous office build

Accepted base: `bdc988ae7cc00379e6b90f1cf22e6c6de192be61`. Development branch: `office/continuous-build`. Phases 0–6A retain their accepted status; original Phase 6 remains NO-GO. Phases 7–27 are provisional implementations, never accepted milestones. See [ADR 0010](../adr/0010-continuous-office-build.md) and the [preserved authorization](../reference/office-continuous-build.md).

Each phase has a separate WIP checkpoint. The implementation commit is located by its unique `wip(phase-N):` subject in `git log office/continuous-build`; later checkpoints record preceding hashes in the debt register. A commit cannot embed its own hash. No remote is configured, so checkpoints remain local until an authorized private remote exists.

| Phase | Implementation | Office checks | Canonical acceptance |
| --- | --- | --- | --- |
| 7 | Implemented; checkpoint `wip(phase-7): implement verified career profile` | Full dual-Python/real-PostgreSQL, typing/lint, integrity/replay and Qwen smoke passed | PENDING |
| 8 | Implemented; checkpoint `wip(phase-8): add career workflow interface` | Strict TypeScript, 22 unit tests, formatting, production build and 2 real Edge/API/PostgreSQL tests passed | PENDING |
| 9 | Implemented; checkpoint `wip(phase-9): add evidence-backed application preparation` | 1,467 tests on each Python version with real PostgreSQL; strict typing, frozen audit, web build and 3 browser journeys passed | PENDING |
| 10 | Implemented; checkpoint `wip(phase-10): add typed workflow IR` | Dual-Python adversarial graph/schema checks, typing and Ruff | PENDING |
| 11 | Implemented; durable PostgreSQL runtime | 22 workflow/runtime tests on each Python version, strict typing, Ruff and frozen integrity | PENDING |
| 12 | Implemented; typed fake connector boundary | 23 pure tests and 8 real-PostgreSQL runtime tests on both Python versions, typing and Ruff | PENDING |
| 13 | Implemented; exact approvals and durable fake effect intents | 41 combined checks on both Python versions; final 11 approval checks on both versions; typing, Ruff and frozen audit | PENDING |
| 14 | Implemented; isolated WorkLab replay | 26 pure checks on both Python versions; five deterministic development cases, typing and Ruff | PENDING |
| 15–27 | Development continues in roadmap order | Recorded at each checkpoint | PENDING |

[Validation debt](canonical-validation-pending.md) records actual checks and outstanding personal-environment validation. [Phase-7 verification](../phase-7/migration-verification.md) contains reproduced office results. Frozen evaluation records remain historical; deterministic replay is not fresh inference or independent held-out evidence.

Environment: Windows, portable uv 0.11.7, Python 3.13.13/3.14.4, disposable native PostgreSQL 18.6, Node 24.19.0, Ollama 0.34.3 and accepted `qwen3:4b-instruct` catalog digest `0edcdef34593eac1aa2be9c7d06c432dcf81945adca5eca2f27662c18f168ba0`. Tools/models/private runtime data stay ignored. Docker is unavailable. Some generated Python console launchers return access denied; equivalent module commands work. The cause is unestablished and security policy remains unchanged.

Architecture questions are resolved when a phase requires them. The first UI must preserve the existing API origin/Host restrictions; consequential fake actions must acquire deterministic authorization and recovery before execution. NEXUS, OAuth, cloud, voice device and browser-extension interoperability require later canonical integration evidence.
