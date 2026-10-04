# CareerLab methodology v0.1

Status: Phase-1 methodology. Read with the accepted [Phase-1 plan](../phase-0/phase-1-plan.md), [evaluation strategy](../phase-0/evaluation-strategy.md) and [CareerLab rubric](rubric.md). This document specifies gates; demonstrated results belong in the Phase-1 acceptance record.

## Purpose and bounds

CareerLab is an offline, explicitly synthetic career environment. It supplies reproducible observable inputs and separate evaluator annotations so later ACTUAL components can be checked against a known, bounded rubric.

Phase 1 proves fixture-schema/invariant enforcement, reproducible generation, separate input/label serialization and documented examples of evidence support, uncertainty and invalidity. It does not measure an ACTUAL application, extraction model, CV drafting system or workflow runtime. It does not establish employability, hiring probability, production readiness, preparation-time savings or generalization to real candidates and employers.

The accepted smallest slice is CAREER-DEV-001 and its unsafe-draft sibling, followed by eight public development scenarios. Validation and locked-test partitions remain unmaterialized in Phase 1. No locked test is frozen, inspected or used for acceptance, and no model benchmark is claimed.

## Design decisions resolved before generation

1. Coverage categories describe behavior; lineage groups describe leakage. They are separate dimensions. Future partitions should have comparable behavior coverage while keeping related source material in one partition.
2. Labels express the published support rubric, not what an employer would decide. Multiple CV choices and ambiguous requirement interpretations can be acceptable.
3. Observable evidence/status is necessary to assess support. Correct answers, expected rejection reasons, scenario category, deliberate-invalidity markers, canary values and future outcomes belong only to evaluator data.
4. Previously received recruiter messages can be observable history. A later recruiter/interview/rejection outcome is a scripted evaluator fixture. It is independently authored and is not derived from a fit score or CV recommendation.
5. A declared shortfall and reviewed support are different facts. Self-reported claims can expose a declared shortfall while leaving actual support unknown.
6. Intentionally inconsistent histories are ordinary-looking observable records with explicit evaluator rejection annotations. They must fail validation; an evaluator marker never makes an invalid ordinary record valid.

## Minimum data contracts and file responsibilities

The implementation uses small, closed fixture contracts rather than the production domain models planned for Phase 2. Required concepts are:

| Contract | Observable content |
| --- | --- |
| Scenario envelope | Schema version, synthetic marker, stable neutral identity and the contained records |
| Company/job | Fabricated company context, stable opportunity identity, original job text and source metadata |
| Candidate/profile | Specific assertions, status and evidence references; no real personal information |
| Evidence | Bounded subject/value support, source excerpt, review method/reviewer and explicit dates |
| CV/draft | Structured assertion IDs and supporting evidence references; proposed additions remain proposals |
| Application/message | Stable application identity, reported states, occurrence/recording times and already-received synthetic correspondence |

Evaluator contracts additionally carry authored requirement annotations, support decisions and rationales, acceptable CV alternatives, blocked draft additions, scripted future outcomes, secret-canary answer and expected invalid-record reasons. These are separate types and files. Requirement annotations are evaluator-only; the observable input retains the original job text rather than pre-extracted answers.

Implementation responsibilities, with final module names recorded in the usage documentation:

| Boundary | Responsibility |
| --- | --- |
| Fixture contracts | Strict shape/type/value validation, synthetic markers, IDs, references and bounded payloads |
| Observable generator | Seeded construction of input records without importing evaluator answers |
| Evaluator annotations | Separately authored expected decisions under [the rubric](rubric.md) |
| Integrity validation | Referential, evidence-scope, date/history and input/label consistency checks |
| Packaging | Separate canonical input and label files plus reproducibility manifests |
| Split integrity | Validate lineage and duplicate isolation using public synthetic test partitions |
| Tests | Exercise rejection, separation, integrity, variation and determinism |

This division establishes a disciplined evaluator boundary. It does not make files inaccessible to the machine owner, and it is not a production sandbox.

## Generation and annotation method

Before expanding the worked example, specify each scenario's observable facts, requirement wording, coverage category, lineage and annotation rationale. Generate only relationships justified by those facts. Authored annotations are reviewed against the published rubric independently of input generation; they are not presented as an independent employer judgment.

Use explicit synthetic names, dates, source excerpts and content. Preserve the CAREER-DEV-001 fixture facts from the accepted contract. Later seeded variations change intended observable details while preserving each case's semantic relationships and expected annotations. Changing only IDs or seed metadata is insufficient evidence of meaningful variation.

Reproducibility depends on seed, generator/schema/rubric versions, fixed base dates, stable ordering and serialization. Use a local seeded random source rather than global randomness, current time, network inputs or host-specific paths. Serialize canonical UTF-8 JSON with a defined key ordering, separators and newline policy. No real profile or job data is used.

Generation and annotation are different responsibilities. A future assessor must not be benchmarked against labels computed by calling that same assessor. Cross-checking an authored label against observable evidence is an integrity check, not a model-quality measurement.

## Development, validation and locked-test lifecycle

### Phase-1 development

