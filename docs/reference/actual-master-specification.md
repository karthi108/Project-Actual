# ACTUAL
## Personal-to-Enterprise Verified Work Intelligence & Automation Platform

I want to build ACTUAL completely from scratch with Codex helping me as an engineering mentor and implementation partner.

This is **not** a request to generate the whole repository in one shot.

The objectives are simultaneously to:

1. build a serious production-style software system;
2. make ACTUAL useful to me personally in everyday life;
3. make the same architecture capable of expanding to freelancers, startups, teams and enterprises;
4. learn AI engineering, backend engineering, automation, distributed systems, cloud, DevOps, security, process intelligence and product engineering while building;
5. create genuinely strong CDI/interview/portfolio material;
6. understand every important design and implementation decision;
7. avoid fake autonomy, architecture theatre and technology soup.

Challenge bad ideas.

Do not blindly agree with me.

Do not introduce technology because it is fashionable.

For every important technology or component, answer:

> What concrete problem does this solve?

Do not claim production readiness, passing tests, security, performance improvements or benchmark results unless they were actually demonstrated.

---

# 1. PRODUCT THESIS

ACTUAL exists because there is usually a large difference between:

- what people are supposed to do;
- what they actually do;
- what software could handle;
- what AI should handle;
- and what humans should continue controlling.

ACTUAL should:

1. understand how digital work actually happens;
2. identify repeated, wasteful or unnecessarily manual work;
3. understand why exceptional human decisions happen;
4. recommend process improvements;
5. decide the cheapest reliable execution mechanism for each step;
6. generate a typed candidate workflow;
7. test that workflow before trusting it;
8. run it in shadow mode before consequential activation;
9. enforce permissions and human approval;
10. execute only authorized actions;
11. measure whether the resulting workflow actually improved anything.

Core philosophy:

> Real work. Real evidence. Real results.

---

# 2. PRODUCT PRINCIPLE

ACTUAL must NOT ask:

> Can we use AI here?

It should ask:

> What is the cheapest, safest and most reliable mechanism that can correctly perform this work?

Default decision hierarchy:

```text
Can the step be removed?
        ↓ no

Can the process be simplified?
        ↓ no

Can systems be integrated directly?
        ↓ no

Can an API solve it deterministically?
        ↓ no

Can ordinary deterministic software solve it?
        ↓ no

Can conventional ML solve it adequately?
        ↓ no

Does semantic ambiguity actually justify an LLM?
        ↓ no

Keep the human.
```

AI is one tool inside ACTUAL.

AI is not ACTUAL itself.

---

# 3. PERSONAL-FIRST, ENTERPRISE-CAPABLE

ACTUAL must be architected so the same core platform can evolve through:

```text
ACTUAL Personal
      ↓
ACTUAL Pro
      ↓
ACTUAL Teams
      ↓
ACTUAL Enterprise
```

## ACTUAL Personal

Useful every day for one person.

Potential workflows include:

- job discovery;
- job-fit analysis;
- CV selection;
- truthful CV tailoring;
- application preparation;
- application tracking;
- follow-ups;
- interview preparation;
- emails;
- calendar;
- meeting-to-task extraction;
- research;
- documents;
- personal administration;
- recurring browser workflows;
- French learning;
- expense/document organization.

ACTUAL Personal must not be hardcoded as a job-search application.

Job hunting is simply the first major workflow family.

## ACTUAL Pro

For:

- freelancers;
- founders;
- consultants;
- students;
- independent professionals;
- very small businesses.

## ACTUAL Teams

Adds:

- multiple users;
- shared processes;
- shared workflows;
- team roles;
- approvals;
- shared connectors;
- organization policies.

## ACTUAL Enterprise

Eventually adds:

- SSO;
- advanced IAM;
- tenant isolation;
- organization-wide process intelligence;
- enterprise connectors;
- governance;
- compliance controls;
- process mining;
- organization policy;
- stronger isolation;
- sophisticated audit;
- NEXUS integration.

Do not build Enterprise ACTUAL first.

---

# 4. FIRST REAL USE CASE — CAREER WORKFLOW

The first ACTUAL workflow should provide genuine daily value to me.

Initial vertical:

```text
JOB DISCOVERY
      ↓
JOB EXTRACTION
      ↓
REQUIREMENT NORMALIZATION
      ↓
FIT ANALYSIS
      ↓
SKILL-GAP ANALYSIS
      ↓
CV SELECTION
      ↓
TRUTHFUL CV ADAPTATION
      ↓
APPLICATION PREPARATION
      ↓
HUMAN REVIEW
      ↓
SUBMISSION
      ↓
TRACKING
      ↓
FOLLOW-UP
      ↓
INTERVIEW PREPARATION
```

Important:

ACTUAL must not become a spam job-application bot.

It must optimize application quality, prioritization and truthfulness rather than application volume.

Example:

