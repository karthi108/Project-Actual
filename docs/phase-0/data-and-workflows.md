# Data and workflow principles

Status: semantic contract for future implementations, not executable schemas.

## Identity and ownership

Opaque identifiers distinguish workspaces, principals, jobs, evidence, artifacts, events and later runs/actions. Personal installs initially have one workspace and owner. The server derives the authenticated actor/workspace; clients and model responses cannot select authority by providing an ID. Relationships must remain inside their owning workspace. This supports later isolation tests without claiming present multi-tenancy.

Time values are timezone-aware; persistent instants use UTC. User-facing times use the configured timezone (initially Europe/Berlin). Preserve both occurrence and recording time for delayed/out-of-order events. Never invent a causal sequence from arrival order alone.

## Claims, evidence and draft content

A claim is a specific assertion: skill, level, dates, experience duration or language proficiency. An evidence record identifies a source and relevant excerpt/structured fact, origin, collection time, content digest, classification and review method. A support relationship says which assertion a source supports, with scope and limitations.

Statuses distinguish `self_reported`, `candidate_support`, `reviewed_supported`, `contradicted` and `withdrawn`. A reviewed record retains reviewer, method and time. Human confirmation records who confirmed it; independent verification records the separate method/source. A checksum identifies content, not authenticity or proficiency. A project link alone does not prove the claimed level of expertise.

Requirements distinguish employer-stated essential/preferred/ambiguous status. Assess each as supported, partial, gap or unknown with rationale and evidence. Separate explicit job constraints from ACTUAL's interpretations. Revoking evidence or editing a source invalidates affected derived assessments and reviews.

For factual draft changes, output assertion IDs and support links rather than an unstructured final CV. The rendering gate accepts only `reviewed_supported` support whose scope covers the assertion. Missing/wrong-owner support and `self_reported`, `candidate_support`, `contradicted` or `withdrawn` status cannot satisfy that gate. Reject unsupported changes to levels, dates or experience. New self-reports remain visible claims. Early safe rendering uses approved factual units/templates; unconstrained paraphrases remain reviewable suggestions until semantic review. Supported inputs and schema validation alone do not prove a paraphrase truthful.

An unresolved or unsupported factual addition cannot silently enter a recommended ready-for-use draft. Suggestions about learning a skill or improving presentation are distinguished from statements that the person already has the skill. Record draft content digest and revision; any factual/content change invalidates previous review. Human review remains necessary. ACTUAL cannot control edits or submissions made outside the application.

## First Work Event contract

Required concepts for Phase 2:

| Field | Meaning |
| --- | --- |
| `schema_version`, `event_id` | Closed schema version and durable unique event identity |
| `workspace_id`, `actor_id` | Server-derived owner and actor |
| `occurred_at`, `recorded_at` | Source occurrence and ingestion instants |
| `activity`, `source` | Registered semantic event and source identity |
| `business_objects` | Typed, owner-scoped object references |
| `payload` | Versioned, activity-specific allowlisted fields |
| `privacy_classification` | Synthetic, personal or sensitive; secrets rejected |
| `source_event_id`, `correlation_id` | Source deduplication and related-operation identity where available |
| `evidence_refs` | Supporting records when the event asserts a reviewed decision |

Phase-1 scenario data may use simple fixture representations; formal domain/schema enforcement starts in Phase 2. A contract cannot be an unlimited `properties` dictionary. Unknown fields, oversized payloads and unsupported event versions fail validation or enter an explicit migration path. Passwords, tokens, full CV text and raw model responses are excluded from semantic event payloads.

First activities: `job_added`, `requirements_reviewed`, `fit_assessment_recorded`, `cv_recommended`, `draft_reviewed`, `application_status_recorded`. Model metadata, once used, identifies model/config/prompt version without copying private prompts into the event. `application_status_recorded` can preserve a user-reported submission without asserting independently verified delivery.

An event records a fact or reported observation; it is not a command and never grants permission. Duplicate delivery of an identical source event is a no-op; the same identity with different content is a conflict requiring investigation. Later replay preserves original provenance and cannot execute effects. State changes and their corresponding semantic events use one transaction when persistence exists.

