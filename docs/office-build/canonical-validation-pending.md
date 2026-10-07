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

## Phase 10 — Typed Workflow IR

- Implementation commit: unique `wip(phase-10):` checkpoint subject; preceding Phase 9 `8e69625`.
- Implementation: IMPLEMENTED; closed synthetic DAG, capability schemas/metadata, typed bindings, outcome completeness, reachability, budgets and successful gate dominance.
- Checks run here: 15 graph/schema/adversarial tests on Python 3.13 and 3.14; Ruff; strict mypy; schema/example roundtrip; frozen-artifact check. First check found workflow version incompatible with the core contract; added a separate explicit IR version without modifying the accepted core schema.
- Checks not run: canonical personal-environment full regression. No execution or external integration in this phase.
- Security validation pending: canonical graph authority/adversarial audit. Declared effects and permissions grant no authority.
- Live integration pending: runtime, connectors and exact effect approval are subsequent phases. AI step is declarative, with no invocation.
- Known limitations: scalar schemas, fixed catalog, acyclic graphs; no arbitrary expressions/code or loops. Conservative static duration budget counts all branches.
- Canonical acceptance: PENDING.

## Phase 11 — Persisted workflow runtime

- Implementation commit: unique `wip(phase-11):` checkpoint; preceding Phase 10 `a6f8900`.
- Implementation: IMPLEMENTED. Separate explicitly migrated PostgreSQL workflow tables, immutable definitions, stable trigger deduplication, fenced leases, durable waits/retries, cancellation and atomic progress/audit.
- Checks run here: 22 graph/runtime tests passed on each Python 3.13.13 and 3.14.4 with real disposable PostgreSQL 18.6, zero skips; strict mypy (92 files and both workflow targets), Ruff, CareerLab current-environment verification and frozen artifact audit.
- Failed attempts preserved: earlier full regression was interrupted before completion and is unverified; sandbox initdb failed to create a restricted token; focused checks initially used an abbreviated Alembic head in an assertion, corrected to the exact preserved accepted head. The corrected dual-Python run passed. Phase-10 static-duration validation initially referenced a missing field; that field was added before its successful checkpoint checks.
- Checks not run: full Python regression repeated to completion at this checkpoint, Docker runtime, canonical long-lived worker/migration review. Available checks used fresh native PostgreSQL and cleaned up their owned cluster.
- Environment dependency: explicit disposable PostgreSQL URL and supported Python; operator migration, never startup DDL. Office configuration manifest is separate from frozen accepted manifests and preserves all eight record hashes.
- Security validation pending: canonical concurrency, migration, audit/lease and cross-owner adversarial review.
- Live integration pending: no tools, positive effect approval or live model execution in this checkpoint. Those capabilities have separate later gates.
- Known limitations: single DAG cursor, bounded scalar payload, no background scheduler. Lease fencing protects local progress; remote effect safety requires a distinct durable intent protocol.
- Canonical acceptance: PENDING.

## Phase 12 — Controlled connectors

- Implementation commit: unique `wip(phase-12):` checkpoint; preceding Phase 11 `e291af9`.
- Implementation: IMPLEMENTED. Closed fabricated read/write contracts, default-deny scoped authorizer, fake read runtime and safe error codes. Write dispatch remains denied.
- Checks run here: 23 pure workflow/connector tests and 8 real-PostgreSQL runtime tests on each supported Python version; Ruff, strict typing on both workflow targets, CareerLab environment integrity. Exact permission, revocation, destination rejection, malicious output and provider error redaction passed.
- Failed attempts preserved: initial import used a nonexistent principal identifier; corrected to accepted `ActorId`. Lint formatting/import findings corrected before clean checks.
- Checks not run: real provider/OAuth/network interoperability and full canonical regression. No live accounts connected.
- Environment dependency: existing Python/PostgreSQL only; no added dependencies or credentials.
- Security validation pending: canonical connector scope/error/egress adversarial review.
- Live integration pending: all real connectors; current `WritePort` has no enabled implementation.
- Known limitations: one fabricated resource reader, fixed catalog, synthetic labels cannot authenticate private prose. Provider errors expose closed codes without raw diagnostics.
- Canonical acceptance: PENDING.

## Phase 13 — Human approval and effect intents

