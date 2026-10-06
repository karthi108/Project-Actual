# Phase 7: evidence-backed career profile

Scope: the user's Verified Career Profile request, following accepted Phase 6A `bdc988a`. The original Phase-6 NO-GO and all accepted evaluation artifacts remain historical evidence. This original Phase-7 design remains the implementation contract. The later [continuous-build decision](../adr/0010-continuous-office-build.md) authorizes Phases 8–27 and replaces checkpoint acceptance with provisional office verification and canonical validation pending.

## Reuse and extension

Phase 2 already supplies structured skill, CEFR language and generic-month assertions, separate claim/source review, exact references and five claim states. Phase 3 stores a complete validated CareerSnapshot transactionally. Phase 4 provides synthetic-only services and safe local HTTP transport. Phase 6A deterministically matches reviewed support and conservatively abstains on professional/backend experience meanings that generic months cannot establish.

The missing slice is a deterministic profile view, one admitted evidence projection for matching, controlled synthetic review/withdrawal operations, and explicit source experience context. No duplicate profile store or new capability ontology is needed. Existing Symbol subjects represent Python, FastAPI, Terraform, Azure, cybersecurity and LLM integration without percentages. Education/certification assertions remain deferred: neither the accepted Assertion nor CareerLab supplies the necessary semantics.

## Truth and provenance

1. Creating a claim records a self-report. Attaching a source never accepts the claim.
2. Reviewing a source binds its current structured content, including any experience context. Only active synthetic_fixture sources can receive the new application-level synthetic review. The reviewer, method and time come from the service, not the HTTP body.
3. Accepting a claim is a separate pinned operation. Sufficient current reviewed support is required, and explicit current contrary evidence blocks acceptance. The result is reviewed synthetic support, not independent real-world verification.
4. Withdrawal retains source attribution and its existing review metadata on the record, replaces exact dependent references and invalidates affected claim reviews in one aggregate transaction. Any CV/draft reference dependencies require a future explicit reconciliation use case; these commands refuse them with 409.
5. Generation, record revision and complete record snapshot digest bind review/withdraw intents. Reusing a stale pin or an already completed review fails; no automatic retry or claim promotion occurs.

The public evidence-backed view distinguishes declarations, reviewed source values, eligible reviewed claims, withdrawn records and explicit contrary evidence. It exposes structured references and claim origin; source details remain resolvable through the existing profile read. The view does not repeat source excerpts as endorsed facts. A French B2 declaration accompanied by positive A2 evidence has declaration_exceeds_support=true and remains unverified at B2. A positive lower level alone does not logically disprove a higher level. An explicitly reviewed contrary source produces conflict. Missing evidence does not prove absence of a skill.

## Experience context and compatibility

EvidenceRecord may contain an explicit `actual-experience-context-v1` context: professional_employment, internship, academic, personal_project, open_source or unknown; optional aware activity instants and ongoing status. Reversed intervals, an end for an ongoing activity and activity dates after source collection are rejected. Unknown dates/status remain null. Source-authored months are preserved; calendar arithmetic, accumulated tenure and freshness scoring are absent.

The accepted generic experience assertion has no category. Therefore a contextual source can be source-reviewed, but cannot qualify generic Claim/CV support or refute generic tenure. A generic reviewed_supported claim requires sufficient context-free support. Context-specific contrary sources remain visible individually without creating a generic conflict. This rule is enforced in the domain, the application, the public view and matching, so a caller cannot bypass it by constructing a raw aggregate. Context-specific sources appear individually in the experience view with their assertion, relation, category, interval and exact reference. They are never summed, including overlapping periods. A new scoped experience claim/matching contract would need a later accepted design.

Absent context is omitted from serialization, preserving every legacy canonical byte, source content digest and dependency digest. Present context is included in reviewed source content and exact snapshot references; adding/changing it invalidates old reviews. The core envelope remains actual-core-v1 with a closed required context_version for this additive extension. Old readers reject the new field rather than silently discarding it. No migration is required: the existing canonical JSON payload round-trips it, while the accepted SQL projections/schema guards remain unchanged.

