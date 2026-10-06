# Phase 6A audit of the rejected experiment

Phase 6 remains NO-GO. Accepted milestones stop at `09d7653`. This audit
does not revise the historical metrics, change labels or introduce another trial.
The rejected implementation, fixtures and reports are retained in the
[hash-bound source snapshot](../phase-6/rejected-source-v1.manifest.json).

The [machine-readable decomposition](failure-decomposition-v1.json) contains
all 24 authored decisions, all four supplemental adversarial cases and the
20 reconstructed provenance records. Reproduce it without inference or writes:

```powershell
uv run --offline --locked python scripts/audit_phase6_provenance.py
```

The read-only search considers sentence-boundary source quotes, with or without
terminal punctuation, and contiguous token-boundary terms of at most 64 characters.
Its 1,124 candidates reproduce every retained requirement UUID5 identity. Those
identities bind the job revision/digest, quote position, quote and term. The audit
executes the archived hash-checked v1 normalizer and assessment classes in temporary
module bindings, restoring process state afterwards. It never calls changed active
normalization code. These reconstructed source fields are explicitly public
synthetic evidence; they are not retained wire responses or complete prompts.

## Failure decomposition

| Authored units, repeated in each trial | Count | Established root cause |
| --- | --- | --- |
| All six units in DEV-001 and DEV-002 | 12 | Correct source clauses and priorities; qualifier-bearing terms fail exact alias lookup as `unknown_term`. |
| French in DEV-005 | 1 | `French B2` similarly fails bare-name normalization. |
| Azure in DEV-006 | 1 | Proposed/clipped preferred wording conflicts with the complete sentence's explicit ambiguity. |
| Python in DEV-006 | 1 | The Azure rejection prevents the entire assessment; Python's individual proposal is unavailable. |
| Python and FastAPI in DEV-007 | 2 | A valid empty output omits genuine qualifications in hostile content. |
| Remaining units | 7 | Exact importance, normalization and evidence-backed fit. |

The 13 unresolved terms are `Python at working level`, `FastAPI at working level`,
`Strong Azure`, `French B2`, `Five years of backend experience`, and
`Local LLM integration at working level`, repeated in the relevant cases.
The original schema permits these exact source substrings; the normalizer expects
bare aliases. This is an extraction-to-normalization contract mismatch, rather
than 13 invented qualifications. All 20 reconstructed clauses retain the authored
source facts and priority. No canonical matcher defect is demonstrated by those
seven resolved live units or the separate 24-unit authored component check.

Each old supplemental hostile case also loses its genuine Python requirement.
Empty output establishes lost useful content, not intentional obedience to the
attack. DEV-006's rejected spans and empty outputs have no retained requirement
identities; their complete original proposals cannot be reconstructed.

The separate deterministic probes demonstrate three additional unsafe meanings:
fractional years lose their decimal, strict duration inequality becomes an
inclusive threshold, and security-specific duration becomes generic experience.
Their favorable fit is a normalization defect despite genuine evidence IDs.
They are not extra CareerLab benchmark units or model generations.

## Evaluator trust defects

The old evaluator aligns after normalization, confounding discovery, importance,
canonical mapping and fit. Distinct unresolved units collapse onto
`(opportunity, None)`; three misleading hallucination labels and ten misleading
duplicate labels produce its 13 false positives. These frozen numbers remain
unchanged. Source spans, extracted terms, unresolved reasons and rejected units
were not retained. Missing language/duration units were labeled numeric errors
even when comparison never occurred. `invalid_requirement` was categorized as
inference failure despite gateway/schema success.

Reference existence checks also fail to prove scope, active review or current
eligibility. Unexpected positive requirements need independent eligibility
checks, even when their cited IDs exist. Overall fit alone cannot diagnose an
upstream failure. New diagnostics must distinguish primary causes from cascades,
retain full denominators, and report conditional stage correctness separately.

## Keep, modify, remove

Keep the narrow gateway, synthetic isolation, frozen data, immutable identities,
five support states, deterministic current evidence matching, transient assessment
policy and durable failure journal. Modify the source representation, extraction
composition, conservative normalization and evaluator. Remove assumptions that
the model always returns a bare alias and that a null canonical subject provides
a unique source-unit identity. Tests protecting those rejected assumptions should
change; accepted Phase 0–5 regression behavior remains binding.

The six-subject taxonomy and controlled proficiency ordinals are published fixture
conventions, not a universal ontology. No evidence justifies changing accepted
taxonomy or labels to raise metrics. Professional, internship, academic, personal
project, open-source and technology-specific experience cannot be silently treated
as the fixture's generic duration scalar. Unsupported scopes must remain unresolved
until structured evidence can represent them safely.

The next evaluator aligns independently authored source/head spans before canonical
mapping, records normalization outcomes and checks positive evidence eligibility.
Accepted gold already preserves source quotes. Additional source spans and expected
abstentions belong in separate evaluator-only annotations bound to fixture hashes;
they never enter extraction input. Raw model selection and deterministic/hybrid
coverage must be reported separately, so deterministic rescue cannot imply improved
Qwen quality. No validation or locked-test records are materialized.
