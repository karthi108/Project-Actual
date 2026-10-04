# Phase 1 acceptance evidence: CareerLab

Status: Phase-1 engineering gates satisfied on 2026-10-04. Phase 0 was accepted by the user at commit `4e06cc6`; this work follows its bounded [CareerLab plan](../phase-0/phase-1-plan.md). Record the final Phase-1 source commit through Git history; no Phase-2 work is authorized or included.

## Delivered result

Eight explicitly synthetic public development cases now have closed fixture schemas, separate observable and evaluator serialization, authored requirement/CV/draft annotations, scoped evidence checks, causal timeline checks, a development-only CLI and canonical version/hash packaging. Seven ordinary inputs pass validation. `CAREER-DEV-008` is intentionally invalid and is rejected with exactly `application_transition`; paired dataset validation checks that this failure matches its evaluator annotation.

Every generated record has a synthetic marker and a stable scenario-local identity. Observed recruiter messages belong to input history. Future scripted outcomes, requirement interpretations, acceptable CVs, expected blocks/rejections and the secret-canary answer remain in separate evaluator files. Category and ancestry metadata remain in the author/evaluator manifest.

All eight cases share candidate/evidence/CV/template ancestry and form **one development component**. Validation and locked-test datasets remain unmaterialized. No locked test was frozen, generated, inspected or tuned against. Split tests use handcrafted public metadata, not a held-out acceptance dataset. No model-quality or real-world generalization measurement is claimed.

## Design review and resolved ambiguities

The [methodology](methodology.md) and [rubric](rubric.md) were defined before final artifact generation. The [decision record](../adr/0002-careerlab-fixture-methodology.md) records the bounded choices.

- French A2 self-report remains unknown for reviewed support, with a declared shortfall against B2. Azure learning does not establish strong Azure. Reviewed one-year duration is a gap against five years. This preserves the accepted example without upgrading unreviewed statements into facts.
- Skill/language ordinal values, reviewed scalar experience, draft support requirements and CV relevance/tie handling are explicit fixture conventions. Aliased opportunities receive one primary requirement annotation set and cannot multiply CV relevance.
- Seed changes alter authored context, names and plausible fixed-date offsets while preserving relationships. Eight template-related cases are not randomly divided into supposedly independent splits.
- Draft prose and proposal identities avoid adjectives announcing expected safety decisions; evidence status/provenance remains observable. Malicious instructions remain visible source text, while their canary answer is absent from input.
- Independent methodology, annotation and integrity task reviews found mismatched CV rubric wording, redundant alias annotations and missing negative invariants. These were corrected before delivery. Further regressions cover masked contradictory evidence, future outcomes after closure, real parsed `.invalid` URL hosts, malformed snapshot timestamps and conflicting same-opportunity source text.

Public annotation review checked all eight labels against source facts and the published rubric, separately from input construction. These were assistant task reviews, not independent employer judgments or a human accuracy study. Author assumptions can still be shared; the limitations remain explicit.

## Checks actually run

Host: Windows, PowerShell, uv 0.11.7. Runtime generation has no third-party dependencies. Locked development tools: pytest 9.1.1, Ruff 0.16.10 and mypy 2.4.0; build backend setuptools 84.0.0. Both supported installed interpreter branches were exercised.

Commands ran from the repository root. Test temporary directory paths were resolved and checked to remain inside this workspace before pytest could replace them.

| Command | Result |
| --- | --- |
| `uv sync --locked` | Locked development environment installed successfully |
| `uv run --locked pytest -q --tb=short` | **183 passed**, Python 3.14.7, 7.54 seconds |
| `uv run --isolated --python C:\Python313\python.exe --locked pytest -q --tb=short --basetemp=.pytest-tmp-careerlab-313` | **183 passed**, Python 3.13.1, 6.96 seconds |
| `uv run --locked ruff check src tests` | All checks passed |
| `uv run --locked ruff format --check src tests` | 14 Python files already formatted |
| `uv run --locked mypy` | Strict check passed for 10 source files |
| `uv run --locked careerlab generate` | Final 8 inputs, 8 separate evaluator files and manifest generated after validation |
| `uv run --offline --locked careerlab verify` | Final bytes/hashes, source identity, record membership, shapes and paired invariants verified on Python 3.14.7 |
| `uv run --offline --isolated --python C:\Python313\python.exe --locked careerlab verify` | Byte-identical inputs, evaluator records and manifest regenerated from the same source/seed on Python 3.13.1 |
| `git diff --check` and final staged equivalent | No whitespace errors |
| Staged Git blob SHA-256 comparison | All 13 source/configuration hashes and 8 input hashes match the manifest; no evaluator/locked/environment artifacts staged |