```text
Job requires:

Python               yes
FastAPI              yes
LLM integration      yes
Azure                 strong
French                B2
5 years experience

Verified user profile:

Python               strong
FastAPI              evidence exists
LLM integration      evidence exists
Azure                 limited
French                below B2
5 years experience    false
```

ACTUAL should say:

```text
Strong:
- Python
- backend
- AI integration

Important gaps:
- Azure depth
- French B2
- experience requirement

Do not claim:
- B2 French
- 5 years experience
- advanced Azure
```

The system must be truthful by design.

---

# 5. VERIFIED PERSONAL PROFILE

ACTUAL should maintain a structured evidence-backed profile rather than relying entirely on vague conversational memory.

Conceptually:

```yaml
skills:
  python:
    level: strong
    evidence:
      - project:NEXUS
      - internship
      - project:RELAY

  terraform:
    level: learning
    evidence:
      - project:...

languages:
  french:
    level: ...

career_targets:
  - AI Integration
  - AI Automation
  - Backend
  - Cloud
  - Cybersecurity

constraints:
  location:
    - France
```

Distinguish:

```text
CLAIM
vs
VERIFIED EVIDENCE
```

ACTUAL must never silently convert a user claim into verified professional evidence.

---

# 6. GENERAL WORKFLOW MODEL

Job hunting is only the first workflow family.

Internally all workflows should use the same concepts.

Examples:

## Job application

```text
job
→ analyze
→ evaluate fit
→ prepare
→ approve
→ apply
→ track
```

## Meeting

```text
meeting
→ transcript/notes
→ identify decisions
→ identify tasks
→ confirm
→ schedule/follow up
```

## Invoice

```text
document
→ extract
→ validate
→ classify
→ record
→ human approval if needed
```

## Operations

```text
email
→ attachment
→ extract
→ lookup
→ classify
→ decide
→ update system
→ reply
```

Different domains.

Same workflow engine.

---

# 7. TEACH MODE

ACTUAL should eventually contain an explicit:

## Teach ACTUAL

mode.

The user deliberately starts a capture session.

ACTUAL observes privacy-filtered semantic actions.

Example:

```text
open job
→ company research
→ compare CV
→ choose resume
→ edit summary
→ prepare message
→ update tracker
```

After several sessions ACTUAL detects repeated sequences and variations.

It should NOT claim that a single demonstration represents the full business process.

One execution is:

```text
one observed example
```

not:

```text
the universal workflow
```

ACTUAL must accumulate evidence across multiple executions.

---

# 8. VOICE TEACH MODE

Voice should solve an actual knowledge problem.

Computer activity tells us:

> WHAT happened.

Voice can explain:

> WHY it happened.

Example:

Normally ACTUAL observes:

```text
station lookup
→ ticket
```

But one execution becomes:

```text
station lookup
→ contract lookup
→ ticket
```

ACTUAL can ask:

> Why did you check the contract in this case?

User replies:

> Because this customer has a special maintenance contract and coverage needs to be checked first.

ACTUAL generates:

```text
RULE CANDIDATE

IF special_contract_customer
THEN verify_contract_coverage
BEFORE intervention_creation
```

The user must confirm/edit/reject the candidate.

A voice statement is:

```text
human_claim
```

not automatically:

```text
verified_company_policy
```

Potential supporting evidence later:

- historical executions;
- SOP;
- documented company policy;
- other experts;
- system behavior.

Voice is therefore an evidence-acquisition interface, not decorative voice chat.

---

# 9. NO-PAID-LLM BASELINE

Initial runtime must require no paid LLM API.

Use:

```text
Ollama
    ↓
Qwen
```

behind an internal abstraction.

Conceptually:

```text
ModelGateway

├── OllamaQwenProvider        INITIAL
├── OpenAIProvider            OPTIONAL LATER
├── AnthropicProvider         OPTIONAL LATER
├── vLLMProvider              OPTIONAL LATER
└── future providers
```

ACTUAL business logic must depend on:

```text
typed input
→ ModelGateway
→ typed result
```

not directly on Ollama/Qwen-specific code.

Initial AI responsibilities may include:

- requirement extraction;
- semantic classification;
- document interpretation;
- workflow-step interpretation;
- process explanation;
- voice knowledge extraction;
- candidate workflow design;
- job-fit reasoning;
- CV tailoring suggestions;
- summarization.

AI must NOT control:

- authorization;
- permissions;
- workflow persistence;
- retry logic;
- security policy;
- approvals;
- external side effects;
- audit integrity.

Codex/OpenAI may help develop ACTUAL.

Do not require Codex or a paid OpenAI API for ACTUAL runtime.

---

# 10. LOCAL VOICE

Initial voice stack should also prefer local execution.

Potential architecture:

```text
Microphone
    ↓
explicit record / push-to-talk
    ↓
local audio
    ↓
faster-whisper
    ↓
transcript
    ↓
PII/privacy filtering
    ↓
structured knowledge extraction
    ↓
user confirmation
```

Text input must always remain available.

Voice is optional.

Do not block core ACTUAL development on voice.

---

# 11. HIGH-LEVEL ARCHITECTURE

