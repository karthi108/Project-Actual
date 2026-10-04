# Phase-0 architecture decision register

Date: 2026-10-04. Status: proposed baseline. These grouped decisions keep the initial contract readable; split/replace individual entries when later implementation needs a focused ADR. No runtime component is implemented by this register.

## D01 — Local-only, single-user first release

**Problem:** immediate privacy and a finishable first product. **Decision:** deploy all v0.1 processing locally; interpret the master control-plane server as a role. **Alternative:** cloud-first hybrid. **Trade-off:** the computer must be available; no remote/shared access. **Revisit:** useful personal workflow is demonstrated and remote use is explicitly wanted. Cloud requires new identity, network, secrets, backups and data-boundary evidence.

## D02 — A narrow assistance release before automation

**Problem:** the full roadmap delays daily value and increases consequence. **Decision:** phases 1-9 establish manual intake, truthful assistance, review and manual tracking. **Alternative:** build generic workflows/connectors first. **Trade-off:** automation thesis is not yet demonstrated. **Revisit:** recurring real work justifies IR/runtime and evaluation-backed activation.

## D03 — Modular monolith with relational state

**Problem:** preserve responsibilities while avoiding deployment complexity. **Decision:** Python modules, PostgreSQL when persistence is required, one backend application; events accompany state rather than replacing it. **Alternatives:** microservices, event sourcing, graph database. **Trade-off:** enforce boundaries in code/reviews and pay for later splitting if necessary. **Revisit:** independent scale/deployment needs or measured graph queries demand a different store.

## D04 — Incremental dependency and repository growth

**Problem:** speculative packages hide the missing product. **Decision:** documentation now; a small CareerLab package next; add DB/API/model/UI only in their phases. Select compatible stable versions then. **Alternative:** generate the target monorepo in advance. **Trade-off:** dependency integration is staged. **Revisit:** real reuse/deployment boundaries justify packages/services.

## D05 — Local typed model proposals, no model authority

**Problem:** semantic extraction needs flexibility without granting execution power. **Decision:** one Ollama/Qwen adapter behind ModelGateway, explicit local endpoint/model configuration, bounded typed proposals. **Alternatives:** direct provider calls throughout business logic, paid APIs by default, autonomous agent tools. **Trade-off:** local hardware limits speed/quality and schema validation does not prove truth. **Revisit:** measured inadequacy and an explicit privacy/cost decision justify a new adapter.

## D06 — Provenance and support are explicit, not truth certificates

**Problem:** a fluent draft can fabricate qualifications. **Decision:** assertion-level evidence/status, review method, bounded factual rendering and human semantic review. **Alternative:** trust model confidence or presence of a citation. **Trade-off:** more correction/review work, and residual human error. **Revisit:** demonstrated safer generation may broaden rendering; claims remain traceable.

## D07 — Future IR is constrained data, not executable code

**Problem:** generated programs would bypass validation and authority. **Decision:** future registered capabilities, bounded typed graph/predicates and immutable versioned definitions; Phase 0 only records principles. **Alternatives:** generated Python, unrestricted shell/browser agents, early Temporal. **Trade-off:** unsupported workflows require implementing a capability. **Revisit:** concrete workflow needs refine the IR in Phase 10; no model grants authority.

## D08 — Effects, exact review and business intent are separate

**Problem:** the original taxonomy mixes effect/risk, mutable content defeats approvals, and workflow-version keys permit repeat submissions. **Decision:** primary effect kind plus risk/reversibility; approval binds actual contents/destination; stable business intent deduplicates across versions. Recheck authority at dispatch and handle uncertain remote outcomes. **Alternative:** approve whole workflow, trust artifact paths, retry every timeout. **Trade-off:** explicit state/reconciliation and extra review. **Revisit:** provider guarantees refine recovery, never infer exactly-once behavior from local uniqueness.

## D09 — Security/privacy/recovery accompany capability introduction

**Problem:** late roadmap hardening can imply early unsafe real use. **Decision:** baseline controls are prerequisites when data/API/model/runtime/connectors appear. Phase 12 starts read-only, and later phases deepen reliability/security. **Alternative:** postpone controls until phases 23/24. **Trade-off:** a feature may stay disabled until its own evidence exists. **Revisit:** new threats require updated controls and tests.

## D10 — Evaluation is partitioned and honest

**Problem:** tuned synthetic demonstrations can be mistaken for capability. **Decision:** explicit rubric, development/validation/frozen acceptance separation, withheld labels, hashes, failure reporting and real impact measurements. **Alternative:** use dogfooding alone or inspect the test set while tuning. **Trade-off:** evaluation discipline and no universal claims from small samples. **Revisit:** more real observations refine future datasets without contaminating existing reports.

## D11 — Minimize durable private content

**Problem:** event/audit history can conflict with deletion. **Decision:** private storage outside Git, metadata-only default diagnostics, short personal retention defaults, derivative purge and deletion-aware restore. **Alternative:** retain full prompts/events forever for observability. **Trade-off:** less debugging detail; optional local diagnostics need explicit handling. **Revisit:** consequential actions or deployment change retention needs; append-oriented audit never means indefinite personal text storage.
