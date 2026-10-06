"""Transient atomic interpretations retain source facts separately from meaning.

The accepted profile assertion vocabulary remains unchanged. Scoped experience
cannot become a generic duration assertion merely because its number is explicit.
"""

from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from actual.core.primitives import (
    Classification,
    Contract,
    Digest,
    JobId,
    RequirementId,
    Revision,
    Text,
    WorkspaceId,
    content_digest,
)
from actual.profile.contracts import Assertion

type Priority = Literal["essential", "preferred", "ambiguous"]
type CanonicalConcept = Literal[
    "python", "fastapi", "azure", "llm_integration", "french", "experience"
]
type ExtractionMethod = Literal["deterministic", "qwen"]
type ExperienceScope = Literal[
    "generic",
    "legacy_backend",
    "professional",
    "internship",
    "academic",
    "personal_project",
    "open_source",
    "unknown",
]
type AbstentionReason = Literal[
    "unknown_term",
    "ambiguous_alias",
    "unknown_skill_level",
    "unknown_language_level",
    "unknown_experience_duration",
    "unsupported_experience_scope",
    "unsupported_version_constraint",
    "unsupported_constraint",
    "negated_requirement",
]


class RequirementConstraints(Contract):
    """Only explicit syntax is recorded; this structure does not establish support."""

    kind: Literal["skill", "language", "experience"] | None = None
    unit: Literal["skill_level", "cefr_level", "months"] | None = None
    value: Annotated[int, Field(strict=True, ge=1, le=600)] | None = None
    comparator: Literal["minimum", "unsupported"] | None = None
    experience_scope: ExperienceScope | None = None

    @model_validator(mode="after")
    def bounded_constraint(self) -> Self:
        scopes = {
            "skill": ("skill_level", 3),
            "language": ("cefr_level", 6),
            "experience": ("months", 600),
        }
        if self.kind is None:
            if any(
                value is not None
                for value in (self.unit, self.value, self.comparator, self.experience_scope)
            ):
                raise ValueError("Unknown kinds cannot manufacture typed constraints")
            return self
        unit, maximum = scopes[self.kind]
        if self.unit != unit or self.value is not None and self.value > maximum:
            raise ValueError("Explicit constraints must preserve kind and bounded unit")
        if self.kind != "experience" and self.experience_scope is not None:
            raise ValueError("Only duration requirements have experience scope")
        if self.kind == "experience" and self.experience_scope is None:
            raise ValueError("Duration constraints retain explicit or unknown experience scope")
        if self.value is not None and self.comparator is None:
            raise ValueError("A parsed threshold retains its comparator")
        return self


class InterpretedRequirement(Contract):
    """Atomic source identity and conservative interpretation, never domain truth."""

    id: RequirementId
    workspace_id: WorkspaceId
    revision: Revision
    classification: Classification
    job_id: JobId
    job_revision: Revision
    job_digest: Digest
    priority: Priority
    source_start: Annotated[int, Field(strict=True, ge=0, le=12000)]
    source_end: Annotated[int, Field(strict=True, gt=0, le=12000)]
    source_quote: Text
    term: Annotated[str, Field(strict=True, min_length=1, max_length=128)]
    concept_start: Annotated[int, Field(strict=True, ge=0, le=12000)]
    concept_end: Annotated[int, Field(strict=True, gt=0, le=12000)]
    canonical_concept: CanonicalConcept | None
    assertion: Assertion | None
    resolution: Literal["resolved", "abstained"]
    reason: AbstentionReason | None
    constraints: RequirementConstraints
    extraction_method: ExtractionMethod
    origin: Literal["deterministic_proposal", "ai_proposal"]
    review: None = None

    @model_validator(mode="after")
    def source_and_interpretation(self) -> Self:
        if (
            self.source_end <= self.source_start
            or self.source_end - self.source_start != len(self.source_quote)
            or not self.source_start <= self.concept_start < self.concept_end <= self.source_end
            or self.term not in self.source_quote
            or self.source_quote[
                self.concept_start - self.source_start : self.concept_end - self.source_start
            ]
            not in self.term
        ):
            raise ValueError("Atomic interpretation must retain exact nonempty source extents")
        local_start = self.concept_start - self.source_start
        local_end = self.concept_end - self.source_start
        if (
            local_start > 0
            and (
                self.source_quote[local_start - 1].isalnum()
                or self.source_quote[local_start - 1] == "_"
            )
            or local_end < len(self.source_quote)
            and (self.source_quote[local_end].isalnum() or self.source_quote[local_end] == "_")
        ):
            raise ValueError("Atomic concept spans cannot clip a source token")
        expected_origin = (
            "deterministic_proposal" if self.extraction_method == "deterministic" else "ai_proposal"
        )
        if self.origin != expected_origin:
            raise ValueError("Extraction provenance cannot silently change")
        if self.canonical_concept is not None:
            expected_kind = (
                "language"
                if self.canonical_concept == "french"
                else "experience"
                if self.canonical_concept == "experience"
                else "skill"
            )
            if self.constraints.kind != expected_kind:
                raise ValueError("Canonical concept must preserve its accepted assertion kind")
        if self.resolution == "abstained":
            if self.assertion is not None or self.reason is None:
                raise ValueError("Abstention retains its reason without inventing an assertion")
            return self
        if self.assertion is None or self.canonical_concept is None or self.reason is not None:
            raise ValueError("Resolved interpretation requires explicit canonical assertion")
        if self.assertion.subject != self.canonical_concept or (
            self.constraints.kind,
            self.constraints.unit,
            self.constraints.value,
            self.constraints.comparator,
        ) != (self.assertion.kind, self.assertion.unit, self.assertion.value, "minimum"):
            raise ValueError("Assertion cannot differ from explicit interpreted constraints")
        if self.assertion.kind == "experience" and self.constraints.experience_scope not in (
            "generic",
            "legacy_backend",
        ):
            raise ValueError("Scoped experience cannot become a generic reviewed duration")
        return self

    @property
    def content_digest(self) -> str:
        return content_digest(self.model_dump(mode="json", exclude={"review"}))