ACTUAL should use a hybrid architecture.

```text
                       USER DEVICE
──────────────────────────────────────────────────

Browser Extension / Local Client

Teach Mode
Voice Capture
Application Allowlist
Privacy Filtering
Sensitive-field Exclusion
Semantic Event Generation

                         │
                         │ privacy-filtered events
                         ▼

                       CLOUD / SERVER
──────────────────────────────────────────────────

                    ACTUAL WEB
                         │
                         ▼
                  ACTUAL API
                         │
             ┌───────────┼─────────────┐
             ▼           ▼             ▼
          Identity    Projects      Connectors
                         │
                         ▼
                    Event Store
                         │
                         ▼
                 Work Intelligence
                         │
                         ▼
                      Work Graph
                         │
                         ▼
                 Improvement Engine
                         │
                         ▼
                    Workflow IR
                         │
             ┌───────────┴────────────┐
             ▼                        ▼
       Historical Replay         Shadow Mode
             │                        │
             └───────────┬────────────┘
                         ▼
                 Validation Engine
                         │
                         ▼
                 Authorization Gate
                         │
                         ▼
                    Human Approval
                         │
                         ▼
                   Workflow Runtime
                         │
                         ▼
                    Tool Gateway
                         │
            ┌────────────┼────────────┐
            ▼            ▼            ▼
          Email       Calendar      APIs...
                         │
                         ▼
                  Outcome Events
                         │
                         ▼
                 Impact Measurement
```

---

# 12. LOCAL VS CLOUD

## Local device responsibilities

Keep privacy-sensitive capture as close to the user as practical:

- browser/application interaction capture;
- explicit Teach Mode;
- app allowlists;
- app blocklists;
- password/sensitive input exclusion;
- initial redaction;
- temporary raw event handling;
- optional local speech recognition.

## Backend/server responsibilities

- persistent account state;
- workflow registry;
- event history;
- work graph;
- evaluations;
- AI reasoning;
- workflow execution;
- connectors;
- authorization;
- approvals;
- audit;
- team features;
- long-running tasks;
- outcome measurements.

Therefore:

> Local privacy boundary + centralized control plane.

Do not make the entire project either completely local or completely cloud-based.

---

# 13. DEVELOPMENT DEPLOYMENT

Start locally.

Development environment:

```text
Windows
   +
WSL2
   +
Docker
   +
Docker Compose
```

Initial services should eventually include:

```text
web
api
worker
postgres
ollama
```

Add services only as needed.

Do not deploy to cloud on day one.

---

# 14. PRODUCTION-LIKE DEPLOYMENT

Later deploy to OVHcloud.

Initial topology:

```text
Internet
    ↓
TLS reverse proxy
    ↓
ACTUAL Web/API
    ↓
private network
    ├── workers
    ├── PostgreSQL
    ├── object storage
    ├── model services if required
    └── observability
```

Use:

- Docker;
- Terraform;
- GitHub Actions;
- managed PostgreSQL where justified;
- proper secrets management;
- TLS;
- backups;
- monitoring.

Do NOT introduce Kubernetes initially.

---

# 15. BACKEND STACK

Use current stable compatible releases when implementation begins.

Core:

- Python
- FastAPI
- Pydantic
- SQLAlchemy 2
- Alembic
- PostgreSQL
- pytest
- mypy
- Ruff

Optional only when justified:

- Redis
- pgvector

Do NOT initially add:

- MongoDB;
- Neo4j;
- Elasticsearch;
- dedicated vector database.

---

# 16. FRONTEND STACK

- Next.js
- React
- TypeScript
- Tailwind CSS
- shadcn/ui
- TanStack Query
- TanStack Table
- React Flow
- Vitest
- Playwright

ACTUAL must not primarily be a chatbot.

Potential navigation:

```text
Overview

My Work
  Processes
  Activities
  Variants

Career
  Jobs
  Companies
  Applications
  Interviews
  Skills

Teach

Automations
  Draft
  Replay
  Shadow
  Active

Approvals

Executions

Evaluations

Audit

Connectors

Settings
```

Chat/voice can exist as an interface to ACTUAL but not replace the product UI.

---

# 17. CANONICAL WORK EVENT MODEL

ACTUAL needs an internal event representation.

Conceptually inspired by event/process-mining models such as object-centric event logs.

A semantic event could contain:

```yaml
event_id:
occurred_at:
session_id:

actor:
application:
activity:

business_objects:
  - type:
    id_reference:

properties:

privacy_classification:

source:
```

Example:

```yaml
activity: job_requirement_reviewed

application: browser

business_objects:
  - type: job_posting
    id_reference: JOB-382

properties:
  requirement_category: cloud

privacy_classification: normal

source: browser_extension
```

Raw low-level events should not automatically become permanent cloud data.

---

# 18. WORK GRAPH

Multiple observations should eventually become a versioned graph:

```text
activity nodes
+
transitions
+
conditions
+
business objects
+
variants
+
evidence
+
durations
+
exceptions
```