- Implementation commit: unique `wip(phase-13):` checkpoint; preceding Phase 12 `b5a7e41`.
- Implementation: IMPLEMENTED. Exact previews/approval transitions, atomic durable intent binding, immediate authority/expiry/revocation/fence checks, append-oriented metadata audit and conservative fake-provider reconciliation.
- Checks run here: 41 combined workflow/runtime/approval checks on each supported Python against real disposable PostgreSQL; final 11 approval checks passed on both versions after adding the missing-approval bypass case; strict mypy both workflow targets, Ruff and frozen artifact audit. Concurrency across workflow versions, changed payload conflict, denial, expiry, revocation, cancellation and lost acknowledgement passed.
- Checks not run: real providers, authenticated human UI, canonical crash/process and long-lived concurrency acceptance; full regression deferred to final office checks.
- Environment dependency: existing Python/PostgreSQL, separate explicit approval migration. Fake provider receipt uses a distinct transaction to represent remote uncertainty.
- Security validation pending: canonical approval/canonicalization/authority/audit review and real provider dispatch-boundary semantics. Trusted service actor/configuration is not public authentication.
- Live integration pending: all real effect providers, provider retention/idempotency expiry and compensation. No external message is sent.
- Known limitations: short synthetic human wait; no approval UI or daemon; unknown outcomes require read-only reconciliation and never automatic resend. Cancellation after the committed dispatch marker cannot undo remote acceptance. Append-oriented audit is not administrator-proof.
- Canonical acceptance: PENDING.

## Phase 14 — Historical replay

- Implementation commit: unique `wip(phase-14):` checkpoint; preceding Phase 13 `28ea4a2`.
- Implementation: IMPLEMENTED. Same-runtime transient replay, virtual time, provider-handle/dispatch mode guards, five synthetic WorkLab observations and separate evaluator answers.
- Checks run here: 26 pure tests on both Python versions; strict typing both targets, Ruff; development evaluator reports 5/5 expected-status and branch matches, 2 completions, 1 escalation, 2 deliberate failures and zero provider calls. A typing finding in narrowed branch outcomes was corrected before clean checks.
- Checks not run: canonical historical/live datasets, real-time performance, inference or held-out accuracy. AI claim correctness is unmeasured, not reported as zero defects.
- Environment dependency: Python only. No service, provider or model is acquired by replay.
- Security validation pending: canonical replay/shadow effect-isolation review.
- Live integration pending: none claimed; shared public synthetic observations are development examples only.
- Known limitations: no real latency/ROI claim; virtual policy observations grant no execution authority. CareerLab remains frozen and isolated.
- Canonical acceptance: PENDING.

## Phase 15 — Shadow mode

- Implementation commit: unique `wip(phase-15):` checkpoint; preceding Phase 14 `a58faa3`.
- Implementation: IMPLEMENTED. Registered human-path comparison, per-step readiness and durable metadata-only synthetic observations with owner/event deduplication.
- Checks run here: 30 pure tests plus the shadow persistence/owner/deduplication test on both supported Python versions with real PostgreSQL; Ruff and strict typing both targets.
- Checks not run: real observation capture, canonical readiness calibration, full canonical regression.
- Environment dependency: explicit shadow migration and disposable PostgreSQL; simulation has no provider handles.
- Security validation pending: canonical event/path integrity and cross-owner review.
- Live integration pending: no live workplace feed; human observations grant no authority.
- Known limitations: matching synthetic traces produce candidate evidence only; all approval/effect steps remain human; no automatic activation or measured real accuracy.
- Canonical acceptance: PENDING.

## Phase 16 — Controlled personal activation architecture

- Implementation commit: unique `wip(phase-16):` checkpoint; preceding Phase 15 `3e3d15f`.
- Implementation: IMPLEMENTED for synthetic connectors only. Reviewed step/capability activation, immutable workflow pins, revision/audit and controlled composition combining current permission, activation and exact action approval.
- Checks run here: 30 pure checks plus 2 real-PostgreSQL activation tests on both supported Python versions; Ruff, strict typing both targets. Missing activation, stale revision/evidence, changed workflow, revoked permission and disable-after-approval deny. Literal narrowing was corrected before clean typing checks.
- Checks not run: personal-account activation, authenticated activation UI, full canonical regression.
- Environment dependency: explicit activation migration and existing Python/PostgreSQL; no credentials.
- Security validation pending: canonical composition/activation/revocation review. Low-level contract-test ports are not a public authenticated product boundary.
- Live integration pending: every real personal connector; no office account is activated.
- Known limitations: operator-reviewed synthetic evidence can contain disagreements and never auto-activates; activated writes retain per-action human approval. AI integration remains unavailable. Use `controlled(...)` for application fake execution.
- Canonical acceptance: PENDING.

