# CareerLab Phase 1: use and understand the fixtures

CareerLab is a controlled synthetic environment for future ACTUAL evaluation. It currently supplies eight **public development** cases, strict fixture contracts and integrity checks. It supplies no ACTUAL application, model inference, hiring prediction or held-out benchmark.

The user accepted Phase 0 at `4e06cc6` and authorized this bounded Phase 1. Read the [methodology](methodology.md), [support rubric](rubric.md) and [acceptance evidence](acceptance-review.md). Phase 2 requires a new user request.

## Run from the repository root

Python 3.13 or 3.14 and uv are required. Runtime fixture generation uses the Python standard library; the locked development tools are pytest 9.1.1, Ruff 0.16.10 and mypy 2.4.0. Installation can fetch packages; fixture generation and verification make no network requests.

```powershell
uv sync --locked
uv run --locked careerlab generate
uv run --locked careerlab verify
uv run --locked pytest -q --tb=short
uv run --locked ruff check src tests
uv run --locked ruff format --check src tests
uv run --locked mypy
```

After installation, `uv run --offline --locked careerlab verify` verifies without fetching packages. The CLI accepts only `generate` and `verify`; it has no split-generation option, server or runtime service. It prints the dataset hash and partition status, without printing evaluator answers.

Tests use `.pytest-tmp-careerlab` within this project because the shared Windows temporary directory had incompatible permissions. Pytest replaces its own base temporary directory on each run. Keep that directory dedicated to tests; use `--basetemp=.pytest-tmp-careerlab-313` for a separate interpreter run. These directories are ignored by Git.

Generation accepts an integer seed in `[0, 2**63)`, default `20261004`:

```powershell
uv run --locked careerlab generate --seed 17 --inputs local-data/seed17/inputs --evaluator local-data/seed17/evaluator --manifest local-data/seed17/manifest.json
uv run --locked careerlab verify --inputs local-data/seed17/inputs --evaluator local-data/seed17/evaluator --manifest local-data/seed17/manifest.json
```

Verification takes the seed from the manifest. Use separate destinations to retain multiple versions. Generation replaces the expected eight files at the specified destinations, rejects unexpected directory contents and never deletes unrelated files. It rejects overlapping roots, manifests inside record directories, `locked_test` paths and symlink/junction/reparse aliases. The writer is not transactional across both directories: after an interruption, regenerate and verify before using the data.

## Artifacts and trust boundaries

| Location | Contents and intended reader |
| --- | --- |
| `datasets/development/inputs/CAREER-DEV-001.json` through `008.json` | Public observable records for a future component: source job prose, synthetic profile/evidence, CVs/draft proposals and observed application/messages |
| `datasets/ground_truth/development/CAREER-DEV-001.json` through `008.json` | Evaluator annotations, expected blocks/errors, acceptable CVs, secret canary and scripted future outcomes; ignored by Git |
| `datasets/manifests/careerlab-dev-v1.json` | Dataset/schema/generator/rubric identity, seed, source and record hashes, split membership and lineage/category metadata; author/evaluator only |

Give a future component only the observable input directory, through the closed input loader. A manifest contains category/lineage metadata and is not application input. Evaluator annotations are reproducible from public development authoring code in this repository; ignoring generated labels does not make public development answers secret from a developer. This separation prevents accidental context contamination and establishes the intended future mount boundary. It is not an operating-system sandbox.

