ACTUAL — CONTINUOUS DEVELOPMENT MODE

Continue the existing ACTUAL repository from the current working tree exactly as it exists.

This is NOT a new project.

Do NOT restart Phase 7.

Do NOT reset or discard existing Phase-7 work.

You are now authorized to continue building ACTUAL through the remaining roadmap without stopping after every phase for user approval.

However, this office laptop is a:

DEVELOPMENT / BUILD ENVIRONMENT

It is NOT the canonical final acceptance environment.

The user’s personal laptop will later perform the canonical:

* full regression verification;
* PostgreSQL acceptance;
* migration acceptance;
* live Qwen evaluations;
* security verification;
* browser/E2E validation;
* Docker/runtime validation;
* cloud/deployment validation where applicable;
* final phase acceptance.

Therefore:

Build continuously here.
Preserve phase boundaries.
Commit every phase separately as provisional/WIP.
Never falsely claim final acceptance.

⸻

1. CURRENT ACCEPTED BASELINE

The accepted history before the current office work is:

Phase 0   Engineering Contract        ✅ 4e06cc6
Phase 1   CareerLab                   ✅ 5b6116a
Phase 2   Core Contracts              ✅ fc6d396
Phase 3   PostgreSQL Persistence      ✅ d2a7544
Phase 4   FastAPI Boundary            ✅ 7deff65
Phase 5   Local Qwen Gateway          ✅ 09d7653
Phase 6   Original Job Intelligence   ❌ NO-GO
Phase 6A  Job Intelligence Hardening  ✅ bdc988a

The original Phase-6 NO-GO evidence must remain preserved.

Do NOT rewrite accepted history.

Do NOT remove failed Phase-6 evidence.

⸻

2. CURRENT PHASE-7 STATE

Phase 7 work already exists in the working tree.

A previous office session reproduced significant verification including:

* Python 3.13.13: 1,456 tests passed, zero skipped;
* Python 3.14.4: 1,456 tests passed, zero skipped;
* lint passed;
* formatting passed;
* strict typing passed;
* CareerLab integrity passed;
* retained-source replay: 87/87;
* accepted job/profile snapshots unchanged;
* seven historical manifests preserved;
* disposable PostgreSQL 18.6 verification succeeded;
* accepted Qwen model/catalog digest restored;
* local Qwen smoke tests passed on both Python versions;
* cloud-disabled loopback model execution;
* accepted configuration preserved.

Known environment limitation:

* Windows-generated console launchers produced access-denied behavior;
* equivalent python -m ... commands worked.

Treat these as office verification results, not final canonical project acceptance.

Inspect the current tree before continuing.

Preserve valid Phase-7 work.

⸻

3. GIT STRATEGY FOR CONTINUOUS OFFICE BUILD

Do NOT continue accumulating everything as one uncommitted working tree.

First inspect:

git status
git diff --stat
git log --oneline -10
git branch --show-current

If currently on main, create a dedicated development branch while preserving the existing Phase-7 working tree.

Preferred concept:

office/continuous-build

Do not rewrite accepted main history.

Each completed implementation phase must receive its own non-acceptance checkpoint commit.

Examples:

wip(phase-7): implement verified career profile
wip(phase-8): add career workflow interface
wip(phase-9): add evidence-backed application preparation
wip(phase-10): add typed workflow IR
...

Do NOT use:

phase-7-complete
accepted
production-ready
release

No accepted milestone tags.

No final acceptance tags.

These commits are development checkpoints for later canonical validation.

⸻

4. AUTOMATIC CONTINUATION RULE

After completing the implementation scope of one phase:

1. review the diff;
2. run appropriate checks that are safely available here;
3. record what was and was not verified;
4. create the WIP checkpoint commit;
5. continue automatically to the next phase.

Do NOT wait for user approval between phases.

Continue unless one of these occurs:

HARD BLOCKER

Stop only if:

* an accepted contract fundamentally contradicts the next implementation;
* required source code/repository is unavailable;
* continuing would require fabricating security behavior;
* continuing would require real company/private data;
* continuing would require unavailable secrets/credentials;
* continuing would destroy accepted data/evaluation isolation;
* repository corruption or unexplained Git history appears;
* a design flaw makes later work unsafe to continue.

A failed quality gate on this office machine should normally become:

IMPLEMENTED
CANONICAL VALIDATION PENDING

rather than pretending the phase passed.

But if implementation itself is known to be unsafe, stop rather than stacking future work on broken architecture.

⸻

5. TESTING RULE ON OFFICE LAPTOP

Do not postpone all engineering checks.

Still run what is practical here:

* unit tests;
* deterministic contract tests;
* pure integration tests;
* lint;
* formatting;
* typing;
* schema checks;
* non-destructive migration checks;
* synthetic CareerLab checks;
* mocked connector tests;
* static security checks where available.

However:

Do NOT treat this machine as the canonical acceptance environment.

Do NOT weaken a test merely because this machine cannot run it.

Do NOT bypass corporate restrictions.

Do NOT install prohibited software or require administrator-policy bypasses.

For environment-dependent validation that cannot be reproduced here:

record it as:

PENDING_CANONICAL_VALIDATION

⸻

6. PRIVACY / OFFICE MACHINE RULE

This is an office laptop.

Do NOT introduce:

* real personal CVs;
* real application history;
* private Gmail;
* private calendar;
* OAuth refresh tokens;
* passwords;
* personal API credentials;
* company confidential data;
* DRIVECO production data;
* employee data;
* private browser-history capture;
* private ACTUAL Teach Mode recordings.

Use:

* CareerLab;
* WorkLab;
* synthetic fixtures;
* fake credentials;
* test connectors;
* local development data.

Source code and synthetic evaluation data only.

⸻

7. MODEL RULE

Current runtime direction remains:

ACTUAL
   ↓
ModelGateway
   ↓
Ollama
   ↓
Qwen

Do NOT introduce paid runtime models.

No:

OpenAI API
Anthropic API
Gemini API
paid inference API

unless explicitly requested in a future project decision.

Codex itself is a development assistant and is separate from ACTUAL runtime.

Do not silently change the accepted Qwen model/configuration.

⸻

8. CORE ACTUAL PRINCIPLES

Preserve throughout every remaining phase:

LLM output = untrusted proposal
claim ≠ verified evidence
model output ≠ verified fact
no evidence → cannot satisfy requirement
AI cannot grant itself authority
external side effect requires deterministic authorization
approval must bind to what was reviewed
one duplicated event must not cause duplicate side effects
every consequential action must eventually be auditable
automation improvement must eventually be measurable

Prefer safe abstention over fabricated precision.

Prefer deterministic software over AI where appropriate.

⸻

9. PRODUCT PRINCIPLE

Never ask:

Can we use AI here?

Ask:

What is the cheapest, safest and most reliable mechanism that can correctly perform this work?

Decision hierarchy:

ELIMINATE
   ↓
SIMPLIFY
   ↓
INTEGRATE
   ↓
API
   ↓
DETERMINISTIC SOFTWARE
   ↓
CONVENTIONAL ML
   ↓
LLM
   ↓
HUMAN

⸻

10. REMAINING ROADMAP

Continue through:

Phase 7   Verified Career Profile
Phase 8   Career Workflow UI
Phase 9   Application Preparation
Phase 10  Workflow IR
Phase 11  Persisted Workflow Runtime
Phase 12  Connectors
Phase 13  Human Approval
Phase 14  Historical Replay
Phase 15  Shadow Mode
Phase 16  Controlled Personal Activation
Phase 17  Teach Mode
Phase 18  Process Discovery
Phase 19  Voice Teach Mode
Phase 20  Improvement Engine
Phase 21  General Personal Workflows
Phase 22  NEXUS Integration
Phase 23  Reliability Hardening
Phase 24  Security Hardening
Phase 25  Cloud / Production-like Deployment
Phase 26  Pro / Teams
Phase 27  Enterprise Research

Implementation should remain incremental.

Do not pre-build later concepts inside earlier phases without justification.

⸻

PHASE 7 — VERIFIED CAREER PROFILE

Continue and finish the existing implementation.

Goal:

Build a trustworthy structured, evidence-backed career profile that Job Intelligence can consume.

Required behavior:

* claims;
* evidence;
* provenance;
* capability representation;
* experience categories;
* language evidence;
* education/certification evidence where justified;
* deterministic profile projection;
* integration with Phase-6A Job Intelligence.

Hard invariants:

