# ADR 0009: source-reviewed profile projection

Status: implemented and office verified; canonical acceptance pending under ADR 0010; see [design](../phase-7/design.md) and [acceptance review](../phase-7/acceptance-review.md).

The accepted Profile already owns strict claims, sources and digest-bound reviews. Job Intelligence needs a stable admitted evidence boundary and users need a view separating declarations from current support. Replacing these contracts with a second verified-profile store would duplicate truth and introduce stale reconciliation.

Keep the existing aggregate. Add an immutable deterministic grouping projection and a transient reference-rich public view. Job Intelligence builds and consumes the projection from the current exact synthetic Profile. Source review and claim acceptance remain separate application intents; only synthetic fixture sources can receive the new review operation. Server actor/time/method and generation/revision/snapshot pins prevent client-supplied verification authority. Source revision/withdrawal reconciles all affected refs and claim reviews in the same existing transaction; all CV/draft reference dependencies are refused pending an explicit future use case.

Extend EvidenceRecord with optional versioned ExperienceContext. Omit absent context to preserve accepted canonical bytes/hashes. Include present context in source content digests so an old review cannot certify new facts. Store it in the existing JSON payload; no new table, column, migration or dependency is justified.

The legacy experience Assertion is unscoped months. Contextual durations therefore qualify source review but not generic claim support, even when their category is professional_employment. Enforce this in the domain so future CV support checks cannot bypass the projection. Display each contextual assertion separately; do not sum periods or invent dates. A later category-specific claim contract would require an explicit accepted extension. This conservative choice loses automatic matching utility until then, but avoids manufactured professional tenure.

Positive lower CEFR evidence is not a ceiling. Display optimistic declaration/support discrepancies; reserve conflict for explicit contrary evidence. Keep existing claim states and five fit states, not a score or a new proficiency ontology.

The Phase-4 unauthenticated synthetic-only boundary remains binding. These operations do not verify source authenticity, authenticate local callers, unlock real documents or grant tools. Education/certifications, scoped tenure matching, CV generation, richer review history and external verification remain later decisions. All frozen CareerLab and original/hardened evaluation artifacts remain unchanged; Phase 7 records a separate environment manifest and a clearly labeled deterministic replay regression.
