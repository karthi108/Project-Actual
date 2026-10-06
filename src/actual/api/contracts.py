"""HTTP envelopes reuse safe accepted records without exposing storage projections."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from actual.career.applications import Application
from actual.career.jobs import Job
from actual.career.snapshot import CareerSnapshot
from actual.profile.contracts import Profile
from actual.profile.projection import EvidenceBackedProfileView

type Generation = Annotated[int, Field(strict=True, ge=1, le=9223372036854775807)]


class ApiModel(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid", hide_input_in_errors=True)
    schema_version: Literal["actual-api-v1"] = "actual-api-v1"


class CareerView(ApiModel):
    generation: Generation
    snapshot: CareerSnapshot


class JobView(ApiModel):
    generation: Generation
    job: Job


class ProfileView(ApiModel):
    generation: Generation
    profile: Profile


class EvidenceProfileResponse(ApiModel):
    generation: Generation
    profile: EvidenceBackedProfileView


class ApplicationView(ApiModel):
    generation: Generation
    application: Application


class Page[T](ApiModel):
    items: tuple[T, ...]
    offset: int
    limit: int
    total: int
    next_offset: int | None


class StatePage[T](Page[T]):
    generation: Generation


class ErrorDetail(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)
    code: str
    message: str


class ErrorResponse(ApiModel):
    error: ErrorDetail
    request_id: str


class Health(ApiModel):
    status: Literal["live", "ready"]
    mode: Literal["synthetic-development"] = "synthetic-development"