Example:

```text
Job discovered
       ↓
Extract requirements
       ↓
Fit evaluation
       ↓
 ┌─────┴─────────┐
 ↓               ↓
poor             strong
 ↓               ↓
reject        select CV
                 ↓
             tailor
                 ↓
             approval
                 ↓
              apply
```

The graph must distinguish:

- observed behavior;
- inferred behavior;
- user-confirmed behavior;
- policy requirements.

---

# 19. WORKFLOW IR

This is a core ACTUAL technical primitive.

AI must NOT generate arbitrary Python code and execute it directly.

Generate a strongly typed intermediate representation.

Conceptually:

```yaml
workflow:
  id: career-application
  version: 3

trigger:
  type: job_discovered

steps:

  - id: extract_requirements
    type: ai
    capability: job_requirement_extraction
    output_schema: JobRequirements

  - id: evaluate_fit
    type: deterministic_ai_assisted
    output_schema: JobFitAssessment

  - id: choose_cv
    type: deterministic
    capability: cv_selection

  - id: tailor_cv
    type: ai
    constraints:
      - evidence_required
      - no_skill_fabrication

  - id: review
    type: human_approval

  - id: submit
    type: tool
    capability: job_application_submit

  - id: record
    type: deterministic
```

Every executable step eventually needs metadata such as:

```text
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
```

---

# 20. SIDE-EFFECT CLASSES

All tools/actions should be classified.

Examples:

```text
READ_ONLY

LOCAL_WRITE

REVERSIBLE_WRITE

EXTERNAL_COMMUNICATION

FINANCIAL

PRIVILEGED

IRREVERSIBLE
```

Example:

```text
read_job
→ READ_ONLY

save_application_draft
→ LOCAL_WRITE

send_recruiter_email
→ EXTERNAL_COMMUNICATION

submit_application
→ EXTERNAL_WRITE

delete_account
→ IRREVERSIBLE
```

Higher-risk classes require stronger approval.

---

# 21. TOOL GATEWAY

Models never receive raw secrets.

The model requests:

```text
tool:
calendar.create_event

arguments:
...
```

The Tool Gateway handles:

- schema validation;
- identity;
- secrets;
- authorization;
- retries;
- rate limits;
- audit;
- API execution.

Models must never directly receive:

- OAuth refresh tokens;
- cloud credentials;
- database passwords;
- GitHub admin tokens;
- raw secret vault contents.

---

# 22. AUTHORIZATION

Initially implement a simple deterministic authorization interface.

Conceptually:

```text
AuthorizationPort
```

Initial implementation:

```text
LocalPolicyAuthorizer
```

Later:

```text
NexusAuthorizer
```

The ACTUAL domain must not be tightly coupled to NEXUS.

Permission request concept:

```text
principal
action
resource
context
```

Example:

```text
principal:
career-application-workflow

action:
application.submit

resource:
job-493

context:
user=Karthik
workflow_version=3
approval=...
```

Default deny.

---

# 23. HUMAN APPROVAL

Approval must bind to exactly what was reviewed.

Do not use vague:

```text
approve workflow
```

Instead approval should eventually bind to:

```text
workflow version
specific action
relevant arguments or argument hash
approver
expiration
policy version
```

If the workflow or consequential arguments change:

```text
approval invalidated
```

---

# 24. HISTORICAL REPLAY

No generated workflow earns execution authority immediately.

Run candidate workflows against historical or synthetic cases first.

```text
Candidate workflow
       ↓
Historical dataset
       ↓
Replay
       ↓
Compare expected vs candidate outcomes
```

Potential metrics:

- correct branch rate;
- extraction accuracy;
- false automation;
- false rejection;
- human escalation rate;
- policy violations;
- tool-call validity;
- workflow completion;
- hallucinated entities;
- cost;
- latency.

Failing workflows stay inactive.

---

# 25. SHADOW MODE

After replay:

```text
                LIVE INPUT
                   │
        ┌──────────┴──────────┐
        ▼                     ▼
      HUMAN                ACTUAL

 real actions          predicted actions
                            │
                       NO SIDE EFFECTS
```

Compare afterwards.

Example:

```text
Human:
apply = yes
CV = AI-Automation
French claim = A2

ACTUAL:
apply = yes       ✓
CV = AI-Automation ✓
French claim = B2  ✗
```

This workflow cannot fully activate.

Fix the problem first.

---

# 26. PARTIAL ACTIVATION

ACTUAL must support capability/step-level activation.

Example:

```text
job extraction       READY
company research     READY
fit analysis         READY
CV recommendation    READY
CV tailoring         SHADOW
application submit   HUMAN APPROVAL
```

Do not require the entire workflow to become autonomous.

This is a critical product principle.

---

# 27. WORKFLOW RUNTIME

Initially build a small persisted runtime so I learn:

- workflow states;
- durable state;
- activity execution;
- retries;
- backoff;
- timeouts;
- idempotency;
- wait states;
- human approvals;
- crash recovery.

