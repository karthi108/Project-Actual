# Phase 6A: Job Intelligence hardening acceptance

Review date: 2026-10-06. **GO for the combined Phase-6/6A development slice.**
All preregistered engineering and development-quality gates passed. This accepts
the hardened implementation under the user's conditional commit policy; it does
not retroactively accept the rejected Phase-6 experiment or enable Phase 7.

The [audit](audit.md), [failure decomposition](failure-decomposition-v1.json) and
[archived rejected source](../phase-6/rejected-source-v1.manifest.json) preserve
the original NO-GO. Its reports and labels were not rewritten. The accepted
Phases 0–5 domain, storage, migration, HTTP and ModelGateway implementations
remain unchanged.

## What changed and why

Qwen now selects source segment IDs, rather than simultaneously proposing terms
and importance that deterministic code might interpret differently. The pipeline
retains original clause/head spans, adds a narrow explicit-clause parser, derives
importance from complete source context, normalizes conservative explicit facts,
and compares only current scoped reviewed evidence. Independent unit failures
cannot remove other genuine requirements. Unknown concepts, thresholds and scopes
remain explicit abstentions; they cannot gain evidence or positive support.

Professional employment, internship, academic, project, open-source and
technology-specific duration cannot use the accepted generic months scalar.
Durations are never summed. Generic months cannot establish positive backend
tenure. Two original legacy backend shortfall units retain only their authored
negative comparison, a fixture convention rather than general experience logic.

The source-first evaluator aligns independently authored provenance before
examining importance, normalization, evidence and fit. It reports raw Qwen and
hybrid extraction separately, independently checks positive evidence eligibility,
and records primary errors and downstream cascades. Checkpoints retain derived
spans/closed labels/references, without complete prompts or wire responses.
Recorded predictions can be decoded without rerunning normalization or matching.

See [the file map](README.md) and [ADR 0008](../adr/0008-source-preserving-job-intelligence-hardening.md).
There is no score, overall recommendation, assessment persistence, new HTTP route,
semantic normalization model call, real-data intake, tool authority or new dependency.

## Frozen evaluation and reproducibility

[Freeze v2](evaluation-freeze-v2.json) binds 99 source/schema/prompt/evaluator/fixture
files and the [preregistered gates](design.md). Its identity is:

```text
f5817af298a71ddcf569c15bceffe5d0ee1a7e91c433d0ae0171942a144f22ca
```

All 99 file hashes still match the report and current implementation after the
run. There was no prompt, rule, fixture, oracle or gate adjustment during or after
inference. Freeze v1 was withdrawn before any inference because an independent
review found a positive backend-scope defect; the
[withdrawal record](evaluation-freeze-v1-withdrawal.json) preserves that decision.
The freeze hashes literal evaluated worktree bytes. Narrow `.gitattributes`
exceptions preserve two hash-checked evaluator artifacts and the audit record
byte-for-byte, and reproduce CRLF checkouts for three new evaluated modules and
the pre-existing `src/actual/profile/__init__.py`. Python Git blobs remain LF;
the accepted profile module's blob is unchanged. This packaging correction
prevents default newline conversion from breaking evaluator hashes on a fresh
checkout. A temporary export of the staged Git tree reproduced all 99 frozen
hashes. The frozen preregistration document also retains an encoding blemish
rather than silently changing its hash.

A startup verification attempt made **zero model calls** and produced the
[preserved abort record](aborted-evaluation-v1.json). Two startup-only diagnostics
then verified cloud-disabled status and exact listener ownership. One unchanged
restart produced the complete run; no inference was retried or repaired.

[Evaluation results v1](evaluation-results-v1.json) is an exact copy of the derived
synthetic report, SHA-256:

```text
903990d81e2784e0c2c3fd161c3d97b8159eadedca16a3ca142dea6d45c8e2aa
```

Run `cd3982917ba848a7b4e544be71b9b32d` completed on 2026-10-05,
21:12:49–21:31:02 Europe/Berlin. **87/87** ordered unique calls were attempted
and schema-valid: 29 cases in each of three trials. No trial was selected or
excluded. DEV-008 remains an accepted invalid-transition fixture and is rejected
before inference. Evaluator labels were loaded only after model attempts ended.

The same installed **qwen3:4b-instruct**, Q4_K_M, through **Ollama 0.34.3** was
used in every call. All 87 metadata records have unique request IDs and the same
provider-reported catalog digest:

```text
0edcdef34593eac1aa2be9c7d06c432dcf81945adca5eca2f27662c18f168ba0
```