There is no validation or locked-test dataset. All eight cases share candidate/evidence/CV/template ancestry and form one development component. Future held-out data needs independently authored lineages, comparable behavior coverage, separate mounts and a recorded freeze/exposure policy. See [the lifecycle](methodology.md#development-validation-and-locked-test-lifecycle). No individual frozen test case was generated, inspected or tuned against in Phase 1.

## Important files

| File | What to understand |
| --- | --- |
| `src/actual/careerlab/contracts.py` | Frozen, closed input and oracle records; explicit synthetic markers, typed units/statuses and reference fields. These are fixture schemas, not Phase-2 production models. |
| `src/actual/careerlab/codec.py` | Strict recursive decoding and canonical JSON. Missing/extra fields, wrong literal types and duplicate JSON keys are rejected. Observable and oracle serializers accept their own exact types; a combined pair cannot be serialized as input. |
| `src/actual/careerlab/generator.py` | Authored input facts plus local seeded variation of context, dates and names. Explicit clocks/order avoid host-time and network dependence. Input construction does not use oracle assessments. |
| `src/actual/careerlab/annotations.py` | Separately authored public development answers, rationales and honest lineage assignments. This is authoring/evaluator code, not an assessor for future application behavior. |
| `src/actual/careerlab/validation.py` | Shape, identity, evidence scope/provenance, timeline and annotation invariants. Pair validation checks expected rejection codes; it never turns an invalid ordinary record into a valid one. |
| `src/actual/careerlab/splits.py` | Transitive lineage-component isolation and duplicate detection over normalized posting title/text. Other shared prose relies on truthful ancestry metadata and later human review. |
| `src/actual/careerlab/dataset.py` | Separate artifact roots, pre-write integrity gate, canonical manifests, source/record hashes and regeneration verification. Only public development packaging is supported. |
| `src/actual/careerlab/__main__.py` | Small local generate/verify CLI. |
| `tests/careerlab/test_codec.py` | Strict contracts, recursive synthetic markers, serializers and malformed shape/type rejection. |
| `tests/careerlab/test_validation.py` | Scoped evidence, contradictions/unknowns, unsafe additions, CV alternatives, dates, aliases and invalid histories. |
| `tests/careerlab/test_splits.py` | Direct/transitive lineage and normalized source duplicate rejection with handcrafted public test metadata. |
| `tests/careerlab/test_dataset.py` | Determinism/variation, separation, hashes, tampering, path boundaries and fresh-process CLI checks. |
| `pyproject.toml` and `uv.lock` | Supported interpreter range, pinned tools, checks and reproducible dependency resolution. |

## Cases and deliberate invalidity

This author-facing inventory describes the public examples. Categories and expected answers are absent from observable record fields and filenames; neutral IDs do not make public development examples held out.

| Case | Controlled behavior |
| --- | --- |
| `CAREER-DEV-001` | Worked backend example: reviewed Python/FastAPI/integration support, Azure learning, French A2 self-report and one reviewed year against higher requirements |
| `CAREER-DEV-002` | Sibling with unsupported French B2 and five-year draft additions |
| `CAREER-DEV-003` | Equally relevant safe CV alternatives; observed interview and cancellation/rejection history |
| `CAREER-DEV-004` | Reviewed contradictory integration evidence and a proposal that must remain blocked |
| `CAREER-DEV-005` | Candidate support awaiting review, self-report and withdrawn assertions |
| `CAREER-DEV-006` | Ambiguous priority, acknowledgement/follow-up history and a separately scripted future outcome |
| `CAREER-DEV-007` | Hostile job instructions requesting fabricated facts and a canary whose answer exists only in evaluator data |
| `CAREER-DEV-008` | Aliased identical opportunity and an application that skips from preparing to interview |

Cases 001–007 pass ordinary input invariants. Case 008 is structurally well formed but fails the fixture transition rule with exactly `application_transition`; the oracle records that expected rejection. The package gate succeeds only when actual violations match that authored expectation and the annotations themselves remain valid.

The timeline policy is intentionally small: preparing → ready_for_review → reviewed → applied → interview → offer, with specified returns to preparing before application and closure branches; closed is terminal. Received messages must follow the relevant reported application state. Applied is a synthetic manual report, not proof of delivery. This fixture checker implements no workflow engine or external effect.

## Dataset identity and limitations

The manifest hashes canonical UTF-8 JSON: sorted keys, compact separators and one trailing LF. Its dataset SHA-256 is the hash of the manifest body before adding `dataset_sha256`. Record hashes cover the exact input/oracle bytes. Source hashes cover every CareerLab module, methodology, rubric, project configuration and lockfile. A source or rubric change requires regeneration and verification; seed alone is not an adequate identity.

The manifest intentionally excludes the acceptance document and itself to avoid circular hashes. Git records tests and documentation alongside the fixture source. Keep the source commit and manifest together for reproduction.

Eight authored examples do not represent the labor market. Seed variations preserve templates. Normalized duplicate detection cannot prove semantic independence. Labels encode bounded fixture conventions, including ordinal skill/language values, reviewed scalar experience and a simple CV relevance rule. They do not authenticate real evidence, assess unrestricted prose or predict recruiter decisions. Refer to [known limitations](methodology.md#known-limitations); no model performance or real-world generalization is claimed.
