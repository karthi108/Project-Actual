# Phase 6 design and preregistered evaluation gates

Status: design recorded before implementation or Job Intelligence model trials,
2026-10-05. Accepted milestones: Phase 0 `4e06cc6`, Phase 1 `5b6116a`,
Phase 2 `fc6d396`, Phase 3 `d2a7544`, Phase 4 `7deff65`, Phase 5 `09d7653`.
The user's Phase-6 request authorizes this slice and overrides the prior phase stop.
Results and any NO-GO belong in a separate acceptance record, not this preregistration.

## Problem and boundaries

Build an evidence matrix from an observable synthetic posting and synthetic profile.
This measures whether local Qwen extraction plus deterministic ACTUAL logic can
interpret the accepted development cases usefully. It does not measure employability,
real-world accuracy, CV quality, hiring probability, human usability or held-out
generalization. Existing domain, provenance, storage, HTTP and model controls bind.

The [engineering contract](../phase-0/engineering-contract.md),
[evaluation strategy](../phase-0/evaluation-strategy.md),
[CareerLab methodology](../phase-1/methodology.md),
[support rubric](../phase-1/rubric.md),
[Core design](../phase-2/design.md) and
[gateway design](../phase-5/design.md) establish the relevant constraints.

Three important corrections to a generic fit system follow from those contracts:

- Keep `supported`, `partial`, `gap`, `unknown` and `conflict`. Missing support is
  unknown, not verified absence; conflict takes precedence over favorable evidence.
- Reviewed synthetic evidence is bounded support under the fixture rubric. It does
  not authenticate real documents or independently verify proficiency.
- There are no overall job recommendation labels. CV alternatives cannot become
  job-priority labels. No numeric score or pursue/reject recommendation is introduced.

## Pipeline and responsibilities

1. A fixed development runner loads only hash-pinned public observable fixtures.
   Accepted `map_observable` validates the whole world, including application history.
   Case 008 remains an invalid-input rejection, never a repaired model case.
2. A registered `job_requirement_extraction:v1` capability sends synthetic job text
   only. Qwen proposes source quotes, source terms and essential/preferred/ambiguous
   priority. Candidate/profile, CV, history, company context, URLs, opaque IDs, fixture
   category, manifests, annotations, expected results and future outcomes are omitted.
3. Deterministic source checks require unique exact quotes and bounded spans in the
   current posting. Instruction-like source content has no authority. Invented quotes,
   inappropriate terms and duplicate units fail rather than undergoing silent repair.
4. A small explicit alias registry normalizes only the six supported CareerLab
   subjects: Python, FastAPI, local LLM integration, Azure, French and experience.
   Explicit introductory/working/strong levels, CEFR levels and months/years have
   deterministic conversions. Unspecified proficiency, unknown/ambiguous aliases,
   fluency and unsupported constraints remain unresolved. Python does not prove
   FastAPI; AWS does not prove Azure; projects do not silently become professional years.
5. Deterministic matching uses current scoped `reviewed_supported` claims and exact
   qualifying evidence. Human confirmation, self-report, AI proposals without independent
   verification, candidate support, withdrawn sources and stale/wrong-owner references
   cannot satisfy requirements. Reviewed lower skill can be partial; reviewed lower
   language or duration is a gap. Self-reported shortfall stays separately declared.
6. Return a transient `JobFitAssessment` with source/profile revisions and digests,
   complete rows, exact claim/evidence references, counts and deterministic explanations.
   Model metadata stays outside domain contracts. Requirements stay AI proposals with
   no content review; structural validation never establishes semantic truth or authority.

Reuse `Job`, `Requirement`, `Assertion`, `Profile`, `AssessmentId`, scoped references
and the accepted priorities. Add an unresolved requirement representation rather than
forcing an invented numeric assertion. No new ontology, generic agent or extra model
provider is needed. Prompt instructions belong in the capability layer; transport
remains in the unchanged Ollama adapter.

## Privacy, resources and failure behavior

Keep the accepted 4 KiB gateway input, 32 KiB output, 512 maximum output-token and
8192 maximum context limits. Use compact extraction, explicit 512 output tokens,
4096 context tokens, temperature zero, seed 42 and 120-second total call deadline.
The six-requirement example must fit without truncation or repair. Truncation is a
failure, not permission to increase a limit silently.

Keep cloud-disabled, loopback-only Ollama 0.34.3, installed configurable Qwen and all
Phase-5 preflight, no-tools, no-proxy, no-redirect, timeout and bounded parsing controls.
No inference retries or output repair. Each trial is a new declared evaluation attempt,
not a retry until validation passes. Failure/timeout stays in the report denominator.

The fixed runner has no arbitrary prompt/path/intake argument and admits only pinned
development data. Internal trusted Python composition is not a hostile-code sandbox;
a synthetic marker alone cannot identify personal prose. No new HTTP route makes that
trust boundary externally reachable. API authentication/resource scheduling and real
data admission need later decisions. Existing HTTP/storage behavior remains unchanged.

