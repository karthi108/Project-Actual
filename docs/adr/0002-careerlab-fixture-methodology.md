# ADR 0002: CareerLab public development fixture boundary

Status: implemented under the user's Phase-1 request; Phase-0 contract accepted at `4e06cc6`. This records fixture choices within that contract, not a change to ACTUAL production scope.

## Decision

Implement eight offline public development scenarios with standard-library frozen dataclass schemas, strict recursive decoding, semantic invariants and separate observable/evaluator serializers. Use a local seeded random generator for bounded context/date variations, explicit dates and canonical JSON for byte reproducibility. Author annotations separately under a published rubric; do not generate labels by running the future assessor.

Keep generated evaluator files outside the observable directory and out of Git. Commit public development inputs, the version/hash manifest, authoring source, tests and methodology. The developer may inspect these public answers; a future evaluated component may receive only input files. Neither code organization nor Git ignore is a sandbox.

All eight fixtures share source ancestry and belong to one development component. Do not divide them into held-out partitions. Test direct/transitive lineage and normalized posting duplication rules with handcrafted public test metadata. Actual validation and locked-test construction/freeze remain deferred under the accepted evaluation lifecycle.

Resolve bounded interpretation ambiguities explicitly: self-report-only French A2 stays unknown for reviewed support with a declared shortfall against B2; experience is a reviewed scalar, not computed tenure; skill/CEFR ordinals are fixture conventions. Safe CV alternatives maximize fully supported canonical requirement coverage with all ties accepted, without a hiring score. Aliased opportunities share one annotation set rather than doubling relevance. Draft proposals have no approval/status field; support derives from scoped reviewed profile evidence.

## Alternatives and consequences

Randomly splitting these eight scenarios would preserve candidate/template ancestry across partitions and yield misleading validation. Separate lineages require new authoring rather than renamed IDs or shifted dates. The small dataset is suitable for controlled integrity checks and teaching, not model-quality or labor-market claims.

Production Pydantic/domain schemas, richer tenure/prose evaluation and an evaluation runner would add capability beyond the accepted Phase-1 slice. Closed fixture contracts and validators are sufficient here; Phase 2 may replace them for production without silently redefining this rubric.

Canonical source/record hashes and a lockfile identify the delivered artifacts. They do not prove annotations are correct. Independent public-case review, adversarial invariant tests and explicit limitations supply the additional evidence recorded in [the acceptance review](../phase-1/acceptance-review.md).

Revisit before adding an independently authored evaluation partition, changing the annotation rubric or introducing production profile/evidence models. A frozen locked set must not be used for individual-case tuning.
