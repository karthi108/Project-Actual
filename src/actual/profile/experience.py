"""Source-reviewed experience context, never an accumulated tenure estimate."""

from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from actual.core.primitives import Contract, Instant

type ExperienceCategory = Literal[
    "professional_employment",
    "internship",
    "academic",
    "personal_project",
    "open_source",
    "unknown",
]


class ExperienceContext(Contract):
    """Explicit source metadata. Missing activity dates remain missing."""

    context_version: Literal["actual-experience-context-v1"]
    category: ExperienceCategory
    started_at: Instant | None = None
    ended_at: Instant | None = None
    ongoing: Annotated[bool, Field(strict=True)] | None = None

    @model_validator(mode="after")
    def temporal_consistency(self) -> Self:
        if (
            self.started_at is not None
            and self.ended_at is not None
            and self.ended_at < self.started_at
        ):
            raise ValueError("Experience activity cannot end before it starts")
        if self.ongoing is True and self.ended_at is not None:
            raise ValueError("An ongoing activity cannot have an end instant")
        return self