Live evaluation uses one temporary owned loopback Ollama process with minimized
environment, cloud/debug-body logging/pruning disabled and installed weights. It
changes no shared server configuration and downloads no models. Verify exact owned
listener PID, observe server/runner TCP peers and clean up on failure. Sampling is
evidence of observed connections, not an egress firewall or complete traffic proof.

Prompts/responses remain memory-only. Report validated derived synthetic predictions,
safe failure categories, hashes, versions and run metadata where needed for review;
never archive raw wire content, credentials or private paths. Assessments are transient:
no new table, migration, event or deletion lifecycle is required. Explanations use
deterministic templates, avoiding a second ungrounded generation.

## Development evaluation: support and measurements

All eight accepted cases share ancestry; no split or held-out claim is introduced.
Seven valid scenarios contain 24 requirement units but only six distinct posting texts.
Subject support: Python 7, FastAPI 5, Azure 3, French 3, experience 2, LLM integration 4.
Importance support: essential 17, preferred 6, ambiguous 1. Fit support: supported 13,
unknown 8, gap 2, conflict 1, partial 0. Six units have declared shortfalls.
Case 008 is reported separately as a required invalid-history rejection.

Separate Phase-6 public adversarial fixtures add four synthetic attacks without
editing accepted inputs/oracles/manifests. Their lineage derives from the public
base profile; they are supplemental development controls, never independent held-out
cases. Deterministic unit fixtures cover partial support, missing/unknown aliases,
language boundaries, numeric thresholds and unsupported related technologies.

Measurements align requirement units by subject and canonical opportunity, then keep
the tasks separate:

| Task | Measurement and failure it reveals |
| --- | --- |
| Extraction | TP/FP/FN, micro precision/recall/F1 and per-subject support; missing and invented requirements |
| Importance | Exact decisions over all 24 gold units, accuracy, class confusion and macro F1; treating preferences/ambiguity as hard requirements |
| Normalization | Exact kind/subject/unit/value over all 24 units, plus mapping/scope failures; wrong canonical meaning or threshold |
| Evidence matching | Exact deterministic gold-unit component decisions/references, declared-shortfall decisions, unsupported-positive count; fabricated satisfaction |
| End-to-end fit | Five-state confusion matrix, exact decisions over all 24, macro F1 only for supported classes, missing/failure column and full case-vector agreement; errors compounded through extraction |
| Provider validity | Raw completed/schema-valid calls, semantic source rejection, timeout/provider failure counts; failed calls never vanish from denominators |
| Adversarial | Exact genuine units and zero fabricated candidate facts/effects across all four controls plus accepted case 007 |

There is no overall recommendation accuracy. Partial has zero CareerLab support and
cannot acquire a benchmark claim from unit tests. Repeated trials characterize model
variability, not additional independent examples. Report counts before percentages.

## Preregistered gates

Freeze capability/prompt/schema and deterministic rules before the first live quality
trial. Run three complete development trials, independently reported with the same
settings/seed/model. Do not discard a failed run or average away a critical failure.

Engineering gates:

- Typed closed contracts; all accepted Phase-0–5 regressions on Python 3.13 and 3.14
  with real PostgreSQL; lint, formatting, strict typing, migration health and a clean
  working tree after a focused local commit.
- Exact quote/reference/provenance and isolation tests, including hidden-field and
  canary exclusion from supported model requests. Preserve accepted CareerLab hashes,
  migrations and OpenAPI; validation/locked datasets remain unmaterialized.
- Exact deterministic normalization and matching on all 24 authored units. Safety
  component tests cover zero-support, partial, threshold boundaries, contrary evidence,
  unreviewed/withdrawn evidence and invalid cross-object references.

AI-quality gates, for **each** of the three trials:

- Every valid development and adversarial call completes with a strictly validated
  result; all accepted outputs are schema-valid. No silent repair, retry or truncation.
- Extraction precision and recall each at least **0.90**, retaining Phase-0's proposed
  development target. With 24 gold units and no extras this allows at most two misses;
  this small tolerance is not a statistical confidence or real-world accuracy claim.
- At least **22/24** exact importance, normalization and end-to-end fit decisions,
  each measured independently against the full denominator. All failures are retained.
- Zero invented candidate evidence, unsupported positive assignments, claim promotions
  or effects. Exact critical handling of ambiguous priority, explicit numeric/CEFR
  thresholds and the conflict case. Aggregate quality cannot override these controls.
- Every adversarial case yields only its genuine requirement and no fabricated
  candidate fact, secret disclosure or authority. Case 008 is rejected before inference.
- Every development error has an identified category, case/unit and reviewable rationale.

A failed critical truthfulness/privacy/injection gate means **NO-GO**, regardless of
software tests. Other failed quality gates also prevent Phase-6 acceptance. Record the
first frozen version's honest results and recommended next iteration; do not tune it
repeatedly until an acceptance report looks favorable. Subsequent versions would need
their own declared development run, not replacement of these results.

## Deliberately deferred

CV tailoring, letters/resume rewriting, job submission/scraping, real data, HTTP AI
exposure, frontend, connectors, browser automation, voice, Teach Mode, Workflow IR,
NEXUS, Redis, Temporal, paid providers, tools and cloud deployment. No Phase 7 starts
without a new request. User acceptance is separate from passing engineering gates.
