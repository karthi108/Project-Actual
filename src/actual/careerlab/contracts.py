"""Closed fixture schemas. These are not ACTUAL's Phase-2 production contracts."""

from dataclasses import dataclass
from typing import Literal

type Subject = Literal["python", "fastapi", "llm_integration", "azure", "french", "experience"]
type Unit = Literal["skill_level", "cefr_level", "months"]
type ClaimStatus = Literal[
    "self_reported", "candidate_support", "reviewed_supported", "contradicted", "withdrawn"
]
type State = Literal[
    "preparing", "ready_for_review", "reviewed", "applied", "interview", "offer", "closed"
]
type Coverage = Literal[
    "explicit_gaps",
    "cv_alternatives",
    "unsafe_additions",
    "conflicting_evidence",
    "unreviewed_evidence",
    "ambiguous_requirements",
    "hostile_source",
    "duplicate_and_invalid",
]
type Split = Literal["development", "validation", "locked_test"]


@dataclass(frozen=True, kw_only=True)
class Record:
    id: str
    synthetic: Literal[True] = True


@dataclass(frozen=True, kw_only=True)
class Company(Record):
    name: str
    context: str


@dataclass(frozen=True, kw_only=True)
class JobPosting(Record):
    company_id: str
    canonical_opportunity: str
    source_reference: str
    posted_at: str
    title: str
    text: str


@dataclass(frozen=True, kw_only=True)
class Evidence(Record):
    subject: Subject
    value: int
    unit: Unit
    relation: Literal["supports", "contradicts"]
    source_kind: Literal["project_review", "document_review", "self_report"]
    excerpt: str
    observed_at: str
    reviewer: str | None
    review_method: str | None
    reviewed_at: str | None


@dataclass(frozen=True, kw_only=True)
class ProfileClaim(Record):
    subject: Subject
    value: int
    unit: Unit
    text: str
    status: ClaimStatus
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True, kw_only=True)
class Candidate(Record):
    name: str
    claims: tuple[ProfileClaim, ...]
    evidence: tuple[Evidence, ...]


@dataclass(frozen=True, kw_only=True)
class CVVariant(Record):
    name: str
    summary: str
    claim_ids: tuple[str, ...]


@dataclass(frozen=True, kw_only=True)
class DraftAssertion(Record):
    subject: Subject
    value: int
    unit: Unit
    text: str
    source_claim_ids: tuple[str, ...]


@dataclass(frozen=True, kw_only=True)
class HistoryEntry(Record):
    state: State
    occurred_at: str
    recorded_at: str


@dataclass(frozen=True, kw_only=True)
class Application(Record):
    job_id: str
    candidate_id: str
    state: State
    history: tuple[HistoryEntry, ...]


@dataclass(frozen=True, kw_only=True)
class RecruiterMessage(Record):
    application_id: str
    job_id: str
    kind: Literal["acknowledgement", "interview", "offer", "rejection", "follow_up"]
    sent_at: str
    text: str


@dataclass(frozen=True, kw_only=True)
class ScenarioInput(Record):
    schema_version: Literal["careerlab-input-v1"]
    as_of: str
    companies: tuple[Company, ...]
    jobs: tuple[JobPosting, ...]
    candidate: Candidate
    cvs: tuple[CVVariant, ...]
    draft_assertions: tuple[DraftAssertion, ...]
    applications: tuple[Application, ...]
    messages: tuple[RecruiterMessage, ...]


@dataclass(frozen=True, kw_only=True)
class RequirementOracle(Record):
    job_id: str
    subject: Subject
    minimum: int
    unit: Unit
    priority: Literal["essential", "preferred", "ambiguous"]
    source_quote: str
    assessment: Literal["supported", "partial", "gap", "unknown", "conflict"]
    claim_ids: tuple[str, ...]
    declared_shortfall: bool
    rationale: str


@dataclass(frozen=True, kw_only=True)
class FutureOutcome(Record):
    application_id: str
    state: Literal["interview", "offer", "closed"]
    occurs_at: str
    explanation: str


@dataclass(frozen=True, kw_only=True)
class GroundTruth(Record):
    schema_version: Literal["careerlab-oracle-v1"]
    scenario_id: str
    coverage: Coverage
    requirements: tuple[RequirementOracle, ...]
    acceptable_cv_ids: tuple[str, ...]
    cv_rationale: str
    blocked_draft_ids: tuple[str, ...]
    duplicate_job_groups: tuple[tuple[str, ...], ...]
    expected_error_codes: tuple[str, ...]
    future_outcomes: tuple[FutureOutcome, ...]
    secret_canary: str | None


@dataclass(frozen=True, kw_only=True)
class SplitMembership(Record):
    scenario_id: str
    split: Split
    coverage: Coverage
    company_lineages: tuple[str, ...]
    candidate_lineages: tuple[str, ...]
    evidence_lineages: tuple[str, ...]
    cv_lineages: tuple[str, ...]
    application_lineages: tuple[str, ...]
    template_lineages: tuple[str, ...]
    normalized_content_hash: str


@dataclass(frozen=True, kw_only=True)
class FixturePair:
    """Authoring-only bundle; never an observable serialization entry point."""

    inputs: ScenarioInput
    oracle: GroundTruth
    membership: SplitMembership