## Phase 17 — Teach Mode

- Implementation commit: unique `wip(phase-17):` checkpoint; preceding Phase 16 `8fbf723`.
- Implementation: IMPLEMENTED synthetic semantic-session/display/privacy harness. Real capture/UI integration pending.
- Checks run here: 37 pure tests on both Python versions, Ruff, strict typing both targets; visible console demo exercises start/pause/resume/stop with one fabricated event. Allow/deny rules, password/sensitive exclusion, raw-field rejection, visibility, deduplication and deletion tested.
- Checks not run: device/browser extension recording, persistent graphical UI/accessibility or private office capture; no such capture occurs.
- Environment dependency: Python only; no capture dependency installed.
- Security validation pending: canonical permission/display loss, classification/retention and real adapter privacy review.
- Live integration pending: native/browser-extension input, UI, personal-environment observation archive.
- Known limitations: transient event tuple, one observed example per session, no automatic archive or process completeness claim; labels cannot detect deliberately mislabeled private input. No secure erasure guarantee.
- Canonical acceptance: PENDING.

## Phase 18 — Process discovery

- Implementation commit: unique `wip(phase-18):` checkpoint; preceding Phase 17 `7c80ba5`.
- Implementation: IMPLEMENTED bounded deterministic discovery: grouping, variants/repeated sequences, transitions/branches, returns/rework, elapsed durations/gaps.
- Checks run here: 41 pure checks on both supported Python versions, Ruff and strict typing both targets. Three synthetic development traces match separate test assertions; shuffled arrival, duplicate/conflicting identity, ambiguous time and owner scope checked.
- Checks not run: complete real processes, performance benchmark, causal/active-time validation or held-out accuracy.
- Environment dependency: Python only; no process-mining dependency introduced.
- Security validation pending: canonical event integrity, scope, size and clock-boundary review.
- Live integration pending: real capture/event feeds; none enabled here.
- Known limitations: repeated observed activities are returns/rework, not executable loops; elapsed gaps are not active work, causal delay or ROI. Missing events and branches cannot be inferred into completeness.
- Canonical acceptance: PENDING.

## Phase 19 — Voice Teach Mode

- Implementation commit: unique `wip(phase-19):` checkpoint; preceding Phase 18 `a2a9191`.
- Implementation: IMPLEMENTED synthetic transcript/local-STT-port harness and exact candidate confirmation. Real recording/recognizer integration pending.
- Checks run here: 48 pure tests on both supported Python versions, Ruff and strict typing both targets. Active display/session/event binding, privacy abstention, malicious/unknown explanations, duplicate/conflicting identity and human-claim/authority separation passed.
- Checks not run: real microphone/audio, local recognizer/model accuracy, private voice capture or persistent voice UI.
- Environment dependency: Python only; no recognizer/model or paid inference installed.
- Security validation pending: canonical audio permission/retention, classifier/filter limits and real-device privacy review.
- Live integration pending: personal device and a verified local STT backend. Fake fixture transcription is not an audio recognition claim.
- Known limitations: deterministic phrase catalog; unrecognized explanation requires manual review. Confirmation preserves human-claim provenance and never grants policy/permission/approval. No raw transcript/audio retained by candidate storage.
- Canonical acceptance: PENDING.

## Phase 20 — Improvement engine

- Implementation commit: unique `wip(phase-20):` checkpoint; preceding Phase 19 `7ff6578`.
- Implementation: IMPLEMENTED. Exact observation/review-linked proposals following the agreed mechanism hierarchy, conservative consequence preservation, explicit matched measurement comparisons.
- Checks run here: 51 pure checks on both supported Python versions, Ruff and strict typing both targets. Evidence rejection, mechanism ordering, conflicting risk, no automatic execution and matched/missing measurements passed. Long literal lint findings corrected before clean checks.
- Checks not run: real improvement validity, active-time instrumentation, compute/monetary measurement or measured ROI.
- Environment dependency: Python only.
- Security validation pending: canonical review provenance and risk/conflicting-judgment review.
- Live integration pending: none enabled; recommendations do not change policy/workflows/materials or execute effects.
- Known limitations: judgments remain labeled human claims/synthetic design reviews; repetition alone cannot prove redundancy. No invented savings; missing measurements remain unavailable.
- Canonical acceptance: PENDING.