The tests cover strict shape/literal handling, duplicate JSON keys, scoped references/provenance, invalid values/seeds, causal histories, safe CV alternatives, exact negative-case reasons, direct/transitive split ancestry, normalized posting duplicates, canonical repeatability, meaningful seed variation, separate directories/serializers, canary/future-outcome exclusion, altered/missing/extra files and fresh-process CLI operation. Path-boundary checks reject overlaps and artifact aliases; tests do not claim a hostile filesystem sandbox.

Earlier failures were resolved rather than suppressed: shared Windows pytest temporary-directory permissions required a dedicated project base directory; initial in-progress checks exposed lint/type/test assumptions; adversarial reviews exposed actual validator/rubric gaps described above. The final suites contain no skipped tests or known failing assertions.

## Reproducibility identity

The committed [manifest](../../datasets/manifests/careerlab-dev-v1.json) is the authoritative per-record/source-hash inventory.

| Identity | Value |
| --- | --- |
| Dataset | `careerlab-development-v1` |
| Generator | `careerlab-generator-v1` |
| Seed | `20261004` |
| Input/oracle schemas | `careerlab-input-v1` / `careerlab-oracle-v1` |
| Rubric | `careerlab-support-v1` |
| Dataset SHA-256 | `a7d59618b371c0e51a5d6b09798eec1b48e82dbe37c5fe307a20f1bd0e8f40a4` |
| Methodology SHA-256 | `f579ed08ae9ed3e9da159a3ef853084518ac778bb65faa52d0348bb6d4f37049` |
| Rubric SHA-256 | `130f62d6824808ee4a07ccf22dde1bb45893370011b20b5ecae6ca0b125bba41` |

The manifest records the generator version and 13 source/configuration hashes: every CareerLab module, methodology, rubric, `pyproject.toml` and `uv.lock`. Each of the eight rows records input/oracle hashes and synthetic development membership with ancestry. Dataset identity hashes the canonical manifest body before its own digest is added. Source/fixture/configuration line endings are fixed to LF in `.gitattributes` for reproducible checkouts.

The public input files and manifest are committed. Generated oracle files remain in the ignored evaluator directory; public annotation authoring source permits their exact regeneration. A future evaluated component must receive only the observable input directory, not authoring code, evaluator files or manifests. The acceptance record is excluded from the manifest to avoid circular identity.

## Gate assessment and remaining limits

The accepted gates are demonstrated for reproducibility, meaningful seed variation, synthetic markers/IDs, strict schemas, scoped evidence, explicit unknowns/conflicts/CV alternatives, negative-case rejection, timeline checks, serialization boundaries, split-isolation checks and artifact identity. A public worked example was inspected: reviewed Python/FastAPI/integration at working level, Azure learning/self-report, French A2 self-report, 12 reviewed months and a preparing application state. Generated evaluator files and environment/test outputs are ignored; no locked directory exists.

No inference, Qwen/Ollama integration, API endpoints, PostgreSQL, UI, connectors, browser automation, scraping, voice, workflow runtime, NEXUS or deployment was introduced. The runtime generator performs no network calls and uses no real personal/job data.

This proves a controlled fixture environment, not ACTUAL behavior. Eight handcrafted cases have narrow language, evidence and industry coverage. Seed variations retain templates. Duplicate fingerprints cover normalized posting title/text; other shared prose depends on honest lineage declarations, and fingerprints miss semantic paraphrases. Synthetic reviewed support does not authenticate real documents. Experience/CV conventions do not assess unrestricted prose or employment history. Recruiter outcomes are scripted independently of fit and predict no hiring result.

The artifact writer is not a two-directory transaction; an interrupted write must be regenerated and verified. File separation and ignore rules are not access control or secure deletion. Future validation/locked construction, exposure controls and production mount enforcement remain required under the accepted evaluation strategy.

Phase 1 stops here. Phase 2 has not begun.