claim ≠ verified evidence
AI proposal ≠ verified fact
internship ≠ professional employment
personal project ≠ professional employment
missing evidence ≠ evidence of absence

Never manufacture professional duration.

Conflicting evidence must remain explicit.

Do not add CV writing yet.

Create Phase-7 WIP checkpoint commit.

Continue automatically.

⸻

PHASE 8 — CAREER WORKFLOW UI

Goal:

Create the first genuinely usable ACTUAL interface.

Use the already planned frontend direction:

* Next.js;
* React;
* TypeScript;
* Tailwind;
* shadcn/ui;
* TanStack Query;
* TanStack Table;
* React Flow only where graph visualization is genuinely useful;
* Vitest;
* Playwright.

Do not make ACTUAL primarily a chatbot.

Initial product navigation may include:

Overview
Career
 ├─ Jobs
 ├─ Profile
 ├─ Skills
 └─ Applications
Settings

Useful states:

Discovered
Prioritized
Rejected
Preparing
Ready for Review
Applied
Interview
Offer
Closed

The UI should use existing FastAPI use cases rather than bypassing backend architecture.

Do not put business logic in React.

Do not enable real-data workflows if accepted security boundaries still prohibit them.

Build using synthetic/local development data.

Add frontend tests where practical.

Checkpoint commit:

wip(phase-8): add career workflow interface

Continue automatically.

⸻

PHASE 9 — APPLICATION PREPARATION

Goal:

Produce evidence-backed application materials without fabrication.

Implement only the preparation side:

* appropriate CV selection;
* truthful CV adaptation suggestions;
* application-message preparation;
* cover-letter preparation where useful;
* human review.

Every generated professional claim must be traceable to:

verified/supported evidence

or explicitly labelled:

unverified user claim

Do not fabricate:

* years;
* skills;
* language proficiency;
* certification;
* employment;
* achievements.

Do not automatically submit anything.

No spam application automation.

Do not use real personal data on this office device.

Use synthetic fixtures.

Checkpoint commit.

Continue automatically.

⸻

PHASE 10 — TYPED WORKFLOW IR

Goal:

Generalize ACTUAL from Career-specific orchestration into a typed workflow representation.

Do NOT execute arbitrary AI-generated Python.

Create the smallest typed IR justified by current workflows.

Potential step types:

TRIGGER
DETERMINISTIC
AI
TOOL
POLICY
HUMAN_APPROVAL
BRANCH
WAIT
TERMINATE

Every executable step should eventually support appropriate metadata such as:

input schema
output schema
timeout
retry policy
idempotency strategy
required permissions
side-effect class
failure behavior
human-review requirement
data classification

AI may propose Workflow IR.

AI does not directly execute it.

Add structural/static validation.

Invalid workflows must fail closed.

Checkpoint commit.

Continue automatically.

⸻

PHASE 11 — PERSISTED WORKFLOW RUNTIME

Goal:

Build the first durable runtime using existing PostgreSQL architecture.

Learn and implement:

* workflow instances;
* step states;
* durable progress;
* retries;
* bounded backoff;
* timeouts;
* wait states;
* human wait states;
* idempotency;
* crash recovery;
* terminal states.

Do NOT introduce Temporal yet unless the current runtime objectively cannot satisfy accepted requirements.

A workflow must survive application-process restart.

External effects must eventually be idempotent.

Do not create real external side effects yet unless using controlled fake connectors.

Checkpoint commit.

Continue automatically.

⸻

PHASE 12 — CONNECTORS

Goal:

Introduce controlled external-system boundaries.

Prefer APIs over browser automation.

Create a connector/tool interface separate from model logic.

Potential future connectors:

* Gmail;
* Calendar;
* files;
* job-source intake;
* generic HTTP/API connectors.

On this office environment:

Do NOT connect to the user’s actual Gmail/Calendar/accounts.

Use:

* fake connectors;
* synthetic provider fixtures;
* contract tests.

A connector must define:

* capability;
* typed inputs;
* typed outputs;
* side-effect class;
* permission requirements;
* idempotency behavior where relevant;
* safe error mapping.

The model never sees raw secrets.

Checkpoint commit.

Continue automatically.

⸻

PHASE 13 — HUMAN APPROVAL

Goal:

Make consequential actions impossible without appropriate approval.

Approval should bind to what was reviewed.

