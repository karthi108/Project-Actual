# Evaluation strategy v0.1

Status: planned methodology and targets. No dataset, test suite or model benchmark has been run.

## Separate software guarantees from model quality

Deterministic contracts test identifiers, owners, state transitions, evidence support and rejection behavior. Model evaluation measures extraction and semantic suggestions on labeled cases. Human product evaluation measures usability and actual preparation work. A good average model score cannot override a failed authorization, privacy or unsupported-claim gate.

Fit labels express a documented CareerLab rubric, not objective employability. Ambiguous/negotiable requirements permit multiple justified answers or escalation. Record label rationale and reviewer adjudication; do not force confident binary labels onto uncertain inputs.

## Dataset lifecycle and ground truth

Phase 1 starts with a small public development world and separable evaluator labels. No production model, schema implementation or runtime is necessary to generate it.

Later create `development`, `validation` and `locked_test` partitions. Split by scenario families/company/template groups to reduce near-duplicate leakage, not just shuffled rows. Record generator version, seed policy, scenario/rubric version, partition assignment and input/label hashes. A hash establishes identity, not validity.

Development labels are inspectable for debugging. Validation supports tuning choices. Freeze locked-test inputs/labels only after the development rubric and acceptance thresholds are settled and before running acceptance. Application/model inputs never include label files; the evaluator loads them separately. Locked cases are withheld from ordinary development and excluded from Git/runtime mounts, with versioned manifests retained.

The machine owner can inspect local files; 'hidden' is a disciplined evaluation boundary, not protection from a determined developer. If a locked case is inspected to diagnose a failure, record that exposure and retire it into development; establish a fresh frozen acceptance set before retuning and reporting an uncontaminated result.

## Coverage

Required families include supported fit, explicit gaps, ambiguous requirements, self-reports, conflicting/withdrawn evidence, fabricated claims, malicious job instructions, duplicate opportunities, inconsistent state transitions and uncertain outcomes. Model/runtime/network adversarial cases expand with those capabilities. Synthetic examples avoid real personal or proprietary data.

## Measures and proposed release gates

| Measure | Method and reporting | Gate |
| --- | --- | --- |
| Requirement extraction | Compare labeled requirement units and essential/preferred status; report counts and precision/recall by category | Initial target: precision and recall each at least 0.90; finalize before freezing acceptance set |
| Uncertainty/escalation | Measure coverage, abstentions and incorrect confident decisions | No silent reinterpretation of explicit critical requirements; record unresolved cases |
| Unsupported factual additions | Evaluate factual units against reviewed support and semantic labels | Zero observed unsupported additions in the acceptance set; any occurrence blocks affected draft capability |
| Typed proposal validity | Raw schema-valid result rate, validation failures, bounded repair attempts | Invalid output is never accepted downstream; report raw model failure rate separately |
| Invariants/privacy | Deliberate invalid-owner, no-authority, malformed-input and boundary tests | Every applicable deterministic safety test passes |
| CV recommendation | Acceptable alternatives under the rubric with evidence/rationale | Report disagreement and rationale quality; no false promise of one perfect CV |
| Local usability | Owner completes intake/review/draft/manual-tracking flow, including model outage | Journey completes with saved work recoverable and manual fallback |
| Performance | Measured p50/p95, sample size, hardware, model size/config, cold/warm state | Set a usable latency budget after Phase-5 measurements; none is claimed now |
| Impact | Recorded active human time, total time, accepted edits, rework and errors | Compare measured manual/assisted cases; no savings claim before measurement |

Targets are proposed product criteria, not benchmark results. A zero failure count on a finite set does not prove failures are impossible. Report case count, rubric/dataset hashes, versions, model/config/prompt versions, failures, seeds and timing conditions with every result. Do not hide errors in successful-case-only averages.

## Phase-proportional checks

The master specification's invariants have explicit responsible boundaries and verification triggers:

| Invariant | Responsible boundary | Evidence when introduced |
| --- | --- | --- |
| 1. Model output is a proposal | ModelGateway/intelligence | Malformed/injected proposals rejected in Phase 5-6 |
| 2. AI cannot grant authority | Authorization/execution | Model/client authority fields rejected before effects |
| 3. External effects need authorization | Runtime/tool gateway | Denied/revoked action cannot dispatch before any write |
| 4. High-risk action requires review | Local policy/approval | Missing approval blocks all initially enabled external writes |
| 5. Approval binds reviewed content/version | Approval/execution | Edited content/destination/version invalidates approval |
| 6. Unsupported claims do not enter materials | Evidence/career drafting | Unreviewed or insufficient support blocks factual rendering |
| 7. Credentials stay out of model context | Model adapter/privacy boundary | Synthetic secret canary and context/log inspection |
| 8. Duplicate event does not cause duplicate effect | Persistence/runtime/adapters | Duplicate/concurrent delivery and acknowledgement-loss cases |
| 9. Consequential actions are auditable | Execution/persistence | Outcome and authority records remain linked through failure/recovery |
| 10. Automation is measurable | Evaluation/event instrumentation | Recorded baseline/assisted outcomes before savings claims |
| 11. Dogfooding informs regressions | Feature owner/test suite | Reproducible practical bugs acquire regression coverage |
| 12. Analyze processes, not employee worth | Product/capture boundary | Review metrics and capture features against excluded ranking/surveillance |

An absent capability has no claim of passing its later checks. Each implementing slice must record actual evidence and keep affected behavior disabled when its gate fails.

Phase 0: review document coverage, consistency, local links and source preservation. No application tests apply.

Phase 1: repeatable synthetic inputs/labels, separation, rubric consistency and adversarial scenarios. Phase 2: schema/state/provenance checks. Phase 3: transactions, constraints, migrations up/down on disposable data, and deletion behavior. Phase 4: authenticated scoped API integration. Phase 5-7: structured inference/errors and evidence-backed assessments. Phase 8-9: browser workflow, exact draft revision review and unsupported-content checks.

Later runtime checks include crash recovery, lease expiry/concurrent claims and acknowledgement loss. Before external writes, test stable business intent across workflow upgrades, replayed/stale/revoked approval and changed artifacts/destination. Replay/shadow must demonstrate inability to dispatch effects before activation. Fault injection and hardening expand existing controls; they do not introduce them for the first time.

Dogfooding bugs become small reproducible regressions when practical. Passing synthetic evaluations, happy-path demonstrations or a production-like folder tree do not establish production readiness.
