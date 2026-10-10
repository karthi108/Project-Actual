Proceed with **ACTUAL Phase 7 — Verified Career Profile only**.

Accepted milestones:

- Phase 0: `4e06cc6`
- Phase 1: `5b6116a`
- Phase 2: `fc6d396`
- Phase 3: `d2a7544`
- Phase 4: `7deff65`
- Phase 5: `09d7653`
- Phase 6A: `bdc988a`

The original Phase-6 NO-GO evidence must remain preserved.

Do not proceed to Phase 8 automatically.

# Goal

Turn the candidate side of ACTUAL into a trustworthy, structured, evidence-backed career profile that Job Intelligence can consume without inventing qualifications.

The profile should answer:

> What can ACTUAL truthfully claim about this candidate, and what evidence supports each claim?

This phase is about:

- claims;
- evidence;
- provenance;
- capability representation;
- experience representation;
- languages;
- education/certifications where already justified;
- evidence-backed profile views;
- integration with the accepted Job Intelligence pipeline.

It is NOT CV tailoring or application generation.

---

# 1. Core invariant

Preserve:

```text
CLAIM
   ≠
VERIFIED EVIDENCE
```

A user saying:

```text
"I know Kubernetes"
```

must not automatically produce:

```text
Kubernetes = verified
```

Likewise, an LLM inference must never promote itself to verified evidence.

---

# 2. Inspect before implementation

Review:

- Phase-2 claim/evidence contracts;
- Phase-3 persistence;
- Phase-4 API exposure;
- Phase-6A evidence matching;
- accepted provenance rules;
- existing CareerLab profile representations.

Do not duplicate concepts that already exist.

Before editing code, explain:

1. what Phase 7 already has from previous phases;
2. what is actually missing;
3. what needs extension;
4. what should remain unchanged;
5. real-data restrictions;
6. acceptance gates.

---

# 3. Evidence-backed capability model

ACTUAL must be able to represent things such as:

```text
Python
FastAPI
Terraform
Azure
Cybersecurity
LLM integration
French
```

without flattening everything into arbitrary “skill percentages.”

Avoid:

```text
Python = 92%
Azure = 63%
```

unless a future measured methodology justifies that.

Prefer evidence and state.

Conceptually:

```text
Capability
    ↓
Claim(s)
    ↓
Evidence
```

Example:

```text
Capability:
FastAPI

Evidence:
- Project A
- Project B

Evidence type:
project implementation

Status:
supported
```

Design actual contracts based on accepted domain types.

---

# 4. Preserve evidence provenance

Every evidence-backed profile fact should remain traceable.

ACTUAL should be able to answer:

```text
Why do we believe this?
```

Potential provenance may include, only where accepted:

- personal project;
- professional experience;
- internship;
- education;
- certification;
- language qualification;
- repository/work artifact;
- self-reported claim.

Do not create evidence categories merely because they might be useful eventually.

---

# 5. Experience must remain semantically honest

Preserve the Phase-6A hardening.

Never collapse:

```text
internship
personal project
academic project
employment
```

into one fake number of “professional years.”

Example:

```text
6-month internship
+
2 years personal projects
```

must NOT become:

```text
2.5 years professional experience
```

Experience types and durations should remain distinguishable.

---

# 6. Temporal evidence

Where justified, evidence should support timing.

Examples:

```text
started_at
ended_at
ongoing
```

This allows ACTUAL eventually to distinguish:

```text
used once three years ago
```

from:

```text
currently used professionally
```

Do not invent dates.

Unknown dates remain unknown.

---

# 7. Conflicting evidence

Design behavior for cases such as:

```text
Claim:
French B2

Evidence:
official certificate says A2
```

ACTUAL must not silently choose the more flattering answer.

Conflicts should be explicit.

Potential outcomes may include:

```text
SUPPORTED
UNVERIFIED
CONFLICTED
UNKNOWN
```

or the minimum equivalent supported by existing contracts.

Avoid unnecessary status proliferation.

---

# 8. Evidence aggregation

If several pieces of evidence support one capability, ACTUAL may aggregate them into a profile view.

But aggregation must be deterministic and explainable.

Example:

```text
Python

Evidence:
Project A
Project B
Internship X
```

The resulting profile may say:

```text
supported by 3 evidence records
```

It must not let Qwen arbitrarily decide:

```text
expert
```

unless a future explicit rule exists.

---

# 9. Job Intelligence integration

Phase-6A Job Intelligence should consume the verified profile through a stable interface.

Preferred conceptual flow:

```text
Verified Career Profile
          ↓
Evidence Projection
          ↓
Job Intelligence
          ↓
Requirement-by-requirement comparison
```

Job Intelligence must not query random raw profile fields or bypass provenance.

Keep the candidate evidence input deterministic.

---

# 10. Unsupported skills

Critical regression requirement:

```text
No evidence
   ↓
cannot satisfy requirement
```

Examples:

```text
Docker evidence
≠ Kubernetes evidence

AWS evidence
≠ Azure evidence

Python project
≠ 5 years professional Python
```

Related technologies may appear in explanatory context but cannot satisfy requirements.

---

# 11. Profile completeness

ACTUAL may identify where profile information is missing.

Example:

```text
Azure:
no evidence

French:
self-reported only

Terraform:
project evidence present
```

This is useful.

But:

```text
missing evidence
```

does not mean:

```text
candidate lacks the skill
```

Distinguish absence of evidence from evidence of absence.

---

# 12. Source-of-truth rules

Define clearly which operations can create:

- a claim;
- evidence;
- verification status;
- profile projection.

The LLM may help interpret evidence later.

It may NOT independently create verified facts.

If Qwen is involved at all in Phase 7, its result remains:

```text
proposal
```

requiring deterministic validation or explicit user confirmation.

Prefer not using Qwen where ordinary domain logic is sufficient.

---

# 13. API behavior

Expose only profile operations needed for the current v0.1 architecture.

Potential capabilities:

```text
create claim
attach evidence
retrieve evidence-backed profile
inspect unsupported/unverified claims
```

Do not automatically create CRUD endpoints for every persistence table.

Keep application services between FastAPI and persistence.

---

# 14. Persistence

Use existing Phase-3 persistence wherever possible.

If Phase 7 requires new stable domain concepts, add only the minimum migrations required.

Do not alter accepted persistence merely to make API work easier.

Migration tests remain required.

---

# 15. Real personal data boundary

Explicitly review the accepted Phase-0/Phase-4 security decision that currently blocks real-data access.

Do NOT bypass that restriction merely because Phase 7 represents a personal profile.

If the accepted architecture still requires authentication or another gate before real personal data is allowed:

```text
keep Phase 7 synthetic/local-test only
```

and document what future phase unlocks real data.

If existing accepted documents already permit a safe local-only profile path, demonstrate that from the accepted contract before enabling it.

Do not silently relax security.

---

# 16. No resume fabrication

Phase 7 does not generate CV wording.

However, its architecture must make future fabrication harder.

Future systems should only be able to derive application claims from:

```text
verified/supported profile evidence
```

or explicitly show something as:

```text
unverified user claim
```

Never blur the two.

---

# 17. CareerLab integration

CareerLab profile fixtures should remain compatible.

Do not modify accepted hidden ground truth merely to accommodate Phase 7.

Evaluator-only fields remain outside runtime access.

Preserve manifests/hashes unless an explicitly versioned extension is justified.

---

# 18. Tests

Add focused tests for:

## Claims

- supported;
- unsupported;
- unverified;
- duplicate claims;
- conflicting claims.

## Evidence

- valid provenance;
- missing provenance;
- invalid references;
- duplicate evidence;
- temporal boundaries.

## Experience

- internship vs professional work;
- project vs professional work;
- overlapping periods;
- unknown dates;
- no fake experience accumulation.

## Languages

Where current contracts support them:

- explicit CEFR level;
- unverified language claim;
- contradictory evidence;
- unknown level.

## Job Intelligence integration

Prove:

- supported evidence can satisfy appropriate requirements;
- unsupported capabilities do not satisfy requirements;
- ambiguous profile information produces safe UNKNOWN/review behavior;
- Phase-6A truthfulness gates remain intact.

## Persistence/API

- round trips;
- transactions;
- safe errors;
- provenance preservation.

All previous accepted tests remain regression requirements.

---

# 19. Do NOT add

Do not add in Phase 7:

- frontend;
- Next.js UI;
- CV tailoring;
- cover letters;
- application messages;
- job submission;
- Gmail;
- Calendar;
- scraping;
- browser automation;
- voice;
- Teach Mode;
- Workflow IR execution;
- NEXUS;
- Temporal;
- Redis;
- cloud deployment;
- paid LLM providers.

---

# 20. Acceptance criteria

Phase 7 is accepted only if:

1. candidate claims and evidence remain distinct;
2. provenance is preserved;
3. unsupported claims cannot become verified silently;
4. model output cannot promote itself to verified evidence;
5. professional experience cannot be fabricated through aggregation;
6. conflicting evidence is represented safely;
7. profile projection is deterministic;
8. Job Intelligence consumes evidence through the accepted profile boundary;
9. Phase-6A zero-fabricated-evidence guarantees remain intact;
10. evaluator-only CareerLab data remains inaccessible;
11. real-data restrictions remain enforced according to accepted security decisions;
12. persistence/API behavior is tested;
13. all accepted Phase 0–6A regressions pass;
14. PostgreSQL migration checks pass;
15. lint passes;
16. formatting passes;
17. strict typing passes;
18. supported Python-version checks pass;
19. known limitations are documented;
20. working tree is clean.

Commit Phase 7 only after acceptance passes.

Then stop.

Do NOT proceed automatically to Phase 8.