Conceptually:

workflow_version
action
relevant argument hash
approver
expiration
policy/version

Changing consequential inputs should invalidate the approval when appropriate.

Approval must not be a vague:

approve workflow forever

Build deterministic approval-state transitions.

Checkpoint commit.

Continue automatically.

⸻

PHASE 14 — HISTORICAL REPLAY

Goal:

Test candidate workflows against controlled historical/synthetic executions before activation.

Conceptually:

candidate workflow
        ↓
historical/synthetic cases
        ↓
replay
        ↓
expected vs produced result

Measure appropriate outcomes:

* branch correctness;
* completion;
* policy violations;
* invalid tool calls;
* human escalation;
* unsupported AI claims;
* workflow failures.

Keep replay isolated from real side effects.

CareerLab / WorkLab synthetic sources should be used.

Do not claim real-world performance.

Checkpoint commit.

Continue automatically.

⸻

PHASE 15 — SHADOW MODE

Goal:

Allow ACTUAL to process a live-like case without producing consequential writes.

Architecture:

INPUT
 │
 ├────────→ HUMAN / EXPECTED PATH
 │
 └────────→ ACTUAL SHADOW
                │
             NO WRITES

Record disagreement.

Support capability/step-level readiness rather than entire-workflow autonomy.

Example:

job extraction       READY
fit analysis         READY
CV adaptation        SHADOW
submission           HUMAN

Checkpoint commit.

Continue automatically.

⸻

PHASE 16 — CONTROLLED PERSONAL ACTIVATION

Goal:

Allow only explicitly approved safe capabilities to execute.

Implement activation states at capability/step level.

External side effects must require:

validated workflow
+
permission
+
approval where required

Do not use the office machine for real personal-account activation.

Use controlled fake/synthetic connectors.

Build the architecture and tests only.

Checkpoint commit.

Continue automatically.

⸻

PHASE 17 — TEACH MODE

Goal:

Introduce explicit user-controlled semantic-work capture.

Do NOT create hidden surveillance.

Teach Mode requires:

* explicit start;
* visible active state;
* stop;
* pause;
* application allowlist;
* denylist;
* sensitive-field exclusion;
* password exclusion;
* local preprocessing;
* session identity.

Prefer semantic events over permanent raw capture.

Example:

job.open
company.research
cv.compare
application.prepare
tracker.update

Do not assume one demonstration represents a complete process.

One session = one observed example.

Checkpoint commit.

Continue automatically.

⸻

PHASE 18 — PROCESS DISCOVERY

Goal:

Reconstruct repeated workflow structure from Work Events.

Use deterministic algorithms where possible for:

* session grouping;
* repeated sequences;
* variants;
* transitions;
* branch points;
* loops;
* rework;
* duration;
* bottlenecks.

Keep the ACTUAL domain independent of any optional process-mining library.

If PM4Py is evaluated/used, isolate it behind ACTUAL’s contracts and review licensing implications.

Evaluate against synthetic processes where ground truth exists.

Checkpoint commit.

Continue automatically.

⸻

PHASE 19 — VOICE TEACH MODE

Goal:

Capture WHY unusual work decisions occur.

Preferred local direction:

microphone
   ↓
explicit recording
   ↓
local STT
   ↓
transcript
   ↓
privacy filtering
   ↓
candidate structured rule
   ↓
human confirmation

Prefer local speech recognition such as faster-whisper where practical.

A voice statement is:

human_claim

not:

company_policy

Do not require always-on audio.

Do not record office conversations or company-confidential information on this machine.

Build/test with synthetic audio/text fixtures.

Checkpoint commit.

Continue automatically.

⸻

PHASE 20 — IMPROVEMENT ENGINE

Goal:

Recommend what should happen to observed activities.

Classification:

ELIMINATE
SIMPLIFY
INTEGRATE
DETERMINISTIC
AI_ASSISTED
HUMAN

Every recommendation requires evidence/reasoning.

Do not automatically choose AI.

Example:

copy structured ID
→ deterministic
look up record
→ API
interpret ambiguous complaint
→ AI-assisted
high-consequence approval
→ human

Do not automatically automate inefficient steps.

Sometimes the recommendation must be:

REMOVE THIS STEP

Checkpoint commit.

Continue automatically.

⸻

