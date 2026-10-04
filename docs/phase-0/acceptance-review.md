# Phase-0 acceptance review

Date: 2026-10-04. Status: documentation baseline ready for user review. Architecture/security reviews are documented below; no runtime acceptance, application tests or product-readiness claim applies.

## Deliverable coverage

| Required deliverable | Reviewable artifact | Documentation criterion |
| --- | --- | --- |
| 1. Problem statement | [Contract](engineering-contract.md), section 1 | Concrete repetitive preparation problem and bounded product thesis |
| 2. Exact v0.1 scope | [Contract](engineering-contract.md), section 3 | Capabilities, boundaries and relevant engineering phases |
| 3. Non-goals | [Contract](engineering-contract.md), section 4 | External automation and later platform features explicitly deferred |
| 4. First CareerLab scenario | [Contract](engineering-contract.md), section 5 | Synthetic inputs, supported facts, gaps and blocked false claims |
| 5. First journey | [Contract](engineering-contract.md), section 6 | Intake through review/manual submission/status recording |
| 6. Trust boundaries | [Threat model](threat-model.md) | Untrusted origins/content/model and deterministic enforcement points |
| 7. Privacy boundaries | [Privacy](privacy.md) | Local flow, classification, retention, deletion and backups |
| 8. Threat model | [Threat model](threat-model.md) | Threat/control/evidence matrix and known residual risks |
| 9. Architecture | [Architecture](architecture.md) | Local modular monolith, staged topology and responsibilities |
| 10. Work Event principles | [Data principles](data-and-workflows.md) | Versioned facts, ownership, timing, allowlisted payload and deduplication |
| 11. Workflow IR principles | [Workflow principles](data-and-workflows.md) | Typed bounded data, registered capabilities and separated authority |
| 12. Repository structure | [Architecture](architecture.md) | Actual documentation-only tree and justified next additions |
| 13. Technical ADRs | [Decision register](../adr/0001-phase-0-decisions.md) | Problems, choices, alternatives, consequences and revisiting triggers |
| 14. Evaluation strategy | [Evaluation](evaluation-strategy.md) | Rubric, splits, label boundary, targets and honest reporting |
| 15. Acceptance criteria | This document | Coherent contract, no implementation, no unsupported claims |
| 16. Phase-1 plan | [CareerLab plan](phase-1-plan.md) | Small synthetic slice, tests and explicit stop condition |

## Architectural challenges resolved in the proposal

| Specification weakness | Contract correction |
| --- | --- |
| Hybrid/cloud drawing conflicts with local privacy/finish-sooner supplement | Local-only v0.1; server is a responsibility, cloud later |
| Broad target risks building enterprise before a useful product | Assistance release through phases 1-9; no general runtime/connector/capture yet |
| Everything described as communicating through localhost | Browser uses loopback; Compose service traffic uses internal network identities |
| 'Verified evidence' can imply guaranteed truth | Record assertion, support scope, reviewer and verification method; provenance is not certification |
| Mixed effect taxonomy and undefined EXTERNAL_WRITE example | Separate primary effect kind from risk, destination and reversibility |
| Workflow-version submission key can permit duplicate applications | Stable business intent independent of version, with explicit reapplication intent |
| Approval may outlive changes to files/authority | Bind content/destination/arguments and revalidate at dispatch |
| Replay/shadow safety and retries treated as implicit | Effect isolation, uncertain outcome and crash/concurrency checks are prerequisites |
| Late hardening phases could permit early unsafe capabilities | Baseline controls arrive with affected data/API/model/runtime/connector capability |
| Append-oriented audit conflicts with privacy deletion | Minimal metadata, explicit purge/redaction and deletion-aware backup restore |
| Hidden ground truth on an owner-controlled machine sounds absolute | Separate input/evaluator paths and disciplined freeze/exposure policy |

## Acceptance criteria for a defensible engineering contract

- All sixteen requested deliverables have concrete content, not placeholder folders.
- Release scope and phase scope are distinct; Phase 0 contains documentation only.
- Every planned technology has a concrete problem and introduction trigger.
- Model output and external content cannot grant authority or verify claims.
- Evidence states, local trust/data boundaries and known limits are explicit.
- Future external action design covers authorization, exact review, stable intent and uncertain outcomes.
- Evaluation distinguishes invariant checks, model quality and measured product value.
- Independent architecture and security reviews are incorporated; unresolved questions have a phase/trigger rather than unexplained assumptions.
- Documents link consistently and preserved source copies match the attachments.

## Review record and unresolved questions

The complete source documents were read. Independent architecture and security reviews converged on a local assistance release and identified the corrections above. Both reviewers inspected the completed contract and found no architecture/security blocker. Their final precision fixes were incorporated: the synthetic job priorities are explicit, factual rendering requires reviewed support covering the assertion, and approvals bind to one execution intent. No user answer is necessary to complete this documentation baseline.

Open later decisions: dependency versions/locks (Phase 1 onward), local data-root protection and retention implementation (Phase 3), local-owner authentication/CSRF details (Phase 4), actual GPU/RAM/model/config and performance (Phase 5), claim/paraphrase validation quality (Phases 6-9), UI component choices (Phase 8), final IR/state machine (Phases 10-11), and provider-specific effect recovery (before any external write). None is claimed to be solved now.

This contract is a proposed, reviewed baseline. User acceptance of the product scope has not been recorded. This turn stops at Phase 0 as requested; the Phase-1 plan is ready for a later continuation. No accepted-milestone tag is created before acceptance.

## Verification record

- Both preserved specification files match their attachment bytes. SHA-256: master `0acac522d9ce6e80ad2f5d1a3eb01404632b66ce54549a5fd100741ea42959b5`; supplement `9fea032f89cee9d90dbdd999babe4ea2da8f7b0c966244621690e88dbb4bfde4`. Git attributes preserve those bytes rather than normalizing their line endings.
- All 34 local Markdown links in authored documents resolve. Authored code fences are balanced.
- Staged whitespace checks pass, the preserved-source text attributes are unset, and representative secrets/private data/withheld-label paths are ignored by Git.
- The workspace contains 16 documentation/Git-hygiene files, with no application code, dependency manifest or service configuration.
- Independent architecture and security reviews completed with no remaining Phase-0 blocker after the recorded corrections.
- No application tests, model evaluations, service startup, security tests or performance benchmarks ran: there is no application implementation.

Environment note: the restricted command helper reported a setup-refresh error after repository initialization. Final checks ran successfully through host execution. Git's safe-directory configuration now includes only this ACTUAL path as the new trust entry, addressing its sandbox-owner mismatch for host Git; restricted-helper recovery remains unresolved. No remote was configured or content published.