## Phase 21 — General personal workflow families

- Implementation commit: unique `wip(phase-21):` checkpoint; preceding Phase 20 `81c2304`.
- Implementation: IMPLEMENTED synthetic structured meeting-action and conservative subject-triage families on the same engine. Additive registered deterministic handlers preserve original definition bytes.
- Checks run here: 54 pure checks on both supported Python versions, Ruff and strict typing both targets; malformed notes/instructions, unknown dates/assignees, triage branches, effect isolation and original definition preservation passed.
- Checks not run: real meetings/mailbox, interpretation accuracy or live provider integration.
- Environment dependency: existing Python only; no new model or service.
- Security validation pending: canonical structured input/catalog compatibility and untrusted subject/document review.
- Live integration pending: all personal provider sources and any free-prose extraction.
- Known limitations: notes must be structured synthetic tokens; no inferred tasks/dates or facts. Subject classification is a tiny deterministic prefix rule; human-review disposition is not completion of human work.
- Canonical acceptance: PENDING.

## Phase 22 — NEXUS integration boundary

- Implementation commit: unique `wip(phase-22):` checkpoint; preceding Phase 21 `6f35e06`.
- Implementation: IMPLEMENTED ACTUAL-side proposed request/decision protocol, local-policy alias and synthetic loopback adapter; real NEXUS interoperability PENDING_CANONICAL_INTEGRATION.
- Checks run here: 67 pure checks on both supported Python versions, Ruff and strict typing both targets. Mock protocol validates exact context, digest/request ID/version/expiry, malformed/oversized/redirect responses, 429/500 and timeout denial.
- Checks not run: actual NEXUS service/protocol, identity/TLS, remote audit/revocation semantics or credentials.
- Environment dependency: existing pinned httpx2, Python; no service started, new dependency or secret introduced.
- Security validation pending: canonical protocol/service identity, decision audit persistence and real revocation timing. Last-decision metadata is diagnostic, not a concurrency-safe audit ledger.
- Live integration pending: NEXUS repository/service and agreed real protocol.
- Known limitations: proposed synthetic loopback protocol only; no cached approval or fallback allow on failure. Models cannot choose destinations or confer authority.
- Canonical acceptance: PENDING.

## Phase 23 — Reliability hardening

- Implementation commit: unique `wip(phase-23):` checkpoint; preceding Phase 22 `3dae58f`.
- Implementation: IMPLEMENTED. Additive workflow migration 2/dead letters, overdue-wait deadline recovery, stable bounded jitter, explicit failure codes and successful-read error clearing.
- Checks run here: 236 workflow/accepted-model checks and 29 real-PostgreSQL workflow/approval/activation/shadow/reliability checks on each supported Python version; final 7 reliability cases on both versions start from the actual older schema; Ruff, strict typing both targets and frozen artifact audit. Model faults use accepted test doubles, not live Qwen. Negative-power typing finding corrected to bounded integer shifts.
- Checks not run: process-kill/network partition campaign, long-lived DB outage, real provider/OAuth/idempotency expiry/rate limits, canonical operational recovery.
- Environment dependency: disposable PostgreSQL/Python; explicit workflow migration 2, accepted Career migration unchanged.
- Security validation pending: canonical fault/recovery/lease/migration audit.
- Live integration pending: all real provider semantics and OAuth. Workflow AI declarations remain unavailable; accepted gateway timeout/malformed tests remain independent.
- Known limitations: uncertain dispatch reconciles without resend; no automatic unsend/compensation. A compensating action requires its own reviewed intent. Dead letters preserve failure metadata and do not automatically reactivate a run.
- Canonical acceptance: PENDING.

## Phase 24 — Security hardening

- Implementation commit: unique `wip(phase-24):` checkpoint; preceding Phase 23 `e8a77f7`.
- Implementation: IMPLEMENTED. Relational/payload identity checks, full approval audit seal, exact connector arguments and provisional migration shape validation; threat-to-test matrix in Phase 24.
- Checks run here: 236 workflow/model tests and 43 scoped real-PostgreSQL workflow/security tests on each supported Python version; Ruff, strict typing both targets, current CareerLab manifest and frozen artifact audit. Initial lint/RowMapping findings and a test fixture's `bool`/`boolean` type typo (42 passed, 1 failed on the initial database run) were corrected before the clean dual-Python run. Tests were not weakened.
- Checks not run: external penetration testing, actual OAuth/DNS/provider attacks, real-data security or canonical security certification.
- Environment dependency: existing PostgreSQL/Python only; no new library, account or secret.
- Security validation pending: canonical threat review and adversarial suite, database/runtime-role enforcement for new tables, real identity and real provider boundary validation.
- Live integration pending: all real connectors and authentication infrastructure.
- Known limitations: seals detect inconsistent records, not administrator compromise. Earlier provisional effect approvals lack the full seal and require a fresh review/run. Synthetic classification and loopback do not authenticate/detect real data. Accepted artifacts and Career migrations remain unchanged.
- Canonical acceptance: PENDING.

