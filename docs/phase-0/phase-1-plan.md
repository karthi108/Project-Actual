# Phase 1 plan: CareerLab

Status: next implementation plan only. This session does not begin Phase 1.

## Goal and smallest slice

Build an offline, deterministic synthetic career world. Given a seed and generator/rubric version, produce the same scenario inputs and separate expected outcomes. The evaluator sees labels; a future application/model sees only scenario inputs. No network, personal profile, database, HTTP server, LLM or frontend is required.

The first slice is CAREER-DEV-001 plus a negative sibling with unsafe draft claims. Expand to eight public development scenarios only after repeatability and separation work. All are synthetic; names and skill claims do not describe the real user.

## Proposed files and responsibilities

| File or directory | Why it exists |
| --- | --- |
| `pyproject.toml` | Small Python project, locked/compatible dependencies and relevant checks |
| `src/actual/careerlab/` | Fixture representations, seeded generation, scenario packaging and evaluator-only labels |
| `tests/careerlab/` | Repeatability, consistency, separation and edge-case checks |
| `docs/phase-1/` | Rubric, generation commands and demonstrated results, created as needed |

Prefer standard-library fixture types initially; formal production Pydantic schemas arrive in Phase 2. Separate input and expected-result representations and serializers. Do not build an evaluation framework, plugin system or final domain package hierarchy yet.

## Scenario coverage

1. Backend support with explicit Azure/French/experience gaps (public worked example).
2. Suitable CV alternatives under a documented rubric.
3. Unsupported language/experience additions proposed in a draft.
4. Contradictory evidence requiring escalation.
5. Self-reported skills without reviewed support.
6. Ambiguous essential/preferred wording and justified unknowns.
7. Job text containing instructions to fabricate skills or disclose a synthetic secret canary.
8. Duplicate opportunity identity and application-state inconsistency.

Include companies, CV assertion/evidence links, application histories and synthetic recruiter/interview/rejection messages as fixtures, not working connectors. Restrict generation to plausible timeline/label combinations; intentionally invalid cases are marked and contain the expected rejection reason. A seed is only one reproducibility input: stable ordering, explicit dates and generator version also matter.

## Implementation steps

1. Confirm Phase-0 contract has no unresolved blocking contradiction. Explain fixture input versus evaluator label and the rubric before coding.
2. Check Python compatibility and choose/lock the minimal project/test tools. Do not assume the host interpreter version determines the eventual production version.
3. Implement the first public scenario and a separately serialized expected-result record. No locked-test set yet.
4. Add seeded packaging, manifests/hashes and determinism checks. No labels or expected outputs in the input representation.
5. Expand the eight scenario families and add consistency checks for evidence, dates, IDs, expected claim blocks and histories.
6. Run relevant tests/static checks, inspect representative synthetic output and document actual commands/results and limitations.
7. Make one focused local commit after review; stop at Phase-1 acceptance before starting core production contracts.

## Phase-1 acceptance

- Same seed/config/version produces byte-identical canonical scenario inputs and label outputs.
- Changing scenario seed/config changes the intended variation while preserving valid relationships.
- Every record has an explicit synthetic marker and stable identity within the scenario.
- Ordinary input serialization excludes evaluator-only labels, expected results and secret canary answers.
- Expected outcomes follow the documented rubric, including alternatives, unknowns and rejection reasons.
- Evidence references resolve within the scenario; unsupported draft claims remain negative cases.
- Application/message timelines are internally consistent except in explicitly marked invalid cases.
- Tests include an intentional malformed fixture and prove the consistency check rejects it.
- No real user data, network calls, DB/API/model/UI dependencies or empty future scaffolds appear.
- Commands, passing/failing outcomes, generator/rubric hashes and remaining limits are recorded.

Hidden ground truth here means a separate evaluator boundary, not secrecy from the developer of public development cases. Validation and locked-test partitions are created/frozen later under [the evaluation strategy](evaluation-strategy.md).
