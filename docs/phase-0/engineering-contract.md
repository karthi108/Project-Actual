# ACTUAL engineering contract v0.1

Date: 2026-10-04. Status: proposed baseline, reviewed for architecture and security; documentation only.

## 1. Problem and product thesis

A person preparing job applications repeats intake, requirement review, profile comparison, CV selection, drafting and tracking. Information is fragmented, advertised requirements may be ambiguous, and generated text can overstate skills. ACTUAL should reduce preparation/rework while preserving evidence, useful uncertainty and human control.

The broader thesis is to understand observed work, recommend simpler processes, and earn bounded automation through replay, shadow comparison and measured outcomes. v0.1 tests a useful career-assistance slice; it does not yet demonstrate process discovery or the full automation thesis.

Choose mechanisms in this order: eliminate unnecessary work, simplify it, integrate directly, use deterministic software, consider conventional ML, use an LLM for remaining semantic ambiguity, retain the human where reliability or authority is insufficient.

## 2. User and operating assumptions

One person owns a private local installation and is the only application user. The machine and OS account are trusted within stated limits. Browser content, imported documents and model output are untrusted. No real multi-tenant service exists in v0.1.

This release assumes local computer access, manual intake, local storage and a local model when Phase 5 begins. Remote phone access, cloud services and shared use require a later contract. Hardware capability and model size are unresolved until local inference is implemented; they do not block synthetic-world development.

Career is a domain module. Shared provenance/event concepts must not embed job-specific fields, but no speculative general workflow engine is built to achieve this separation.

## 3. Exact product v0.1 scope

| Capability | Bounded behavior | First relevant phase |
| --- | --- | --- |
| CareerLab | Repeatable synthetic jobs, profiles, CVs and application histories | 1 |
| Core data | Typed identifiers, requirements, claims, evidence and events | 2 |
| Local persistence | Only required tables and migrations | 3 |
| API | Typed, authenticated operations for the current career slice | 4 |
| Model proposal | Local Qwen through one typed ModelGateway adapter | 5 |
| Job intelligence | Extract requirements, confirm/correct them, assess support and gaps | 6 |
| Profile | Review evidence and explicit claim status; no automatic verification | 7 |
| Career interface | Jobs, applications, profile/skills, CVs and local settings | 8 |
| Preparation | Recommend a CV and factual draft changes, inspect evidence, review content | 9 |
| Tracking | User manually records submission and subsequent status | By 8-9 |

Intake is pasted job text plus optional manually supplied source metadata. v0.1 does not fetch a URL, crawl sites or parse arbitrary uploaded PDFs. CV variants begin as structured text with evidence-linked assertions; full document parsing/export is separately justified when needed.

Every assessment shows matched, partially supported, missing and unknown requirements. Employer-stated essentials are distinct from preferences. ACTUAL explains gaps without presenting a synthetic fit score as a hiring probability. The user chooses whether to pursue an opportunity.

No API keys or paid model APIs are necessary for ACTUAL runtime. Internet downloads of dependencies/model weights are separate from personal-data processing. Local inference failure leaves manual preparation available.

## 4. Explicit non-goals

- Automated applications, recruiter emails, external writes, scraping and browser automation.
- Connectors, scheduled discovery, calendar integration and automated follow-ups.
- A generic Workflow IR interpreter, durable workflow engine, replay/shadow activation or Teach Mode in the first release.
- Voice, desktop monitoring, invisible capture and unrestricted tool/shell execution.
- Cloud deployment, phone access, teams, enterprise tenancy, SSO and NEXUS integration.
- Kubernetes, Kafka, Redis, vector databases, multiple model providers and Temporal without a measured requirement.
- Employee scoring/ranking, application-volume optimization, fabricated skills or experience.

The master roadmap remains a direction, not permission to create every component now. Phase 0 delivers documents; product v0.1 spans several later engineering phases.

## 5. First CareerLab scenario: CAREER-DEV-001

This is a public development example, never a future locked-test case. Every person, company, job and artifact is synthetic.

**Job:** Example Company seeks an AI/backend engineer. Its synthetic text labels Python, FastAPI, strong Azure, French B2 and five years' experience essential; LLM integration is preferred. Those priorities are fixture facts, not assumptions inferred from the real user's job market.

**Profile:** synthetic project evidence supports Python, FastAPI and a local-model integration. Azure is a declared learning area, French A2 is a self-report, and documented experience covers one year. None of these facts is inferred from the real user's specification.

**CVs:** backend and AI-integration variants with assertion-to-evidence mappings. A deliberately unsafe candidate proposes French B2 and five years' experience.

**Expected behavior:** report support for the backend requirements, identify Azure/French/experience gaps, preserve self-report status, and recommend a suitable CV with an explanation. Block the unsafe additions from the recommended factual draft. Mark unknown requirements as unknown. Do not submit, send or claim the candidate has already applied.

The scenario's fit label is defined by a published rubric. It is not an objective prediction of employer decisions. Correctness includes admitting ambiguity and escalation.

## 6. First user journey

1. Add or review profile assertions and supporting records; retain claim status and source.
2. Paste a job, assign a local job identity, and preserve the original text privately.
3. Review extracted essentials/preferences and correct uncertain interpretations.
4. Inspect requirement-by-requirement support and important gaps.
5. Choose a CV recommendation and inspect suggested edits alongside sources.
6. Review the exact draft and unresolved claims. Revision invalidates its previous review state.
7. Submit manually using the employer's channel, outside ACTUAL.
8. Record applied/interview/offer/closed status and personal notes manually.

Reviewing a draft is an internal content state, not authority to submit it. A manually entered applied status is a user report, not proof of external delivery.

## 7. Success and release boundaries

v0.1 is useful when the owner can complete this journey, recover saved work, understand gaps and evidence, and continue if the model is unavailable. Quality is evaluated using [the evaluation strategy](evaluation-strategy.md), including unsupported-claim and privacy gates. Real time savings are measured against a recorded manual baseline, never estimated into existence.

Approval, authorization, replay, shadow operation and measured activation must precede any later external automation. Their absence in v0.1 is handled by excluding the capability entirely.

## 8. Teaching and delivery agreement

For each meaningful slice, explain what problem it solves, define invariants and failure behavior, implement the smallest coherent change, run relevant checks and review results. Ask for the user's reasoning when it advances understanding; do not make ordinary reversible engineering choices depend on repeated permission.

Record dependency compatibility when dependencies first appear. Record focused commits after verification. No phase completion, security property, benchmark or production-readiness claim substitutes for evidence.