Configuration: temperature 0, seed 42, context 4096, output limit 512 and total
request deadline 120 seconds. Recorded gateway inference durations were approximately
9.42–15.68 seconds. Equal outcomes in these trials do not guarantee deterministic
generation. Tags and provider-reported catalog digests do not prove immutable
loaded weights under retagging or host tampering.

Capability `job_requirement_extraction:v2`; output schema
`actual-job-source-output-v2`, schema SHA-256:

```text
eb3c8e3f7acd199f675a759b8c70322e11469405672712c38d750497dcf420c7
```

Instruction SHA-256 is
`afd5f95e914e7c8f96f2ace8414746657db6d4fc8e5ae5698fde7eef99dced97`.
Source, normalization, matching and evaluator versions are respectively
`source-extraction-v2`, `career-normalization-v2`,
`career-evidence-matching-v2` and `source-first-evaluation-v2`.
Per-call configuration, prompt hashes, timestamps, correlation IDs and provider
metadata are retained; full prompt bodies and responses are not.

## Measured public development performance

Counts below apply separately to **each** of the three trials. Repeated trials
do not multiply independent dataset support. Each trial includes seven valid
CareerLab cases / 24 authored units, 14 adversarial cases / 24 genuine units and
eight semantic controls / six genuine units plus two negative documents.

| Measurement | Trial 1 | Trial 2 | Trial 3 |
| --- | --- | --- | --- |
| Schema-valid calls | 29/29 | 29/29 | 29/29 |
| Original raw Qwen extraction TP / FP / FN | 24 / 1 / 0 | 24 / 1 / 0 | 24 / 1 / 0 |
| Original hybrid extraction TP / FP / FN | 24 / 1 / 0 | 24 / 1 / 0 | 24 / 1 / 0 |
| Original extraction precision / recall / F1 | .960 / 1.000 / .980 | .960 / 1.000 / .980 | .960 / 1.000 / .980 |
| Original importance / canonical normalization / exact evidence matching / exact fit | 24/24 each | 24/24 each | 24/24 each |
| Adversarial raw and hybrid TP / FP / FN | 24 / 0 / 0 | 24 / 0 / 0 | 24 / 0 / 0 |
| Adversarial importance / normalization / matching / fit | 24/24 each | 24/24 each | 24/24 each |
| Semantic raw TP / FP / FN | 6 / 0 / 0 | 6 / 0 / 0 | 6 / 0 / 0 |
| Semantic importance / normalization / matching / fit | 6/6 each | 6/6 each | 6/6 each |
| Detected unsafe normalization / unsupported evidence / promotion violations | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| All preregistered gates | GO | GO | GO |

Importance macro F1 and fit macro F1 over supported classes are 1.0 in each live
group. Original fit confusion counts are 13 supported, eight unknown, two gap and
one conflict, all on the diagonal. There is **zero partial-state gold support**
in this live corpus; tests exercise partial support, not measured model quality.
Adversarial fit has 24 supported units; semantic fit has six unknown units.
Full confusion matrices and exact evidence reference diagnostics are in the report.

Original normalization and fit improve from the rejected **7/24** to **24/24**.
Old canonical-after-normalization extraction metrics are not directly comparable
to the new source-first metric. The audit demonstrates the old alias-interface
defects; these were not 13 hallucinated skills. Old adversarial retention of zero
of four supplemental genuine units improves to four of four on those same
postings, with another 20/20 units retained in ten new hostile cases.

All six semantic positives bypass the explicit grammar, and both negative company
narratives remain empty. No raw Qwen miss was rescued by deterministic extraction
in these trials. This supports narrow source-selection utility on these controls,
not broad semantic reasoning quality.

Separate deterministic safety controls passed **24/24** interpretation, evidence
matching and fit decisions: **20/20** safe abstentions and four explicit resolved
meanings, with zero detected unsafe certainty or evidence promotion. The original
authored component check also passed **24/24**. Safety controls make no model
calls: the shared evaluator's raw-Qwen FN24/missed-model-source diagnostics are
**not applicable control telemetry**, not 24 live Qwen failures.

## All observed development errors

One false-positive source repeats in each trial: DEV-006's source segment 3,
offsets 127:163, **“The listing gives no minimum tenure.”** Qwen incorrectly
selects this negative statement as a requirement. Hybrid extraction retains it.
The result has no canonical concept, assertion, threshold, observed value, claim
reference or evidence reference; it is ambiguous, abstained `unknown_term` and
`unknown`, with no declared shortfall. It therefore cannot confer positive fit.

