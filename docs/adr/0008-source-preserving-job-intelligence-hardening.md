# ADR 0008: source-preserving Job Intelligence hardening

Date: 2026-10-05. Status: accepted at the 2026-10-06 Phase-6A gate review;
see [acceptance evidence](../phase-6a/acceptance-review.md).
Supersedes the unaccepted extraction/normalization representation in ADR 0007.
Accepted Phases 0–5 contracts are unchanged.

The rejected experiment used a model-selected term and priority with a normalizer
that assumed bare aliases. The evaluator aligned after normalization, losing the
distinction between missed source and unresolved semantics. Case-wide rejection
also deleted independent valid requirements. The read-only [audit](../phase-6a/audit.md)
and hash-checked archived source preserve the evidence for this decision.

Use one narrow Qwen source-selection capability, retain atomic source/head spans,
and normalize explicit meaning deterministically with an explicit abstention.
Union semantic discovery with a small precision-first explicit grammar; report
their contributions separately. Importance and constraints retain full meaningful
context. Independent clauses separated by malicious text remain discoverable;
dependent ambiguity clauses cannot be clipped away. Treat fake role wrappers as
untrusted content boundaries, including their interiors.

Current reviewed evidence and final five-state support remain deterministic.
Recheck a requirement's source interpretation at matcher admission. A known
concept can have unknown threshold; this cannot claim candidate support. Scoped
experience cannot use generic profile months. The two legacy backend duration
units retain only their published shortfall comparison; positive backend support
requires a future typed scope contract and is currently unknown. No accepted
evidence schema is expanded merely to make a model output fit.

Source-first evaluator annotations are separate from observable data and retain
accepted labels. Stage diagnostics identify primary failures and cascades. Store
only derived spans, closed labels, exact references and model metadata for the
public synthetic evaluation; reconstruct recorded predictions without rerunning
normalization or matching. Raw prompts and wire responses remain excluded.

No semantic-normalization model call is justified while deterministic normalization
can safely resolve published aliases and abstain. This trade-off reduces semantic
coverage; a later independently evaluated narrow capability may be justified.
Repeated literal clauses and duplicate canonical subjects currently fail closed;
this is a utility limit, not a claim of complete document understanding.

Assessments remain transient. No new HTTP route, persistence, score, overall
recommendation, model/provider, real-data access or tool authority is introduced.
The [preregistered gates](../phase-6a/design.md) determine GO/NO-GO separately from
software tests. A failed critical gate leaves acceptance at Phase 5 and blocks a
milestone commit. Stop before Phase 7.