PHASE 21 — GENERAL PERSONAL WORKFLOWS

Goal:

Prove ACTUAL is not permanently a job-search application.

Add only a few generalized workflow families built on the same engine.

Candidates:

* meeting → actions;
* email triage;
* document processing;
* research workflow;
* personal administration.

Do NOT build dozens of superficial integrations.

Choose the smallest set that proves generality.

Use synthetic/local-safe data on the office machine.

Checkpoint commit.

Continue automatically.

⸻

PHASE 22 — NEXUS INTEGRATION

Goal:

Integrate ACTUAL’s authorization boundary with NEXUS.

Expected abstraction:

AuthorizationPort
├── LocalPolicyAuthorizer
└── NexusAuthorizer

ACTUAL must remain usable without NEXUS.

NEXUS should answer:

Is this workflow/actor allowed
to perform this specific action
on this specific resource
under this context?

AI cannot bypass it.

If the NEXUS repository/service is NOT available in this environment:

DO NOT fake a working integration.

Instead implement:

* ACTUAL-side adapter contract;
* protocol/interface;
* integration test harness/fake server;
* documented expected request/response semantics.

Mark real NEXUS interoperability:

PENDING_CANONICAL_INTEGRATION

Checkpoint commit.

Continue automatically.

⸻

PHASE 23 — RELIABILITY HARDENING

Goal:

Deliberately break ACTUAL.

Test/design for:

* duplicate event;
* duplicate webhook;
* worker crash;
* process restart;
* DB reconnect;
* connector 429;
* connector 500;
* model timeout;
* malformed model output;
* OAuth expiry;
* stale approval;
* revoked permission;
* lost response after successful side effect;
* workflow loop;
* retry exhaustion.

Add:

* bounded retries;
* jitter/backoff where appropriate;
* dead-letter state;
* compensation where possible;
* recovery;
* idempotency enforcement.

Do not hide failures.

Checkpoint commit.

Continue automatically.

⸻

PHASE 24 — SECURITY HARDENING

Goal:

Attack ACTUAL deliberately.

Threat cases should include:

* prompt injection;
* malicious documents;
* malicious job postings;
* fake evidence;
* cross-object IDOR;
* cross-tenant access where tenancy exists;
* OAuth scope abuse;
* SSRF;
* arbitrary URL access;
* secret extraction;
* tool output injection;
* stale/replayed approval;
* tampered Workflow IR;
* workflow changed after approval;
* privilege escalation;
* duplicate side effects;
* malicious connector content.

Security principle:

AI text ≠ authorization

No model gets:

* DB password;
* OAuth refresh token;
* cloud admin secret;
* unrestricted shell;
* Docker socket.

Use static/adversarial tests available locally.

Record canonical security validation pending where necessary.

Checkpoint commit.

Continue automatically.

⸻

PHASE 25 — CLOUD / PRODUCTION-LIKE DEPLOYMENT

Goal:

Prepare ACTUAL for reproducible deployment.

Target direction:

OVHcloud
+
Docker
+
PostgreSQL
+
Terraform
+
GitHub Actions
+
TLS
+
OpenTelemetry

Do NOT deploy from the office laptop using private/personal cloud credentials.

Build:

* Dockerfiles;
* Compose production-like config where appropriate;
* Terraform modules/configuration;
* deployment documentation;
* environment configuration;
* secret interfaces;
* health/readiness behavior;
* CI workflows;
* backup/recovery plan;
* OpenTelemetry instrumentation/config;
* deployment verification scripts.

Cloud deployment itself may remain:

PENDING_PERSONAL_ENVIRONMENT

No Kubernetes unless a concrete demonstrated requirement exists.

Checkpoint commit.

Continue automatically.

⸻

PHASE 26 — PRO / TEAMS

Goal:

Generalize single-user ACTUAL toward shared organizational usage.

Add only minimum architecture justified for:

* organizations/workspaces;
* multiple users;
* roles;
* shared workflows;
* shared approvals;
* shared connector references;
* organization policy;
* tenant-aware data boundaries.

Security is critical.

Do not assume a tenant ID parameter is sufficient isolation.

Test tenant boundaries deterministically.

Do not introduce employee ranking/productivity scoring.

Checkpoint commit.

Continue automatically.

⸻

PHASE 27 — ENTERPRISE RESEARCH / READINESS