## Phase 25 — Deployment preparation

- Implementation commit: unique `wip(phase-25):` checkpoint; preceding Phase 24 `9aec149`.
- Implementation: IMPLEMENTED private Linux Dockerfiles/Compose, explicit secret-backed migration/check/serve, OVH/OpenStack configuration, TLS probe config, SHA-pinned verification CI, bounded OTLP/HTTP JSON instrumentation and recovery runbook.
- Checks run here: 251 workflow/model/deployment unit checks and the real-PostgreSQL deployment migration/role check on each supported Python version; four YAML files parsed, Ruff and strict typing both targets. Initial telemetry fixture clock used the wall clock against a historical synthetic run (249 passed, 2 failed); corrected to the same fixture clock, preserving deadline enforcement. Role grants were exercised against every named table and refused audit UPDATE and DDL.
- Checks not run: Docker builds/volume initialization/network isolation, Terraform fmt/init/validate/lock/plan, Nginx TLS/certificates, actual Collector interoperability, hosted GitHub Actions, OVH deployment or physical/cloud backup restore.
- Environment dependency: supported private Linux Docker host, reviewed image tags/digests, mounted secrets, optional Collector 0.162.0, Terraform/OpenStack 3.4.0, operator-supplied OVH account/region/image/network. Docker/Terraform unavailable here; registry tag endpoints unavailable in review. No SDK or infrastructure tool installed.
- Security validation pending: canonical container/users/ports/firewall/context, file permissions, runtime roles, telemetry privacy, TLS and state/backend review.
- Live integration pending: all deployment platforms, domain/TLS and hosted CI; none activated or published.
- Known limitations: private synthetic rehearsal only; host network is trusted code access, not untrusted-code isolation. OTLP instrumentation is a small manual protocol exporter, not SDK/full tracing/guaranteed audit. TLS probe forwards no API. Old backups cannot authorize redispatch. Version-tag images still require digest and compatibility resolution.
- Canonical acceptance: PENDING.

## Phase 26 — Minimal teams

- Implementation commit: unique `wip(phase-26):` checkpoint; preceding Phase 25 `e910f95`.
- Implementation: IMPLEMENTED synthetic verified-session/current-membership boundary, organization policy/admins, workspace roles, connector references, immutable shared workflows and shared operator/reviewer approvals. Additive workflow migration 3 preserves unassigned legacy runs.
- Checks run here: 252 workflow/model/deployment unit checks and 52 required PostgreSQL team/approval/runtime/migration/security/role checks on each supported Python version; final 8 team checks on both versions include expired sessions. Ruff, strict typing both targets and frozen audit passed. Existing reliability test was extended to remove the new initiator column before its legacy upgrade. No real identity provider or account is used.
- Checks not run: remote/browser login, OIDC/SCIM, real session issuance/credential lifecycle, production tenant isolation, team UI or public deployment.
- Environment dependency: existing PostgreSQL/Python only; explicit team migration 1 and workflow migration 3. Fake sessions/identities are operator-provisioned and synthetic-only.
- Security validation pending: canonical authorization/tenant/revocation/migration review, protected bootstrap/session audit lifecycle and stronger database isolation against SQL compromise.
- Live integration pending: real identity, tenant-aware external connector accounts, NEXUS identity/protocol and team deployment.
- Known limitations: workspace-wide sharing; one enabled execution principal per step. Nullable old initiators cannot enter teams. Shared DB role is not a tenant sandbox. Logout does not withdraw already-granted reviewer approval; explicit revocation/membership/expiry does. Administrators can review; mandatory dual control is not implemented.
- Canonical acceptance: PENDING.

## Phase 27

Implementation and check records are added as each phase is developed. No unavailable integration is represented as working. No final green command accepts the entire roadmap.
