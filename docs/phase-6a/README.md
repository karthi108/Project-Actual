# Phase 6A: Job Intelligence hardening

The combined Phase-6/6A slice passed its preregistered development gates; the
commit containing [the acceptance review](acceptance-review.md) records the
milestone. The original Phase-6 experiment remains historical NO-GO evidence.
Read [the audit](audit.md), [design and gates](design.md), [measured results](evaluation-results-v1.json) and
[ADR 0008](../adr/0008-source-preserving-job-intelligence-hardening.md).

Important files (module paths below are relative to `src/actual/`):

| File | Responsibility |
| --- | --- |
| `capabilities/job_requirements.py` | Closed source-selection schema and trusted prompt v2 |
| `job_intelligence/extraction.py` | Observable segmentation, atomic spans, narrow explicit grammar |
| `career/requirements.py` | Source-bound interpretation, constraints and abstention invariants |
| `job_intelligence/normalize.py` | Conservative explicit meaning and importance |
| `job_intelligence/matching.py` | Current exact reviewed evidence; no model authority |
| `job_intelligence/service.py` | Stages, isolated unit failures and transient result |
| `evaluation/intelligence_v2.py` | Independent source-first gold alignment and failure localization |
| `scripts/phase6a_results.py` | Derived prediction checkpoint round trips without re-evaluation |
| `scripts/evaluate_phase6a_live.py` | Fixed 3-trial local development evaluation |
| `datasets/phase6a/*inputs*.json` | Separate explicitly synthetic observable controls |
| `datasets/phase6a/*oracles*.json` | Evaluator-only authored meanings, never inference input |

The model receives only synthetic job segments. Candidate evidence is used after
inference. There is no API integration or arbitrary file/prompt intake. No model
has tools. No real profiles, jobs or documents are enabled.

Run deterministic checks with the existing disposable PostgreSQL harness:

```powershell
./scripts/verify_phase6.ps1
uv run --offline --locked careerlab verify --manifest datasets/manifests/careerlab-hardening-env-v1.json
```

The live runner has no arguments, uses existing installed weights and a private
cloud-disabled loopback Ollama child, and records every attempt without retries:

```powershell
$env:ACTUAL_MODEL_MODE = 'synthetic-development'
uv run --offline --locked python scripts/evaluate_phase6a_live.py
```

Reports/checkpoints go to ignored `evaluation-runs/`. The final review preserves
only necessary derived synthetic evaluation evidence under `docs/phase-6a/`. The
old runner fails explicitly; its rejected source remains in the hashed archive.
Fresh runs measure variability; they must not replace the frozen acceptance
record or silently relax its gates.

Limits: this tiny public shared-ancestry corpus proves no held-out or real-world
accuracy. Conservative normalization sacrifices coverage for truthfulness.
Unfamiliar scopes, versions, fractional/ranged duration and ambiguous language
remain unresolved. Two legacy backend units use the fixture's authored negative
duration comparison; generic months cannot establish positive backend support.
Repeated exact quotations and duplicate canonical subjects
fail closed. Directive detection is a bounded baseline, not a general malicious
document classifier; job advertisements with ordinary instruction-like verbs may
lose coverage. Metadata does not guarantee immutable model tags or deterministic
generation. TCP sampling can miss brief connections and does not inspect DNS/UDP.
Reviewed synthetic support is not independent real-world verification. Future
milestones require separate authorization; stop before Phase 7.