This phase is NOT “build SAP.”

Goal:

Establish what ACTUAL would require to become a credible enterprise platform.

Research/design/implement only where justified:

* enterprise SSO/OIDC;
* SCIM/provisioning considerations;
* stronger tenant isolation;
* enterprise secrets;
* large-scale process-event ingestion;
* organization process intelligence;
* data retention/deletion;
* privacy controls;
* audit/export;
* compliance evidence;
* enterprise connectors;
* workload identity;
* policy governance;
* durable workflow scaling;
* Temporal evaluation if current runtime complexity now justifies it;
* isolation strategy for untrusted execution;
* operational runbooks;
* backup/restore;
* disaster recovery;
* SLA/SLO strategy.

Do NOT automatically adopt every enterprise technology.

Produce ADRs for major decisions.

Any implementation requiring unavailable external enterprise systems should use contracts/harnesses and be marked pending real integration.

Create Phase-27 WIP checkpoint commit.

⸻

11. OPTIONAL TEMPORAL DECISION

Do not assume Temporal must be introduced.

After the existing persisted runtime has enough complexity, evaluate:

current runtime complexity
failure recovery needs
long-running workflows
human waits
operational burden

If Temporal clearly solves a demonstrated problem:

create an ADR and adopt it carefully.

If not:

keep the existing runtime.

⸻

12. OPTIONAL REDIS DECISION

Do not introduce Redis unless needed for a demonstrated requirement such as:

* distributed cache;
* rate limiting;
* coordination;
* ephemeral state.

PostgreSQL remains the primary source of truth.

⸻

13. OPTIONAL VECTOR SEARCH

Do not introduce a separate vector database.

If semantic retrieval becomes justified:

evaluate PostgreSQL + pgvector first.

Do not add retrieval simply because the system contains AI.

⸻

14. NO ARBITRARY GENERATED CODE

Do not let AI generate arbitrary Python/shell and immediately execute it.

Workflow IR + typed tools remain the safe path.

If later code execution becomes genuinely required:

use isolated sandbox design with:

* no secrets;
* non-root;
* read-only filesystem where possible;
* CPU/RAM/PID/time limits;
* network denied by default;
* no Docker socket;
* no host mounts.

But do not introduce a complex sandbox unless needed.

⸻

15. OBSERVABILITY

Progressively instrument important boundaries.

Expected future correlation:

trace_id
workflow_run_id
workflow_version
model_run_id
tool_execution_id
authorization_decision_id

Use OpenTelemetry direction.

No secrets or full sensitive content in logs.

⸻

16. AUDIT

Every consequential action should eventually answer:

WHO
did WHAT
WHEN
to WHICH RESOURCE
with WHICH WORKFLOW VERSION
under WHICH AUTHORITY
based on WHICH EVIDENCE
after WHICH APPROVAL
with WHAT RESULT

Use ordinary append-oriented relational audit architecture.

No blockchain.

⸻

17. IMPACT MEASUREMENT

Do not invent ROI.

Prepare ACTUAL to measure:

* human active time;
* end-to-end duration;
* automation coverage;
* human intervention;
* error/rework;
* workflow success;
* policy denial;
* inference latency;
* model calls;
* compute cost;
* connector failures;
* exception frequency.

Later compare:

MANUAL
vs
ASSISTED
vs
PARTIALLY AUTOMATED

Only measured outcomes may be reported.

⸻

18. README / DOCUMENTATION DISCIPLINE

Because phases are not canonically accepted here, documentation must distinguish:

IMPLEMENTED
OFFICE VERIFIED
CANONICAL ACCEPTANCE PENDING

Do not write:

Phase X accepted
Phase X production-ready

unless the personal canonical process later establishes that.

Maintain:

docs/office-build/

or the repository-appropriate equivalent containing:

* phase checkpoint map;
* verification debt;
* environment limitations;
* pending canonical tests;
* known architectural questions.

Avoid duplicating accepted phase documentation unnecessarily.

⸻

19. VALIDATION DEBT REGISTER

Maintain a machine-readable or clearly structured document such as:

docs/office-build/canonical-validation-pending.md

For every phase record:

Phase:
Implementation commit:
Checks run here:
Checks not run:
Environment dependency:
Security validation pending:
Live integration pending:
Canonical acceptance:
PENDING