Use PostgreSQL-backed state initially.

Only introduce Temporal after the project's workflow complexity genuinely justifies it.

Do not hide these concepts behind Temporal immediately.

---

# 28. IDEMPOTENCY

Every side-effecting operation should eventually answer:

> What happens if ACTUAL receives the same request twice?

Example:

Job submission:

```text
submission idempotency key =
user + job + workflow version
```

ACTUAL must avoid accidental duplicate applications.

Similar logic is required for:

- emails;
- tickets;
- calendar events;
- file operations;
- payments if they ever exist.

---

# 29. PROCESS / TASK INTELLIGENCE

Initially use deterministic analysis where possible:

- event grouping;
- sequence extraction;
- frequency;
- repeated subsequences;
- variants;
- branch discovery;
- duration distributions;
- loops;
- rework;
- bottlenecks.

Possible research/prototyping dependency:

- PM4Py

But keep ACTUAL's domain model independent of PM4Py.

Do not make a third-party library define the architecture.

---

# 30. IMPROVEMENT ENGINE

Every discovered activity should eventually be classifiable as:

```text
ELIMINATE

SIMPLIFY

INTEGRATE

DETERMINISTIC

AI_ASSISTED

HUMAN
```

The recommendation must include evidence explaining why.

Example:

```text
Activity:
Copy job title into application tracker

Observed:
93/100 applications

Variation:
none

Semantic reasoning:
none

Recommendation:
DETERMINISTIC

Reason:
repetitive structured transfer
```

---

# 31. IMPACT MEASUREMENT

ACTUAL cannot claim savings based purely on AI estimates.

Measure actual outcomes such as:

- human active time;
- end-to-end duration;
- workflow success;
- manual intervention;
- error/rework rate;
- application preparation time;
- follow-up misses;
- workflow failure;
- inference time;
- compute cost;
- number of AI calls;
- acceptance/rejection of AI suggestions.

Compare:

```text
manual baseline
vs
assisted
vs
partially automated
```

Only report measured data.

---

# 32. DOGFOODING

I will use ACTUAL in my real life while building it.

This is important product testing.

Real use can identify:

- missing workflows;
- poor UX;
- incorrect assumptions;
- annoying approval flows;
- missing integrations;
- weak AI behavior;
- useful new features.

But dogfooding does NOT replace formal testing.

Every bug discovered through normal use should ideally become:

```text
reproducible test
```

before being fixed.

Principle:

> Production usage finds the bug.
> Regression testing prevents its return.

---

# 33. SYNTHETIC TEST ENVIRONMENTS

Create controlled environments for evaluation.

Initial:

## CAREERLAB

Synthetic:

- jobs;
- companies;
- CV variants;
- recruiter emails;
- applications;
- interview requests;
- rejections;
- follow-ups.

Ground truth may include:

```text
actual required skills
true strong-fit / low-fit classification
unsupported CV claims
correct CV choice
required human intervention
expected follow-up state
```

Later:

## WORKLAB

Synthetic enterprise workflows:

- inbox;
- document processing;
- CRM;
- asset registry;
- ticketing;
- internal portal.

This lets ACTUAL be tested without proprietary company data.

---

# 34. DATASET METHODOLOGY

Create:

```text
development
validation
locked_test
```

Once locked test is frozen:

- do not inspect individual cases during development;
- do not tune prompts/rules against locked-test examples;
- preserve dataset/version hashes;
- measure only when deliberately running an acceptance evaluation.

Avoid benchmark leakage.

---

# 35. TESTING PYRAMID

ACTUAL needs:

## Unit tests

Domain behavior.

## Schema tests

Invalid objects rejected.

## Property/invariant tests

Examples:

```text
no approval → prohibited write impossible

revoked authority → action impossible

wrong tenant → access impossible

workflow version changed → old approval invalid
```

## Database tests

Transactions, constraints and migrations.

## Integration tests

API ↔ DB ↔ worker ↔ model ↔ connector.

## AI evaluations

Structured-output validity, extraction accuracy, classification accuracy and unsupported claims.

## Replay tests

Candidate workflows against known cases.

## Shadow tests

Predicted vs human decisions.

## Security tests

IAM, injection, secrets and privilege boundaries.

## Privacy tests

Sensitive data never leaves intended boundary.

## Browser E2E

Playwright.

## Reliability tests

Failures, retries and recovery.

## Load tests

Only after meaningful traffic paths exist.

---

# 36. SECURITY ADVERSARIAL CASES

Eventually deliberately test:

- prompt injection in job listing;
- prompt injection in PDF;
- malicious email;
- fake evidence;
- fabricated CV skill;
- cross-tenant IDOR;
- OAuth scope abuse;
- secret extraction;
- SSRF;
- arbitrary URL access;
- connector output injection;
- tool-loop attempts;
- replayed approval;
- stale permission;
- tampered workflow;
- workflow changed after approval;
- duplicate event;
- duplicate side effect;
- model timeout;
- malformed model output.

