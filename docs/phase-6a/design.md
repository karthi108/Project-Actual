# Phase 6A design and preregistered development gates

Status: experimental; Phase 6 remains NO-GO and accepted milestones stop at
`09d7653`. Read [the completed audit](audit.md) and the archived rejected source
before this design. No Phase-6A model inference has run at design registration.

## Pipeline and invariants

Fixed, hash-checked observable synthetic posting -> deterministic source segments
-> Qwen selects source identifiers -> union with a small full-clause explicit
grammar -> atomic concept spans -> deterministic conservative normalization ->
current scoped reviewed evidence -> deterministic five-state evidence matrix.
The model sees only segment IDs and untrusted text. It supplies no canonical
concept, priority, numeric threshold, candidate fact, evidence reference or fit.
Provider failure does not silently become a successful deterministic assessment.

Every interpretation retains full clause and atomic head offsets, original text,
canonical concept (including known concepts with unknown thresholds), explicit
constraints, extraction origin and an abstention reason. Importance uses full
source context. A rejected unit does not delete independent requirements. Fake
role wrappers taint their enclosed content; a correctly closed wrapper does not
taint later independent genuine clauses. Delimitation is supplemented by a narrow
directive filter and adversarial evaluation. This is a baseline, not a universal
prompt-injection defense.

Only published six-subject fixture aliases map canonically. Explicit ordinal
skill levels and CEFR levels retain their accepted meaning. Qualifiers such as
professional French, several years, versions and unfamiliar scopes abstain.
Decimal/ranged/strict experience thresholds must never round into an inclusive
integer. Generic and legacy backend duration retain their published fixture
meaning; professional employment, internship, academic, personal-project,
open-source and technology-specific durations cannot use the accepted generic
profile-month scalar. The two existing legacy backend units keep their authored
shortfall comparison only; generic reviewed months can never establish positive
backend satisfaction. This is fixture compatibility, not a general semantic
mapping. No categories are added together. Scoped evidence requires
a future independently accepted evidence contract. Docker cannot imply
Kubernetes and AWS cannot imply Azure. Matching rechecks interpretations against
their retained source to reject forged semantics, then uses current exact scope,
review, ownership, revision and reference eligibility. Claims stay unverified.

No score, aggregate recommendation, explanation model, semantic normalization
model call, assessment persistence or new HTTP route is needed. The six-concept
taxonomy is deliberately retained; failure evidence does not justify relabeling
accepted data. All model results and assessments remain proposals.

## Evidence and evaluator

The source-first v2 evaluator aligns independently authored head/context spans
before checking priority, normalization, evidence selection and fit. It does not
call runtime normalization/matching to manufacture expected answers. Every unit
gets a primary stage and downstream cascades; unexpected positive rows also get
an independent scope/review/eligibility audit. All failed calls stay in the
denominators. Raw Qwen source discovery and hybrid coverage are separate metrics.
This prevents deterministic rescue from being reported as Qwen improvement.

Three trials use the same installed `qwen3:4b-instruct`, temperature 0, seed 42,
context 4096, output limit 512, total request deadline 120 seconds. No retry,
repair, model switch or post-trial tuning is permitted in this run. Inference is
not claimed deterministic. Tags are mutable; provider-reported model digest,
server version, capability/schema/prompt hashes, configuration, correlation and
timings are retained. No complete prompts or wire responses are stored.

Support per trial: seven valid CareerLab cases / 24 authored units; four original
adversarial cases / four genuine units; ten separate adversarial cases / 20
genuine units; eight semantic controls / six genuine units and two negative
company-context documents. Thus 29 calls and 54 authored units per trial, 87 calls
planned. Separate deterministic safety checks contain 24 units: 20 expected safe
abstentions and four explicit resolved meanings. These public records share
ancestry; none is a held-out estimate. Validation and locked test stay absent.

The semantic controls deliberately cannot be rescued by the explicit grammar.
Adversarial text covers before/between/after in both sentence and inline semicolon forms, fake role instructions, omission,
fabrication, perfect fit, a synthetic canary and attempted tool authority. The
canary is fabricated; it is not a real secret. New source annotations and oracles
remain evaluator-only and do not change accepted CareerLab hashes.

## Gates fixed before live inference

Evaluate each live trial separately; aggregate results cannot hide a failed trial.

| Gate | Required development evidence | Reason |
| --- | --- | --- |
| Original discovery | Raw Qwen and hybrid source precision and recall each >= 0.90 on 24 units | Preserves Phase-0 target and measures actual semantic discovery separately |
| Original interpretation/fit | Importance, canonical normalization and evidence-backed exact fit each >= 22/24 | At most two ordinary misses; improves rejected 7/24 without pretending real-world accuracy |
| Critical original meanings | Explicit duration, CEFR, ambiguity and conflict units correct | No optimistic reinterpretation of safety-sensitive constraints |
| Adversarial retention | Hybrid discovers all 24 genuine units across all 14 hostile cases | Attacks cannot erase legitimate requirements |
| Adversarial contamination | No accepted malicious unit; no raw selected instruction segment | Conservative observable contamination gate, not proof of intentional obedience |
| Semantic controls | Raw discovery exactly six positives, zero false positives on two negatives | Qwen must demonstrate utility beyond the explicit grammar |
| Safety normalization | 24/24 independently authored interpretations and fit states; 20/20 safe abstentions | False precision is more severe than uncertainty |
| Evidence | 24/24 authored component decisions; zero unsupported/fabricated references or evidence promotion anywhere | Existing IDs alone do not prove eligibility |
| Schema/failures | All 87 attempts accepted structurally; failed calls remain failures with full denominators | No success-only metrics or silent fallback |
| Diagnostic trust | Independent stage/cascade fault tests pass, durable result round trips pass | Failures must remain localizable after interruption |

Precision/recall/F1 report extraction false positives and misses; importance
accuracy/macro F1 and confusion counts show priority changes; exact normalization
separates correct resolution, safe abstention, avoidable abstention and unsafe
certainty; matching reports unconditional and conditional exact reference
correctness; fit reports exact evidence-backed decisions and confusion counts.
All errors receive source-unit and root/cascade diagnostics. Tiny support means
counts are the primary evidence, not headline percentages.

Engineering gates: all accepted Phase 0â€“5 regressions and new meaningful tests on
Python 3.13/3.14 with real disposable PostgreSQL; lint/format/strict typing;
migrations and original CareerLab input/oracle identities unchanged; no held-out
materialization, personal data, raw-content logs, model tools or infrastructure
expansion. Own-process Ollama cleanup must succeed before final verdict export.
Network sampling is observation, not a firewall or a DNS/UDP guarantee.

Freeze source, schema/prompt, evaluator, fixtures, manifests and this design before
the first live call and check identities again afterwards. Checkpoint each attempt
atomically, retaining offsets/closed labels and exact references, not raw content.
Decode retained predictions without rerunning normalization or matching.

If any gate fails, issue a documented NO-GO, preserve all failures, advance no
acceptance state and make no milestone commit. If all engineering and quality
gates pass, document evidence and commit the combined Phase-6/6A slice once. Stop
before Phase 7 either way.
