# ADR 0007: synthetic extraction and deterministic evidence assessment

Date: 2026-10-05. Status: implemented design under the user's Phase-6 request;
quality acceptance is reported separately. Previous accepted milestones end at
Phase 5 `09d7653`.

## Context

ACTUAL needs its first measurable AI-assisted career capability. Accepted CareerLab
has seven valid scenarios, 24 requirement units and a deliberate eighth rejection
case. All scenarios share source ancestry. Its oracle covers requirement support,
priority and thresholds; it does not label overall job recommendations. Existing
claims/evidence contracts distinguish current reviewed support from self-report,
contradiction, withdrawal and independent verification.

Sending the full fixture/profile to a model would violate minimization, exceed the
4 KiB model-input budget and expose unnecessary material. Asking Qwen to decide
candidate support would also make hallucinated evidence harder to prevent and isolate.

## Decision

Use one narrow versioned extraction capability, one gateway invocation per posting
and the accepted local Qwen provider. The model proposes exact source clauses,
qualification terms and priority; it sees only synthetic job text. Deterministic
source/context checks, explicit alias/scope normalization and current evidence matching
produce a transient, source/profile-bound five-state matrix. Requirements remain
unreviewed AI proposals. No schema or hash certifies semantic correctness or truth.

Preserve the accepted states `supported`, `partial`, `gap`, `unknown`, `conflict`,
priorities `essential`, `preferred`, `ambiguous` and Assertion kinds/units. Unknown
normalization gets its own explicit unresolved representation instead of a fabricated
minimum. Evidence references must resolve exactly against the current scoped profile.
Contrary evidence takes precedence; related technologies cannot satisfy each other.
Explanations are deterministic templates; no second explanation model is needed.

Keep assessments transient, with deterministic content-bound identities and no new
table, event or migration. Defer numeric scores and overall recommendations because
there is no accepted weighting or overall-fit oracle. Defer HTTP exposure because
the present goal is quality evaluation; unauthenticated model-backed intake adds
privacy/resource controls without helping that measurement. Use a fixed hash-pinned
synthetic development runner with no arbitrary input/path arguments.

Preregister [the task metrics and gates](../phase-6/design.md), freeze the first
version, run three complete development trials and retain every failure. Read oracle
answers only at the separate evaluator boundary after runtime calls; verify their
accepted hashes before parsing. Supplemental adversarial pairs are separately authored
public development records, preserving all accepted CareerLab artifacts. No held-out
partition is created or inspected. Critical failures produce NO-GO regardless of
averages or passing software tests.

## Alternatives and trade-offs

- One all-in-one fit prompt would mix extraction, normalization and evidence authority,
  making independent evaluation and truthfulness guarantees weaker.
- A large regex extractor would overfit the fixture writing style and avoid measuring
  the proposed semantic component. Use narrow deterministic mappings for explicit
  meanings while measuring Qwen's requirement proposals separately.
- A broad ontology or unsupported professional-duration/version conversion would force
  assumptions beyond the accepted evidence contracts. Keep those meanings unresolved.
- A raw chat API, stored model transcripts and automatic assessment persistence add
  access/retention/lifecycle concerns with no present acceptance need.

The first capability is deliberately bounded: at most eight units, 1024 UTF-8 input
bytes, 512 output tokens and nonoverlapping source spans. Shared-clause requirements,
rich alternatives, unknown platforms, prose proficiency and professional constraints
can be rejected or unresolved. Development success would justify later controlled
expansion; it would not prove generalization, employability or real-data readiness.

Revisit after measured failures demonstrate a need, with fresh declared capability
versions, supported examples and security/evaluation decisions. No Phase 7 starts
automatically.
