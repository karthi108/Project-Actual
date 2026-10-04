# Phase 2 design: used Core Contracts

Status: implementation design under the user's Phase-2 request. Phase 0 was accepted at `4e06cc6` and Phase 1 at `5b6116a`. This document defines responsibilities and acceptance methodology; passing results and the final source commit belong in the Phase-2 acceptance record.

The binding references are [the engineering contract](../phase-0/engineering-contract.md), [data and workflow principles](../phase-0/data-and-workflows.md), [architecture](../phase-0/architecture.md) and [evaluation strategy](../phase-0/evaluation-strategy.md). [CareerLab's rubric](../phase-1/rubric.md) remains an unchanged development-fixture convention.

## Problem, scope and smallest solution

CareerLab demonstrates controlled synthetic facts using fixture types. ACTUAL now needs reusable domain boundaries that reject malformed data, inconsistent state, foreign/stale references and unsupported structured claims before persistence or an API is introduced.

The solution is immutable Pydantic contracts plus pure validators for the records used by the career slice. A related-record snapshot checks what an individual record cannot establish alone. A compatibility adapter exercises those contracts against observable CareerLab inputs without importing evaluator answers.

Phase 2 implements identifiers, typed business/evidence/claim references, scoped profile evidence, job/requirement/material/application records, the six first Work Events and minimal review/effect primitives. It does not implement persistence, transactions, authentication, authorization, API endpoints, inference, document rendering, external writes or a workflow runtime. No Phase-3 work or user acceptance is inferred from schema tests.

## File responsibilities

| File | Responsibility and boundary |
| --- | --- |
| `src/actual/core/primitives.py` | Closed immutable contract base; kind-prefixed opaque IDs; bounded text, revisions and digests; UTC instants; strict JSON loading and canonical serialization |
| `src/actual/core/references.py` | `BusinessObjectRef`, `EvidenceRef` and `ClaimRef` bind workspace, classification, typed identity, revision and content digest; profile-specific refs also identify their profile |
| `src/actual/core/workflow.py` | `ContentReview` binds an exact revision/digest and reviewer; `EffectKind` supplies the accepted three classification values without an executor or permission mechanism |
| `src/actual/profile/contracts.py` | Structured assertions, source/review provenance, current evidence status, claims, related profile validation and the bounded `supports_assertion` predicate |
| `src/actual/career/jobs.py` | Companies, original job source revisions, separate job decision and proposed requirement interpretations with source span/digest and optional exact-content review |
| `src/actual/career/materials.py` | Evidence-linked CV variants and draft proposals; exact-content reviews do not authorize delivery or certify unrestricted prose |
| `src/actual/career/applications.py` | Seven reported lifecycle states, occurrence/recording history and a narrowly explicit external-manual tracking exception |
| `src/actual/career/snapshot.py` | Resolve current related records; enforce workspace/profile scope, classification, source spans, aliases, exact refs and causal support/review timelines |
| `src/actual/core/events.py` | Shared `EventHeader` metadata and chronology/workspace/classification/reference-uniqueness checks; no career import, activity or payload |
| `src/actual/career/events.py` | Career `WorkEvent` extends the shared header with six closed observation payloads, domain reference checks, current catalog resolution and pure source-redelivery classification |
| `src/actual/careerlab_bridge.py` | Accept only observable CareerLab input; map stable synthetic identities and recorded facts into a `CareerSnapshot`; never load an oracle or produce extraction answers |
| `tests/core/` | Boundary, provenance, career-state, event and observable-compatibility checks using public synthetic data |
| `src/actual/careerlab/`, `tests/careerlab/` | Accepted Phase-1 world and checks, preserved as the compatibility baseline |

Pydantic is the one new runtime dependency justified by the accepted Phase-2 architecture. Its exact version is locked in `pyproject.toml`/`uv.lock`; compatibility must be checked on the project's supported Python 3.13 and 3.14 branches. No framework or service is required to exercise these contracts.

## Contract and reference invariants

Every serialized nested contract declares `actual-core-v1`. Unknown/missing wire versions, duplicate JSON keys and unknown fields fail closed. Python construction can use declared schema defaults; wire loading requires explicit versions. Booleans cannot stand in for numeric levels/revisions, and string coercion cannot stand in for typed boundary data. Strings and collections have explicit bounds; the wire loader and canonical serializer enforce a 2,000,000-byte limit.

Records are frozen and replacement snapshots are revalidated. Unchecked `Contract.model_construct` and validation options that disable strict/closed fields are rejected. These are data-boundary controls in trusted Python code, not protection from a developer modifying the implementation or host memory.

IDs contain a kind prefix and opaque 32-hex identity. A job ID cannot silently become a CV ID. References bind an exact revision and digest; having a syntactically valid reference alone proves neither existence nor support. `Profile`, `CareerSnapshot` and event catalog checks resolve references against supplied current records. A workspace/actor ID is attribution data: authentication and server-derived ownership remain later responsibilities.

Evidence and claim records have two deliberately different digest boundaries. Their own `content_digest` identifies the source/assertion content being reviewed and excludes the record's review and status. A claim's review also binds its revision; evidence review binds its retained source content. Their `snapshot_digest` covers the complete current record, including review, status, identity and revision. `evidence_ref` and `claim_ref` store this snapshot digest in the reference field named `content_digest`, and profile/career resolution compares that full dependency identity. Changing a review or withdrawing support therefore invalidates downstream references even if the assertion text and revision remain the same. The two digests cannot be substituted for each other.

Draft and requirement own-review digests exclude their own `review` field to avoid a circular binding; they include their revision and the content/dependencies being reviewed. Other whole-record digests identify their complete serialized records. Generic business-object event catalogs are explicitly supplied by the caller: Phase 2 does not provide a universal catalog builder or infer which domain digest the catalog should use.

Input instants require an explicit timezone and normalize to UTC; serialization uses a fixed UTC representation. Recording cannot precede occurrence. Delayed recording is allowed, and causal order follows occurrence rather than ingestion order. Related facts/reviews cannot lie after the snapshot time. Canonical UTF-8 JSON uses sorted keys, compact separators and one LF; hashes establish content identity rather than authenticity.

Classification permits `synthetic`, `personal` and `sensitive`; `secret` is excluded. Synthetic and real-classified records cannot mix in a profile/snapshot or event reference set, and a parent cannot understate sensitive child/reference content. Matching a reference against its current catalog also checks its classification, so relabeling a sensitive reference as personal cannot pass resolution. This type policy does not detect every secret embedded in free text or implement retention, deletion or access control. Phase-2 tracked fixtures/tests contain fabricated data, including the cases exercising real-data classification tags.

## Assertions, provenance and bounded support

Assertions distinguish skill, language and experience subjects with their corresponding level/month units. Numeric bounds retain the current bounded vocabulary; these ordinals do not measure universal competence. Experience is a reviewed scalar, not tenure derived by adding projects or dates.

Claim statuses retain `self_reported`, `candidate_support`, `reviewed_supported`, `contradicted` and `withdrawn`. Evidence has active/withdrawn status plus positive/contrary relation and explicit source identity. Reviews distinguish human confirmation, source review, independent verification and synthetic review. Independent verification requires a distinct source reference, but a correctly filled field still cannot authenticate that real-world source. Human confirmation alone does not qualify support. AI/user reports cannot become sufficient support merely by acquiring source-review labels.

Reviewed-supported claims require their own exact revision/content review and sufficient current scoped reviewed evidence. References must resolve inside the owning profile and cover the same assertion kind/subject/unit and sufficient value. Contrary qualifying evidence is considered across the profile; selecting only favorable references cannot hide it. Source collection precedes review, and claim review cannot precede its qualifying supporting review.

`supports_assertion` checks these structured units and current references. It does not judge the semantics of arbitrary claim, CV or draft text. Proposed drafts can contain unsupported units for inspection/rejection. Within `CareerSnapshot`, an accepted structured draft requires sufficient current support that was available by its review time. Changing reviewed content breaks its own review binding; changing a dependency's revision, content, review or status breaks the corresponding snapshot reference. These records must be reconciled, and affected content must be reviewed again where its binding has changed.

CV records preserve assertion provenance but their shape alone does not make every included claim safe or establish a recommendation. Requirement records preserve a source span, priority, origin and optional review; valid spans do not prove correct interpretation. The snapshot checks exact current job revision/digest, matching source text and one normalized subject per canonical opportunity. Aliases with conflicting source text are rejected.

## Application history and review are separate

The lifecycle is `preparing`, `ready_for_review`, `reviewed`, `applied`, `interview`, `offer`, `closed`. Histories start at preparing, preserve strictly increasing occurrences and match their final state; closed is terminal. Job decision remains a separate field.

Ordinary internal progress follows the accepted fixture transition map, including returns to preparing before application and closure branches. To track an application submitted manually outside ACTUAL, `preparing` or `ready_for_review` may transition directly to `applied` only with `basis=user_reported` and `external_manual=true`. This records what the user reports without inventing an internal review. Synthetic observations cannot use that exception.

The historical lifecycle value `reviewed` does not prove a particular draft's current approval. Applications preserve reported history; exact artifact review belongs to the draft/revision contract. Applied status never establishes independently verified delivery, authority to send or completion of an automated effect.

## Work Events and minimal workflow primitives

Shared `EventHeader` contains only attribution, source, time, reference and privacy metadata. It is not a complete semantic event and cannot substitute for a `WorkEvent`. Core has no import of Career payloads or application transitions. Career owns its concrete discriminated payload union and validators in `actual.career.events`; this preserves the accepted boundary without a generic registry, plugin framework or executor.

The six payloads are discriminated by activity:

| Activity | Allowed metadata |
| --- | --- |
| `job_added` | Current job reference |
| `requirements_reviewed` | Job and requirement references; reviewer and review time |
| `fit_assessment_recorded` | Job/profile/assessment references and bounded supported/partial/gap/unknown/conflict counts |
| `cv_recommended` | Job/profile references and CV choices |
| `draft_reviewed` | Draft reference, exact revision/digest through that ref, decision, reviewer and review time |
| `application_status_recorded` | Application reference, previous/current reported state and explicit observation basis/manual flag |

The envelope binds event/workspace/actor identities, occurrence/recording times, registered source, classification, source-event/correlation identities and evidence references. Its activity must agree with its payload. Business-object references must be exactly the payload's deduplicated set; refs cannot cross workspace, and profile-bearing evidence must match the named profile. Event classification must cover every referenced object's classification without mixing synthetic and real data. Reviewed events attribute the same reviewer as actor and cannot report a review from after occurrence.

Nonzero supported/partial/gap/conflict assessment counts require evidence refs. Unknown-only or empty assessments may have none; absence of evidence must remain representable. Accepted draft-review events require refs, while rejected drafts can record lack of support. The events carry no job/CV prose, prompts, arbitrary properties or authority flags. Counts are category metadata, not hiring probabilities or a numeric fit verdict. Full assessment behavior remains later work.

`validate_references` compares an event with a supplied current owner-scoped reference catalog and rejects missing, stale, altered or foreign entries. Catalog refs do not replace domain evidence/semantic validation. In particular, an accepted draft-review event's nonempty evidence refs are an envelope requirement; they do not establish sufficient structured support or a matching accepted `Draft.review`. Those checks belong to the related domain records and `CareerSnapshot`. An event records an observation and cannot grant approval, authority or permission to execute it.

`delivery_relation` is a pure comparison returning unrelated/duplicate/conflict. The key is workspace + registered source + source-event ID; absent source-event identity cannot promise deduplication. Semantic comparison ignores fresh ingestion event IDs and recording times, sorts unordered envelope object/evidence sets, and retains attribution, occurrence, payload, privacy, correlation and source identity. Ordered payload collections remain significant. No durable reservation, effect suppression, transaction or exactly-once guarantee exists here.

Workflow primitives are only exact content/revision review and the accepted `READ_ONLY`, `LOCAL_WRITE`, `EXTERNAL_WRITE` classification values. Workflow graphs, capabilities, predicates, execution states, retries, approvals for external effects, replay/shadow activation, workers and IR compilation remain deferred. An enum value does not enable a capability.

## Observable CareerLab compatibility

The adapter accepts the exact `ScenarioInput` fixture type or its closed input JSON plus an explicit import context. It validates ordinary fixture invariants before conversion and deterministically maps workspace/scenario/source/kind identities through a fixed namespace. It does not fetch source links or read evaluator files.

Recorded source facts become synthetic profile evidence, CV/draft units, jobs and reported application history. Source-qualified fixture reviews become explicitly synthetic reviews. The adapter reconstructs the fixture's recorded reviewed-supported state using those source reviews and marks the reconstruction method `synthetic_fixture_import`; this is compatibility bookkeeping, not new human review or independent verification. Original assertion actor/time and evidence source actor remain `None` when the fixture does not supply them. Application history uses the explicit import-context actor for attribution; it does not recover an original real-world actor from missing fixture metadata.

Draft proposals remain unreviewed. Requirement interpretations are not present in observable fixture data, so the mapped snapshot's requirements are empty. Recruiter-message records are not part of this minimal Core snapshot and are not recast as evidence or predictive labels. Evaluator categories, expected decisions/blocks/errors, future outcomes and canary answers never enter mapping. Cases 001–007 are the intended valid compatibility inputs; case 008 must still be rejected through its ordinary invalid transition rather than repaired using its oracle annotation.

Preserve the accepted baseline manifest `datasets/manifests/careerlab-dev-v1.json` and SHA-256 `a7d59618b371c0e51a5d6b09798eec1b48e82dbe37c5fe307a20f1bd0e8f40a4`. Adding Pydantic changes project/lockfile source identity while the accepted CareerLab input/oracle bytes and generator sources remain unchanged. Regeneration/verification under the new environment uses the separate manifest path `datasets/manifests/careerlab-core-env-v1.json`; explicitly select it rather than overwriting the baseline CLI default.

That compatibility manifest records current CareerLab/configuration identity, not hashes of all new Core modules. Retain the final Phase-2 Git commit and acceptance/check record for Core-source reproducibility. Neither manifest establishes annotation validity or held-out generalization. Validation and locked-test datasets remain unmaterialized; the eight shared-ancestry public cases remain one development component.

## Acceptance gate methodology

Before claiming completion, record actual commands/results and source identity for these gates:

1. Malformed/unknown fields, versions, duplicate JSON keys, wrong ID kinds, coercions, oversized records and attempts to weaken validation are rejected; valid canonical contracts roundtrip on supported interpreters.
2. Foreign, missing, stale and changed-content refs fail against current records/catalogs. Classification and profile/workspace scope remain consistent.
3. Reviewed source/claim support, contradictory and withdrawn evidence, unknown status, content/revision binding and causal review dates receive adversarial checks. Unsupported structured draft additions cannot pass an accepted snapshot.
4. Job-source spans/aliases and the application transition space are checked, including delayed recording, closure, the explicit user-reported manual exception and preservation of historical status without artifact-approval claims.
5. All six event contracts validate positive cases and reject wrong payload/ref/time/version/authority data. Unknown-only events remain valid; duplicate/conflict comparison is tested without claiming persistent deduplication.
6. The compatibility adapter maps valid observable public cases deterministically, leaves requirements/approval unknowns untouched and rejects the negative case. Tests establish that it accepts neither oracle objects nor an authoring bundle and does not read hidden answers.
7. The complete accepted CareerLab suite remains passing. Compare preserved source/input/oracle bytes with the accepted baseline, then record a separate environment manifest for changed dependency identity.
8. Run appropriate lint, formatting and strict typing checks plus complete contract/compatibility tests, including supported interpreter branches. Record limitations and unresolved failures rather than converting partial results into acceptance.
9. Confirm no persistence, service, model, UI, connector, browser, voice, workflow executor, cloud or real personal data was introduced. Make the focused local commit only after gates pass and stop before Phase 3.

These gates establish executable data-boundary and consistency checks on controlled records. They do not establish document authenticity, semantic drafting quality, extraction accuracy, authentication, database isolation, transactionality, external delivery, operational privacy enforcement, model performance or real-world hiring outcomes.