All eight generated scenarios are public development cases, deliberately inspectable by developers. They share candidate, evidence, CV and template ancestry and form one connected leakage component. They cannot be divided into independent validation or locked-test partitions; those require fresh independently authored source lineages. This permits debugging and worked-example review. Inspecting them does not establish held-out evaluation. Tests exercise partition-isolation rules with their own public synthetic records; those records are test fixtures, not a validation or locked acceptance dataset.

Coverage includes explicit gaps, supported CV alternatives, unsafe additions, contradictory/withdrawn evidence, self-report-only support, ambiguous priority, malicious instructions/canary requests and duplicate/inconsistent application history. Preserve uncertain observations within the bounded history fixtures without introducing an external-write capability.

### Future partition construction

Set rubric, intended measurements, category coverage and acceptance thresholds before generating/finalizing evaluation partitions. Create independent scenario instances and source-writing templates for validation and locked testing. Curate the held-out language for plausibility; replacing names or shifting dates in a public template does not create an independent case.

Construct connected components over every shared company, candidate, evidence, CV, application and text-template lineage. If records share any lineage key, including through a chain of other records, assign the entire component to one partition. Candidate/CV derivatives and paraphrases retain their original lineage. A claimed group ID, identifier rename or mask cannot erase ancestry.

Also compute duplicate fingerprints from normalized source content. Normalize superficial variation consistently, then reject duplicates that cross partitions. Computed fingerprints supplement lineage tracking: they do not prove the absence of semantic paraphrases. Human source/template review is needed before a future freeze.

Balance comparable coverage categories across development, validation and locked testing while holding source-lineage components apart. Do not withhold all ambiguity, attack or invalid-history cases into only one partition. Document any intentional distribution shift explicitly; do not mistake it for ordinary generalization.

Validation supports choosing prompts, models or rubric clarifications. Every such choice precedes locked acceptance. Locked inputs and labels remain outside Git and ordinary runtime/development mounts; only versioned manifests and exposure records are retained in the source project. Development commands must not automatically generate or read locked cases.

### Future freeze and exposure

Freeze locked cases only after the development rubric and thresholds settle. Record source/generator/schema/rubric hashes, seed policy, lineage assignments, input/label hashes, coverage counts and freeze date. Do not inspect or tune against individual locked cases after freezing. An acceptance report includes aggregate outcomes and its dataset/version identity, including failures.

If a locked case is exposed for diagnosis, record who/when/why and the affected case/hash in an exposure log, retire it into development and establish a fresh frozen acceptance set before retuning or claiming an uncontaminated result. Hashes establish dataset identity; they do not establish validity or lack of contamination.

## Ground-truth isolation

Observable packaging contains only the input contract. Evaluator files and schema are loaded separately by integrity checks/evaluators, never appended to future application/model context. Leakage-group/category metadata must remain outside ordinary input records. Historical source facts may be observable; expected interpretations and future responses may not.

The actual synthetic canary value belongs only in evaluator data. Malicious job text requests disclosure without copying the answer. Separation tests check exact sentinel values as well as evaluator-only fields and annotations. Ordinary serialization must not accidentally serialize an evaluator object or a combined object graph.

Each deliberately invalid case carries a separate expected-rejection annotation. Keep that marker out of the observable record, so rejection tests depend on the malformed content rather than a hint. Structural validation and semantic validation are distinct: a well-formed reference may still have the wrong scope or insufficient reviewed support.

## Acceptance gates

Acceptance requires demonstrated checks, with commands and results recorded separately:

1. Every generated ordinary record passes the explicit schema and applicable invariants; intentionally invalid records fail for their documented reason.
2. Same seed/config/version yields byte-identical canonical inputs, labels and stable manifests; another seed alters the intended observable variation while preserving valid relationships.
3. Every record is explicitly synthetic and uses stable, unique scenario-local identities. References resolve without crossing scenario boundaries.
4. Profile/CV/draft support has reviewed status and sufficient scope where required; unsupported additions remain blocked. Unknowns, conflicts and acceptable alternatives match the rubric.
5. Application/message histories preserve causal occurrence order and explicit recording time; delayed recording does not invent causal order. Invalid history is rejected.
6. Observable output excludes labels, expected outcomes, category/invalidity hints and canary answers. Future recruiter outcomes remain evaluator-only.
7. Split tests reject direct/transitive shared lineage and normalized source duplicates across public synthetic partitions.
8. Coverage and authored ground truth receive independent review; all relevant integrity, rejection, separation and determinism tests pass.
9. Manifests retain dataset version, seed/config, generator/schema/rubric identity and input/label hashes. Exact checks and remaining limits are documented.
10. No model, network, DB, API, UI, connector, browser, voice, workflow or deployment capability is introduced. Commit only after these gates pass; stop before Phase 2.

## Known limitations

Eight handcrafted cases provide useful controls and teaching examples, not a representative career population. Writing styles, industries, evidence types and timelines are narrow. Deterministic variations can preserve recognizable templates, and normalization misses many paraphrases. Generator correctness and reviewed annotations can still share author assumptions; independent review reduces this risk without removing it.

Evidence review within a synthetic fixture means the rubric's support condition is satisfied. It does not authenticate real documents or certify proficiency. Scripted recruiter outcomes have no causal or statistical relationship to actual hiring. There is no measured model performance, held-out generalization, calibration or human-usability result in this phase.