This document will be used on the personal laptop later.

⸻

20. DO NOT TOUCH REAL OFFICE SYSTEMS

Do NOT connect ACTUAL to:

* company Gmail;
* company Microsoft account;
* company calendar;
* company internal applications;
* company production APIs;
* DRIVECO databases;
* internal tickets;
* confidential PDFs;
* employees;
* production credentials.

No real workplace automation from this device.

Synthetic/local development only.

⸻

21. BUILD QUALITY

Do not optimize for:

* number of files;
* test count;
* lines of code;
* technologies;
* “agentic” appearance.

Optimize for:

* correctness;
* maintainability;
* privacy;
* security;
* reproducibility;
* evidence;
* explicit failure behavior;
* learning value.

Do not generate giant generic frameworks.

Use explicit code.

⸻

22. EACH PHASE CHECKPOINT

Before each WIP phase commit:

1. inspect git diff;
2. remove accidental temporary/private files;
3. run available relevant checks;
4. document checks skipped;
5. update canonical-validation debt;
6. commit only that phase’s coherent changes.

Do not squash all remaining phases into one commit.

⸻

23. PUSH STRATEGY

If a private Git remote is already configured and pushing does not require introducing new credentials or violating machine policy:

push the development branch periodically, preferably after meaningful checkpoint commits.

At minimum push the final continuous-build branch before handoff.

Do not force-push accepted history.

If push is unavailable:

leave the complete Git history locally and clearly report this.

⸻

24. FINAL OFFICE-LAPTOP HANDOFF

After Phase 27 development scope has been reached, do NOT declare ACTUAL complete.

Instead create a final handoff document containing:

Git

* branch;
* accepted base commit;
* all WIP checkpoint commits;
* current HEAD;
* working-tree state.

Phase Matrix

For each Phase 7–27:

IMPLEMENTED?
OFFICE CHECKS?
CANONICAL VALIDATION PENDING?
KNOWN LIMITATIONS?

Environment

* Python versions;
* PostgreSQL version;
* Node version;
* Ollama version;
* accepted Qwen identifier/digest;
* operating-system limitations.

Validation Commands

Provide exact commands for the personal laptop to verify:

* Python 3.13;
* Python 3.14;
* PostgreSQL;
* migrations;
* CareerLab;
* model gateway;
* Phase-6A regression;
* frontend;
* Playwright;
* workflow runtime;
* replay;
* shadow mode;
* security tests;
* reliability tests;
* Docker;
* Terraform formatting/validation;
* CI configuration.

Unavailable Integrations

Clearly identify anything that still requires:

* personal Gmail;
* personal Calendar;
* NEXUS service;
* OVHcloud;
* browser extension runtime;
* real voice device;
* real deployment;
* OAuth;
* domain/TLS.

No pretending.

⸻

25. FINAL STATUS

At the end of this office build, the correct status is:

ACTUAL Phases 7–27 have been implemented to the extent possible in the office development environment with phase-separated WIP commits. Final canonical validation and acceptance remain pending on the personal laptop.

NOT:

ACTUAL is production-ready.

NOT:

All phases are accepted.

NOT:

Enterprise deployment verified.

⸻

26. PERSONAL-LAPTOP FUTURE WORKFLOW

Prepare everything so the personal laptop can later:

clone/pull development branch
        ↓
review commit history
        ↓
validate Phase 7 checkpoint
        ↓
validate Phase 8 checkpoint
        ↓
validate Phase 9 checkpoint
        ↓
...
        ↓
validate Phase 27 checkpoint

If a phase fails canonical validation:

fix that phase before accepting later dependent phases.

Do not rely on one final green command to accept the entire project.

⸻

27. BEGIN NOW

Resume from the current dirty Phase-7 working tree.

First:

1. inspect current changes;
2. determine exactly what Phase-7 work is already complete;
3. preserve valid work;
4. move onto a dedicated continuous-build branch if appropriate without losing changes;
5. clean accidental temporary files;
6. finish Phase 7 implementation;
7. make the Phase-7 WIP checkpoint commit;
8. continue automatically through the roadmap above.

Do not ask the user to approve every phase.

Do not stop after each checkpoint.

Stop only for a genuine hard blocker as defined above.

Otherwise continue through Phase 27 and produce the final office-development handoff.