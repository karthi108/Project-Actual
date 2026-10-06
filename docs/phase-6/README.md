# Job Intelligence development usage

**NO-GO, unaccepted.** Read the [acceptance review](acceptance-review.md) and
[recorded results](evaluation-results-v2.json). Three complete live trials failed
quality gates; known normalization and evaluation-diagnostic defects remain.

This slice extracts requirements from explicitly synthetic public development jobs
and compares them with current reviewed synthetic profile evidence. Read the
[design and preregistered gates](design.md) before running it. Quality results are
reported separately; implementation alone does not mean Phase 6 is accepted.

## Important files

| File | Responsibility |
| --- | --- |
| `src/actual/capabilities/job_requirements.py` | Fixed extraction prompt, versions and closed structured schema |
| `src/actual/job_intelligence/service.py` | Synthetic/scoped admission, gateway call and deterministic composition |
| `src/actual/job_intelligence/normalize.py` | Exact source checks, explicit alias/level/month rules and unresolved meanings |
| `src/actual/job_intelligence/matching.py` | Current reviewed evidence decisions and grounded explanation templates |
| `src/actual/career/assessments.py` | Transient five-state matrix, immutable source/profile identities and references |
| `src/actual/job_intelligence/development.py` | Eight fixed observable input paths and accepted hashes; no oracle loader |
| `src/actual/evaluation/job_intelligence.py` | Separate authored-label loading, component checks, task metrics and gate decisions |
| `datasets/phase6/` | Four supplemental public adversarial inputs with separately packaged evaluator labels |
| `scripts/evaluate_phase6_live.py` | Three genuine local-Qwen trials, fixed synthetic inputs and metadata/derived prediction report |
| `scripts/phase6_journal.py` | Atomic metadata/derived-result checkpoint after each attempt, including cancellation |
| `scripts/phase6_monitor.py` | Bounded, metadata-only TCP observation of the owned Ollama process tree |

The application/domain depend on the internal gateway, not Ollama. Only the development
composition script creates the accepted Ollama provider. Model input contains synthetic
job text only. Candidate facts remain in deterministic matching; no CV/history,
ground truth, category/lineage, manifests or future outcome enters inference.

## Deterministic checks

With supported Python 3.13 and 3.14 installed and Docker available:

```powershell
uv sync --locked
./scripts/verify_phase6.ps1
```

This uses the unchanged accepted disposable-PostgreSQL harness and runs all prior
checks plus Phase-6 tests. It never starts Qwen. Interpreter overrides are supported:

```powershell
./scripts/verify_phase6.ps1 -PythonExecutables @('C:\Python314\python.exe')
```

Select the new environment manifest explicitly when regenerating/verifying CareerLab:

```powershell
uv run --locked careerlab generate --manifest datasets/manifests/careerlab-intelligence-env-v1.json
uv run --offline --locked careerlab verify --manifest datasets/manifests/careerlab-intelligence-env-v1.json
```

The five accepted historical manifests/fixtures remain unchanged. The new identity
records the current project/lockfile environment and preserves every input/oracle hash.
Do not pass any manifest or evaluator file to Job Intelligence. Invalid case 008 must
still be rejected by the accepted bridge before inference.

## Live development evaluation

The installed default remains `qwen3:4b-instruct`; reviewed Ollama compatibility remains
0.34.3. Existing Phase-5 configurable installed-Qwen choices and loopback/privacy gates
apply. This script starts and cleans up an owned hidden cloud-disabled loopback server
using existing weights. It does not change the shared server, download models or accept
arbitrary text/path arguments.

```powershell
$env:ACTUAL_MODEL_MODE = 'synthetic-development'
uv run --locked python scripts/evaluate_phase6_live.py
```

The run has three declared trials, each containing seven valid CareerLab development
scenarios and four supplemental adversarial controls. It explicitly requests 4096
context tokens, maximum 512 output tokens, temperature zero, seed 42 and a total
120-second deadline per call. There are no inference retries/repairs. A failed call
remains in the full-denominator task report. Candidate matching does not invoke Qwen.

The machine-readable report is written to ignored
`evaluation-runs/phase6-<run-id>.report.json`, with an atomic
`phase6-<run-id>.checkpoint.json` updated after every attempt. It contains derived synthetic predictions,
references, per-task metrics, confusion matrices, every failure, frozen source hashes,
dataset identity, capability/schema/prompt hashes and safe model/run metadata. Raw
prompts/responses and evidence excerpts are not archived. The final engineering record
may version the reviewed synthetic report; future personal content is not authorized.
Console output contains case IDs and safe outcome codes, never model bodies.

An inspection failure cancels inference and prevents another call. The checkpoint
retains completed results and the interrupted attempt; unattempted cases remain in
the report's full denominators with an explicit `not_attempted` failure. A failed
checkpoint write stops progress and preserves the previous valid file. Inspection
failures never report a successful zero-external-connection observation.

The original runner stopped after 16 observed outcomes and lost its in-memory task
predictions before producing a report. [Its abort record](aborted-evaluation-v1.json)
preserves the observed failures and unavailable metrics. The checkpointed runner's
new, separately identified trials use the same frozen prompt, schemas and domain
rules. They cannot erase the first run's NO-GO. Source freezes distinguish both runs.

An exit code of 0 means the recorded quality gates passed; 1 means NO-GO or an explicit
environment failure, and 2 rejects unsupported CLI arguments. Inspect the report before
claiming acceptance. The runner loads development evaluator answers after model calls;
normalization/matching component checks intentionally use authored requirements but
never invoke inference with them.

## Meaning and limits

`supported` means a current reviewed-supported claim and qualifying evidence cover the
same explicit structured assertion. It is not independent authentication. `partial`
applies to reviewed lower nonzero skill support; lower reviewed language/months is a
`gap`. Missing/unreviewed/withdrawn support stays `unknown`. Contradictions stay
`conflict`. Self-reported lower values expose a separate declared shortfall.

Unresolved terms/proficiency/versions remain visible as unknown requirements. For
example, professional French is not automatically B2, AWS is not Azure, and a personal
project is not silently professional experience. Source quotes and schema validation
do not prove extraction meaning. The current evaluator measures canonical alignment
after normalization; it cannot independently diagnose unresolved extraction units.
Its unresolved-key collisions must not be interpreted as proven invented requirements.
The acceptance review documents that measurement limitation without changing the
frozen report or gates.

Assessments remain unreviewed proposals. Their stable identities, source/profile
digests and exact evidence references make changes detectable; validate against the
current sources before reuse. Counts and explanations are deterministic. There is no
numeric match percentage, overall recommendation, storage table/event or new HTTP route.

Seven scenarios, 24 requirement units and six distinct posting texts share ancestry.
Three generations do not create 72 independent units. Partial has no authored
CareerLab labels; supplemental edge tests are engineering coverage, not benchmark
support. Neither held-out generalization nor real-world accuracy is established.

Source-instruction checks and adversarial tests are a baseline, not a universal prompt
injection defense. TCP samples cannot prove absence of transient/UDP connections or
host compromise. Trusted Python can change registries or invoke providers; this is not
a hostile-code sandbox. Startup can leave an incomplete checkpoint, and a taskkill
timeout can bypass the cleanup fallback; actual cleanup needs verification. No real
data, tools/effects, CV work or Phase 7 is authorized.