Critical principle:

```text
AI text
≠
authorization
```

---

# 37. PRIVACY

ACTUAL must never become invisible surveillance software.

Local capture should support:

- explicit Teach Mode;
- visible capture state;
- pause;
- stop;
- app allowlist;
- app denylist;
- sensitive field exclusion;
- password exclusion;
- local filtering;
- session review;
- deletion;
- retention controls.

Enterprise philosophy:

> Analyze the process, not rank the person.

Do not introduce:

- employee productivity score;
- employee ranking;
- termination recommendation;
- hidden keylogging.

---

# 38. OBSERVABILITY

Use OpenTelemetry.

Every important flow should eventually carry:

```text
trace_id
workflow_run_id
workflow_version
user/tenant
model_run_id
tool_execution_id
authorization_decision_id
```

Example:

```text
job-application.workflow

├── extract_job
│   └── qwen.inference
│
├── evaluate_fit
│   └── qwen.inference
│
├── choose_cv
│
├── tailor
│   └── qwen.inference
│
├── approval.wait
│
└── submission
```

Need structured logging.

No secrets in logs.

---

# 39. AUDIT

Every consequential action should eventually answer:

```text
WHO

did WHAT

WHEN

to WHICH RESOURCE

using WHICH WORKFLOW VERSION

under WHICH AUTHORITY

based on WHICH INPUT/EVIDENCE

with WHICH APPROVAL

with WHAT RESULT
```

Use append-oriented relational audit events.

Do not use blockchain.

---

# 40. REPOSITORY TARGET

Do not create these folders until functionality requires them.

Eventually something similar to:

```text
actual/
│
├── apps/
│   ├── web/
│   ├── api/
│   └── edge/
│
├── services/
│   ├── worker/
│   └── sandbox/
│
├── packages/
│   ├── contracts/
│   ├── events/
│   ├── workflow_ir/
│   ├── intelligence/
│   ├── connectors/
│   ├── authorization/
│   ├── process/
│   └── evals/
│
├── careerlab/
│
├── worklab/
│
├── datasets/
│
├── infrastructure/
│   ├── docker/
│   └── terraform/
│
├── tests/
│   ├── integration/
│   ├── security/
│   ├── e2e/
│   └── evals/
│
└── docs/
    ├── architecture/
    ├── adr/
    ├── threat-model/
    ├── privacy/
    └── evaluations/
```

No empty architecture theatre.

---

# 41. BUILD PHASES

## PHASE 0 — Engineering Contract

Define:

- exact problem;
- v0.1 scope;
- users;
- non-goals;
- trust boundaries;
- privacy model;
- threat model;
- first Career workflow;
- first event model;
- Workflow IR principles;
- evaluation methodology;
- repository structure;
- technical ADRs.

NO UI application.

NO agent.

NO LLM runtime.

Acceptance:

ACTUAL Architecture v0.1 is defensible.

---

## PHASE 1 — CAREERLAB

Create controlled synthetic job-search world.

Implement:

- synthetic jobs;
- companies;
- CV evidence profiles;
- application states;
- recruiter messages;
- interview/rejection outcomes.

Acceptance:

repeatable cases with hidden ground truth.

---

## PHASE 2 — Core Contracts

Implement:

- identifiers;
- work events;
- business objects;
- evidence objects;
- profile evidence;
- job objects;
- workflow primitives.

Acceptance:

schemas reject invalid state.

---

## PHASE 3 — Persistence

PostgreSQL + SQLAlchemy + Alembic.

Only entities needed now.

Acceptance:

migrations up/down and database integration tests pass.

---

## PHASE 4 — API

FastAPI.

Expose only required CareerLab/core operations.

Acceptance:

typed API + integration tests.

---

## PHASE 5 — Local Qwen Model Gateway

Implement:

```text
ModelGateway
    ↓
OllamaQwenProvider
```

Use typed structured outputs.

No model can write to production systems.

Acceptance:

repeatable structured inference + timeout/error handling.

---

## PHASE 6 — Job Intelligence

Implement:

- job extraction;
- requirement normalization;
- evidence-backed fit analysis;
- skill-gap detection.

Acceptance:

evaluation dataset metrics measured.

---

## PHASE 7 — Personal Career Profile

Structured user evidence.

Separate claims from verified evidence.

Acceptance:

unsupported skill claims cannot silently enter generated CV content.

---

## PHASE 8 — Career Workflow UI

Implement useful daily interface.

Jobs:

```text
Discovered
Prioritized
Rejected
Preparing
Ready for Review
Applied
Interview
Offer
Closed
```

Acceptance:

I can genuinely use it every day.

---

## PHASE 9 — Application Preparation

Implement:

- CV selection;
- truthful tailoring;
- cover-letter/message preparation;
- human review.

Never fabricate experience.

Acceptance:

every generated modification traceable to user evidence or explicitly marked as suggestion.

---

## PHASE 10 — Workflow IR

Generalize Career workflow into typed Workflow IR.

Acceptance:

invalid workflows rejected and required permissions can be calculated.

---

## PHASE 11 — Runtime

Build persisted execution.

Learn:

- states;
- retries;
- timeouts;
- idempotency;
- wait states.

Acceptance:

workflow survives process restart.

---

## PHASE 12 — Connectors

Only now connect real systems where needed.

Potential initial connectors:

- Gmail;
- Calendar;
- files;
- browser/job-source intake.

Prefer APIs over browser automation.

Acceptance:

read operations first.

---

## PHASE 13 — Human Approval

Consequential actions require explicit approval.

Acceptance:

no application/email/write action bypasses approval.

---

## PHASE 14 — Historical Replay

Replay candidate logic against CareerLab/frozen cases.

Acceptance:

formal go/no-go evaluation.

---

## PHASE 15 — Shadow Mode

Run candidate workflow against real personal work without consequential writes.

Acceptance:

compare ACTUAL predictions with my decisions.

---

## PHASE 16 — Controlled Personal Activation

Activate only proven capabilities.

Example:

```text
job extraction       active
job ranking          active
CV suggestion        active
application submit   approval required
```

Acceptance:

no uncontrolled external action.

---

## PHASE 17 — Teach Mode

Browser/local semantic capture.

Explicit user-controlled capture only.

Acceptance:

repeatable personal workflows produce useful semantic event sequences.

---

## PHASE 18 — Process Discovery

Find:

- repetition;
- variants;
- branch points;
- loops;
- waste.

Acceptance:

measured against synthetic known process cases.

---

## PHASE 19 — Voice Teach Mode

Add local speech-to-text.

Capture WHY decisions occur.

Acceptance:

voice explanation creates editable candidate rule, never automatic policy.

---

## PHASE 20 — Improvement Engine

Classify:

```text
ELIMINATE
SIMPLIFY
INTEGRATE
DETERMINISTIC
AI_ASSISTED
HUMAN
```

Acceptance:

recommendations contain evidence.

---

## PHASE 21 — General Workflows

Move beyond Career:

- meeting actions;
- email triage;
- documents;
- research;
- personal administration.

Do not add workflow families merely for demos.

Use actual personal demand.

---

## PHASE 22 — NEXUS Integration

Replace/augment local authorization with:

```text
NexusAuthorizer
```

for bounded authority.

Acceptance:

ACTUAL remains functional without NEXUS but receives stronger authorization when connected.

---

## PHASE 23 — Reliability

Add:

- retries;
- bounded backoff;
- dead-letter states;
- compensation;
- provider outage handling;
- recovery.

Acceptance:

fault-injection tests.

---

## PHASE 24 — Security Hardening

Attack the system.

Acceptance:

documented threat tests and known residual risks.

---

## PHASE 25 — Cloud

Deploy:

- Docker;
- OVHcloud;
- PostgreSQL;
- Terraform;
- GitHub Actions;
- proper secrets;
- TLS;
- OpenTelemetry.

Acceptance:

reproducible deployment.

---

## PHASE 26 — Pro/Teams

Only after Personal ACTUAL genuinely works.

Add organizations and shared workflows.

---

## PHASE 27 — Enterprise Research

Only later:

- process mining at organization scale;
- SSO;
- advanced governance;
- stronger tenant isolation;
- enterprise integrations;
- durable orchestration such as Temporal where justified.

---

# 42. LEARNING PLAN

Do not study everything before coding.

## Learn before Phase 1

Comfortable basics:

- Python;
- Git;
- HTTP;
- JSON;
- SQL;
- Docker basics;
- pytest;
- authentication vs authorization;
- LLM structured outputs.

## Learn while building

### Backend

- FastAPI;
- SQLAlchemy;
- database transactions;
- async;
- background work;
- migrations;
- idempotency.

### AI

- model abstractions;
- structured inference;
- evaluations;
- hallucination control;
- evidence grounding;
- local inference.

### Data/process

- event modeling;
- sequence mining;
- task mining;
- process mining;
- OCEL concepts.

### Automation

- workflow state machines;
- retries;
- compensation;
- durable execution;
- connectors.

### Security

- OAuth/OIDC;
- RBAC/ABAC;
- secrets;
- tenant isolation;
- OWASP;
- prompt injection;
- tool authorization.

### Cloud

- Linux;
- Docker;
- Terraform;
- networking;
- TLS;
- CI/CD;
- observability.

### Voice

- audio fundamentals;
- VAD;
- speech-to-text;
- streaming later.

---

# 43. TECHNOLOGIES TO EXCLUDE INITIALLY

Do NOT introduce without a demonstrated requirement:

- Kubernetes;
- Kafka;
- Neo4j;
- Elasticsearch;
- dedicated vector DB;
- multiple autonomous agents;
- five model providers;
- Temporal;
- desktop capture across every OS;
- SAP;
- Salesforce;
- ServiceNow;
- fully autonomous browser agent;
- unrestricted shell;
- arbitrary generated-code execution.

---