## Application and review state

Job decision (new, pursuing, rejected, archived) is separate from application lifecycle (preparing, ready_for_review, reviewed, applied, interview, offer, closed). A history entry records transitions. The allowed transition map is explicitly defined with Phase-2 contracts; clients cannot set arbitrary states. Applying is recorded manually in v0.1. No enum value enables a connector.

## Future Workflow IR principles

Phase 0 establishes constraints; Phase 10 designs and implements the actual IR based on the observed career slice.

- Immutable, versioned typed workflow definitions with registered capabilities and bounded graph structure.
- Step inputs/outputs, timeout, retry budget, permissions, failure path, effect metadata and data classification are explicit.
- Registered deterministic predicates and bounded expressions only; no arbitrary Python, shell, dynamic imports or generated executable code.
- Model steps propose structured data. A deterministic validator calculates required capabilities/permissions and rejects unsupported nodes or references.
- Separate definition, run state, proposal, review and effect execution. Candidate status grants no authority.
- Validate types, references, reachable outcomes, cycles/iteration bounds and budgets before persistence or execution.
- Capability/step-level activation enables safe subsets; replay, shadow and activation status remain distinct.
- Replay/shadow use substitutes for effect adapters and cannot reach production writes. Read adapters still obey data-egress and privacy rules.

## Consistent action classification

Use three primary effect kinds: `READ_ONLY`, `LOCAL_WRITE`, `EXTERNAL_WRITE`. Add independent metadata for destination, data classification, reversibility (`reversible`, `irreversible`, `unknown`) and risk flags (`communication`, `financial`, `privileged`). Sending an email is an external write with communication risk. Submission is an external write. Account deletion is a write with irreversible risk. The policy uses the most restrictive applicable requirements; absence of a flag never grants authority.

A read can still disclose data or contact a hostile destination. Effect kind is not the sole security policy. v0.1 enables only the required local state changes and local model calls; no external effect adapter exists.

## Future authorization and approval

`AuthorizationPort` receives a principal, action, resource and context; initial policy defaults to deny. NEXUS is a later optional adapter. Model text, client flags and observed behavior cannot supply authority.

Approval binds owner/principal, immutable workflow/step version, business action identity, exact capability, recipient/destination, canonical arguments, artifact content digests, approver, expiry and policy version. Canonicalization rules are defined before hashing. Storing a mutable CV path is insufficient. Changed content, target, arguments, policy or authority invalidates approval.

Immediately before an effect, revalidate current authorization/revocation, approval binding/expiry and the exact payload to dispatch. Reserve the action and bind/consume approval atomically for one execution intent, recording its audit identity. Recovery attempts may reuse that approval only for the same intent and exact payload under its still-current conditions; it never approves a different operation. Define the dispatch/revocation boundary: requests cancelled before dispatch must not execute; a remote action already accepted may require reconciliation or compensation. Review is never a blanket permission to all future actions.

## Duplicate prevention and uncertain outcomes

Use a durable business intent identity, e.g. owner + provider/destination account + action + canonical opportunity + submission intent, independent of workflow version. A unique constraint and serialized reservation prevent concurrent duplicate intentions. Changed payload under the same intent is a conflict requiring renewed review, not permission to resend. Deliberate reapplication needs a distinct explicitly reviewed intent; a model or upgrade cannot manufacture one. Workflow version remains provenance, not the sole deduplication key.

Local state/events can commit atomically. A remote provider is outside that transaction: an acknowledgement may be lost after a successful send. Use provider idempotency where supported; otherwise reconcile and mark `outcome_unknown` without automatic resend. Neither a local outbox nor a unique key proves exactly-once remote execution. Lease/fencing and restart tests precede concurrent workers.

Every future effect has an append-oriented audit record identifying actor, resource, action, run/version, authority, reviewed inputs, approval and outcome. Audit records avoid private payload duplication and follow [the deletion policy](privacy.md). Append-oriented storage is not tamper-proof against the local administrator.