## Projection and matching

`admit_profile` validates the exact synthetic graph before serialization can discard extra/subclass fields. `project_evidence` groups current claims and sources in sorted kind/subject/unit and ID order. `evidence_backed_profile` additionally binds the snapshot's explicit as_of and rejects future facts. The internal immutable projection is rebuilt from the current domain aggregate; it is not a trusted input format callers may manufacture for matching.

Job Intelligence consumes these groups through matching v3. It retains the five fit states, conservative requirement normalization, exact references and accepted legacy decisions. It does not traverse candidate prose or ask Qwen about candidate facts. Extraction instructions, model/provider configuration, evaluator contracts, scores and recommendations are unchanged. Assessments and profile views remain transient and are rebuilt against current revision/digest.

## HTTP, storage and privacy

Existing create-claim and attach-evidence paths remain. The minimum new paths are GET /api/v1/profile/evidence, POST /api/v1/profile/evidence/{id}/synthetic-review, POST /api/v1/profile/claims/{id}/synthetic-review and POST /api/v1/profile/evidence/{id}/withdraw. The evidence view uses an actual-api-v1 envelope containing generation and profile. Review/withdraw bodies contain only schema_version, expected_generation, expected_revision and expected_digest. They cannot select independent verification, actor, method, timestamp, workspace or status.

The accepted unauthenticated local synthetic mode remains the only supported mode. Loopback transport, server-selected workspace/actor, bounded JSON, classification checks, no-store responses, safe errors and metadata-only logging remain mandatory. Labels cannot detect real prose misrepresented as synthetic and local callers are not authenticated. Real personal sources require a separately accepted access/security gate; Phase 7 does not authorize them. No source URLs are fetched, files read by model paths, new model calls, tools, new tables or side effects outside local profile state are introduced.

## Acceptance gates

All gates are conjunctive; no test-count or accuracy percentage substitutes for them:

- Exact validated projection, deterministic ordering/serialization, provenance-preserving refs and fail-closed versions/extras.
- Separate reviews; zero silent promotion from user/AI claims or source review; insufficient/contrary/context-only generic support rejected. Withdrawal invalidates downstream claim support atomically.
- Typed experience remains unsummed and non-equivalent across categories; unknown times remain unknown; explicit language disagreement is visible.
- Real PostgreSQL round trips, rollback, concurrent conflict, owner/reference/generation boundaries and accepted migration checks pass.
- All accepted Phase 0–6A deterministic regressions, lint, formatting and strict typing pass on supported Python 3.13/3.14.
- Replay all 87 preserved source selections through the unchanged extraction capability and current deterministic pipeline: all previously reported original/adversarial/semantic decisions and error counts remain unchanged, no candidate/evaluator content reaches extraction, and input profile bytes remain unchanged. Replay is an integration regression, not fresh live Qwen evidence or a new AI-quality claim.
- CareerLab observable/oracle hashes, earlier manifests, historical NO-GO and Phase-6A artifacts remain byte-identical. A separate environment manifest records the changed project hash. Validation/locked-test material remains absent.
- Review findings are resolved, known limitations and executed checks recorded, then one local commit leaves the working tree clean. Use a provisional WIP checkpoint and continue under ADR 0010; no acceptance tags. Canonical gates remain pending.

## Limits

Synthetic review is not source authentication. Evidence counts do not establish source independence, expertise or real-world accuracy. Source-authored intervals/months may disagree without automatic resolution; no employment-duration inference is performed. Duplicate identities fail, but different IDs can describe overlapping or duplicate source content; this does not increase a supported level or accumulate duration. Positive low-level evidence is a lower bound, not a maximum proficiency certificate. Profile completeness is limited to observed scopes; absence from the view means no recorded fact. The existing store retains current aggregate revisions, not a complete profile revision audit trail; invalidated claim reviews are cleared and source review metadata survives withdrawal. No refresh/expiry policy, external verification adapter, real-document intake, education ontology, CV rendering or application generation is added.