# 44. DEVELOPMENT PROCEDURE

For every meaningful feature:

```text
1. Define the problem.

2. Explain the underlying concept to me.

3. Ask for my reasoning when educationally useful.

4. Challenge weak reasoning.

5. Define contracts/invariants.

6. Threat-model the feature where relevant.

7. Design the simplest correct solution.

8. Implement the smallest slice.

9. Write tests.

10. Run the tests.

11. Deliberately break edge cases.

12. Diagnose root cause.

13. Improve.

14. Measure where appropriate.

15. Document important trade-offs.

16. Commit cleanly.
```

Do not dump huge generated codebases.

For important files explain:

- why this file exists;
- what responsibility it owns;
- important types/functions;
- failure modes;
- tests.

I should understand what I commit.

---

# 45. GIT PROCEDURE

Use clean, meaningful commits.

Example:

```text
docs: establish ACTUAL phase-0 architecture

feat: add canonical work-event contracts

test: enforce evidence provenance invariants

feat: add ollama qwen model gateway

feat: add job requirement extraction baseline
```

Do not combine unrelated work into giant commits.

Tag significant accepted milestones.

---

# 46. QUALITY BAR

ACTUAL should eventually include:

- useful product UI;
- authentication;
- authorization;
- evidence tracking;
- audit;
- tests;
- CI;
- migrations;
- structured logging;
- traces;
- privacy controls;
- reliable workflows;
- retries;
- idempotency;
- human approval;
- local-model fallback;
- failure handling;
- security;
- deployment;
- documentation;
- evaluations.

Do not call it production-ready merely because these features exist.

Production readiness requires evidence they work.

---

# 47. KEY SYSTEM INVARIANTS

These should remain true throughout the project.

## Invariant 1

LLM output is an untrusted proposal.

## Invariant 2

AI cannot grant itself authority.

## Invariant 3

External side effects require deterministic authorization.

## Invariant 4

High-risk actions can require human approval.

## Invariant 5

Approval is bound to the reviewed workflow/action/version.

## Invariant 6

Unsupported professional claims cannot silently enter application materials.

## Invariant 7

Sensitive credentials never enter model prompts.

## Invariant 8

One event delivered twice must not unintentionally create two side effects.

## Invariant 9

Every consequential action is auditable.

## Invariant 10

Automation must be measurable.

## Invariant 11

Dogfooding feedback becomes regression coverage whenever practical.

## Invariant 12

ACTUAL analyzes work/processes—not employee worth.

---

# 48. LONG-TERM IDEAL DEMO

Final mature demo:

```text
I use ACTUAL in real life.

       ↓

ACTUAL notices repeated work.

       ↓

Teach Mode captures semantic activity.

       ↓

Voice asks why an unusual decision occurred.

       ↓

ACTUAL reconstructs the workflow.

       ↓

It identifies:

remove 1 step
integrate 2
deterministically automate 3
AI-assist 1
keep human 2

       ↓

Candidate workflow compiled to typed Workflow IR.

       ↓

Historical replay.

       ↓

Problems discovered.

       ↓

Workflow corrected.

       ↓

Replay repeated.

       ↓

Live shadow mode.

       ↓

System vs human compared.

       ↓

Safe capabilities approved.

       ↓

NEXUS / authorization provides bounded authority.

       ↓

ACTUAL executes only allowed actions.

       ↓

OpenTelemetry records execution.

       ↓

ACTUAL compares actual results against manual baseline.

       ↓

Only measured improvements are reported.
```

---

# 49. PRODUCT SUCCESS TEST

ACTUAL has failed if it becomes:

```text
ChatGPT
+
tools
+
dashboard
```

ACTUAL succeeds if we can demonstrate:

```text
real observed work
      ↓
evidence-backed understanding
      ↓
better process design
      ↓
typed automation
      ↓
replay
      ↓
shadow verification
      ↓
bounded authority
      ↓
controlled execution
      ↓
measured real-world result
```

---

# 50. HOW TO START THIS CODEX SESSION

Do NOT implement the entire platform.

Do NOT create every eventual folder.

Do NOT add the frontend.

Do NOT add Qwen yet.

Do NOT add connectors yet.

Do NOT add voice.

Do NOT create an agent.

Start with:

# PHASE 0 ONLY

First inspect the repository if it already contains anything.

Then help me produce:

1. ACTUAL problem statement;
2. exact v0.1 scope;
3. explicit non-goals;
4. first CareerLab scenario;
5. first user journey;
6. trust boundaries;
7. privacy boundaries;
8. threat model v0.1;
9. high-level architecture v0.1;
10. canonical Work Event principles;
11. Workflow IR principles;
12. initial repository structure;
13. ADR list;
14. evaluation strategy;
15. Phase-0 acceptance criteria;
16. Phase-1 plan.

Challenge this master specification where something is technically weak, premature, unsafe or unnecessarily complicated.

Teach me the reasoning while doing it.

Do not proceed to Phase 1 until Phase 0 has a defensible engineering contract.