Each report records two diagnostics for this **one** false positive:
`unexpected_model_source_selection` and `unexpected_or_invalid_source_unit`, both
at EXTRACTION. There is no downstream failure on either authored DEV-006 unit.
This is a retained coverage/precision defect, not a perfect extraction result.
It passes the frozen original precision threshold of .90 at .96. No prompt or
filter was adjusted to remove it after seeing the result. A future separately
versioned iteration can evaluate negative requirement language independently.

There are no other observed live source, importance, normalization, matching,
fit, schema, timeout or contamination errors. All rejected-experiment errors
remain documented in the historical audit and report. Zero detected violations
means only these authored development/safety cases and counterfactual tests;
it is not a universal safety guarantee.

## Engineering, integrity and privacy evidence

The final unchanged implementation passed `./scripts/verify_phase6.ps1`, including
the accepted real disposable PostgreSQL harness with the pinned official
PostgreSQL 18.6 image. The final full checks were run after the last source change:

| Check | Result |
| --- | --- |
| Python 3.14.7 full suite | **1,336 passed**, 167.94 seconds |
| Python 3.13.1 full suite | **1,336 passed**, 191.78 seconds |
| Accepted regression support | All 938 Phase 0–5 tests retained, plus 398 intelligence tests |
| Ruff source/tests/migrations/helper lint and formatting | Passed; 113 source/test/migration files and seven current helpers checked |
| Strict mypy | Passed, 76 source files including evaluation/helpers |
| Real migrations / metadata DDL | Upgrade/downgrade/re-upgrade and metadata comparison passed on both interpreters; head remains `0001_career_persistence` |
| Recorded prediction replay | All 87 results decoded and all nine group metrics recomputed identically with runtime normalization/matching disabled |
| Freeze | All 99 hashes unchanged; report source map equals freeze v2 |
| CareerLab verification | Passed on both interpreters again at final review; eight public cases and all 16 accepted input/oracle identities preserved |
| Held-out isolation | Validation and locked-test directories remain absent |
| Rejected evidence | All 39 archived files and original reports/fixtures/manifests unchanged |

The hardening environment manifest identity is
`d8889a7deb51c37ff98a1e38d526d6192d06aed9668077a916c7fce3a77129f3`.
The report separately identifies the accepted Phase-5 oracle manifest and hashes;
the changed project/test metadata is recorded in the new environment manifest
without regenerating accepted records. Historical manifests, dependency pins,
lockfile, accepted OpenAPI artifacts and migrations remain unchanged.

The owned loopback model process was verified cloud-disabled; 509 TCP samples
completed without detected non-loopback established peers. Exact owned-process
cleanup succeeded before final verdict export. Zero models were downloaded and
zero application-state writes occurred. No shared Ollama installation was changed.
The review-day host has Docker stopped and an unrelated Ollama installer process;
neither was started or altered to repeat already-passed checks. Version evidence
describes the recorded evaluation environment, not a newly inspected installation.

The model receives only observable synthetic source segments, with no candidate,
oracle, expected labels, fixture categories or future outcomes. Adversarial
controls cover omission, fabrication, perfect-fit instructions, fake role blocks
and attempted tool authority before/between/after real qualifications, including
inline semicolon forms. No instructions were accepted as requirement units in
that suite, and every genuine unit was retained. No model has tools or authority
to mutate state. Predictions remain proposals even when structurally validated.

Only necessary derived public synthetic evaluation evidence is committed. Full
prompts, wire responses, evaluator storage, local checkpoints, personal data,
credentials and model weights remain outside version control. Synthetic labels
and local access restrictions cannot detect real prose deliberately mislabeled
synthetic; the supported evaluation uses fixed hash-checked public fixtures.

## Limits and closure

This tiny public, shared-ancestry corpus is development performance, not held-out
or real-world job-fit accuracy. There are six canonical fixture concepts, little
class support, no live partial-state support and bounded English requirement
forms. Repetition does not establish generalization. Conservative abstention
reduces coverage for unfamiliar aliases, technology versions, ambiguous language,
fractional/ranged/strict durations and unsupported experience scopes. Repeated
literal clauses and duplicate canonical subjects fail closed.

The bounded directive/role handling is not a general prompt-injection defense;
ordinary instruction-like job verbs can lose coverage. TCP sampling is observation,
not a firewall, and can miss transient connections, DNS and UDP. Reviewed synthetic
support is not independent evidence authenticity, actual professional proficiency,
employability or hiring probability. No score, recommendation quality, CV tailoring,
letter, submission, connector, browser, frontend, voice or workflow quality is claimed.

Acceptance authorizes one focused local combined implementation commit after the
final review. No push, tag, release, real-data access or Phase-7 work is authorized.
The commit containing this review records the accepted hardened slice; the original
Phase-6 NO-GO remains historical evidence.
