# ADR 0003: Small Core Contracts and current-source relationships

Status: implemented within the user's Phase-2 request. Phase 0 (`4e06cc6`) and Phase 1 (`5b6116a`) are accepted baselines. This decision establishes data boundaries; it does not add infrastructure or authorize Phase 3.

## Decision

Use strict, closed, frozen Pydantic records with distinct opaque ID types, bounded values, explicit wire schema versions, canonical JSON and aware UTC time. Pin Pydantic 2.13.5 in the project and lockfile; exercise Python 3.13 and 3.14. Reject unchecked construction, permissive loading and unvalidated copies at the public contract boundary.

Separate generic primitives/references/review/event metadata into Core, evidence/claim support into Profile and concrete career records/events into Career. Resolve inter-record invariants using a current `Profile`, `CareerSnapshot` or supplied event reference catalog. Valid isolated shapes do not prove referenced objects exist or authorize their use.

Keep claims and evidence separate. A review binds exact content and records reviewer, method and time. Qualifying support additionally requires current scoped source evidence and no qualifying contrary evidence hidden elsewhere in the profile. Human confirmation and AI/user reports do not confer independent verification. Support is limited to structured assertion units; arbitrary prose remains untrusted.

Distinguish each claim/evidence record's own-review `content_digest` from its complete `snapshot_digest`. Own-review identity excludes its review to avoid circular hashes. Dependency refs include current review/status/classification; revocation or review changes therefore stale downstream refs even when assertion text is unchanged. Reference constructors and relationship resolution enforce this distinction.

Requirements are proposed scoped interpretations pinned to source job revision/hash and an exact Unicode code-point span. They carry priority/origin and optional content review; no extraction or fit algorithm is implemented. One normalized subject per canonical opportunity and one application per profile/opportunity prevent ambiguous duplicates in this slice. Reapplication intent or multiple structured requirements for one subject would need an explicit later contract revision.

Preserve the accepted seven-state application history. Add a narrow production tracking exception: a user-reported external-manual submission can move preparing/ready-for-review directly to applied. This records an outside submission without inventing an internal draft review. Synthetic observations retain the strict fixture transition map. Historical reviewed status is distinct from current artifact approval.

Core owns generic `EventHeader`; Career owns the six closed payloads and their validations. Events are observations, never executable instructions or authority. Source-redelivery comparison is a pure duplicate/conflict classifier with stable source identity. Persisted reservations, uncertain external outcomes and business-action execution remain later work.

Workflow primitives contain only exact-content review and `READ_ONLY`, `LOCAL_WRITE`, `EXTERNAL_WRITE` classification. Defer graphs, capability catalogs, compiler/executor states and approval machinery until an accepted milestone needs them. Do not introduce model providers, APIs, storage, connectors or enterprise abstractions.

## CareerLab baseline and compatibility

Keep the accepted fixture source, eight inputs, evaluator hashes and original manifest unchanged. Adding the runtime dependency changes configuration hashes, so record the current environment in `careerlab-core-env-v1.json` rather than overwriting `careerlab-dev-v1.json`. Explicit CLI selection is necessary because the accepted CLI default is unchanged.

Map observable inputs through a separate synthetic adapter. Do not turn hidden normalization/recommendation/outcome labels into runtime contracts. Preserve explicit synthetic provenance and unknown original actor/time fields; reconstructed supported-claim review is marked compatibility bookkeeping. Requirements remain empty and draft proposals unreviewed. Recruiter messages are outside this minimal snapshot. No held-out data is generated or inspected.

## Alternatives and consequences

A single shared model file would blur responsibility. A generic enterprise object/metadata registry or full Workflow IR would add unused states. Pure unvalidated dataclasses would require duplicating recursive boundary validation already justified by the accepted Phase-2 Pydantic direction. Full persistence/authorization would exceed this request.

Complete snapshot-bound refs require downstream reconciliation on review or status changes. This is deliberate: unchanged source text must not preserve withdrawn support. IDs remain stable within immutable records, but the future mutation layer must manage monotonic revisions and transactions; this layer cannot enforce history across unrelated supplied snapshots.

Schema/version and bounds fail closed, rather than silently accepting unknown future meanings. Classification guards prevent known cross-object privacy downgrades but cannot detect all secrets in free text. Source references/review fields record provenance but cannot authenticate real documents or reviewers.

The [acceptance record](../phase-2/acceptance-review.md) documents checks and limitations. Revisit this ADR when adding a new schema version, richer assertion taxonomy, reapplication intent, source mutation/persistence, semantic assessment, an event producer or workflow execution. Preserve the accepted truth/authority boundaries when doing so.
