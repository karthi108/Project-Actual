"""Closed intent DTOs: callers cannot set ownership, verification or history."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from actual.career.applications import ApplicationState
from actual.core.primitives import (
    ApplicationId,
    ClaimId,
    CompanyId,
    EvidenceId,
    Instant,
    JobId,
    Label,
    OpportunityId,
    ProfileId,
    SourceReference,
    Text,
)
from actual.profile.contracts import Assertion

type ExpectedGeneration = Annotated[int, Field(strict=True, ge=1, le=9223372036854775806)]
type InitialGeneration = Annotated[int, Field(strict=True, ge=0, le=0)]
type EvidenceSourceKind = Literal[
    "user_report", "project_artifact", "imported_document", "ai_proposal", "synthetic_fixture"
]


class Command(BaseModel):
    model_config = ConfigDict(
        strict=True,
        extra="forbid",
        frozen=True,
        validate_default=True,
        revalidate_instances="always",
        hide_input_in_errors=True,
    )
    schema_version: Literal["actual-api-v1"] = "actual-api-v1"


class CompanyInput(Command):
    id: CompanyId
    name: Label
    context: Text


class ManualJob(Command):
    id: JobId
    opportunity_id: OpportunityId
    company: CompanyInput
    title: Label
    text: Text
    source_reference: SourceReference
    posted_at: Instant


class InitialProfile(Command):
    id: ProfileId
    name: Label


class InitializeCareer(Command):
    expected_generation: InitialGeneration
    profile: InitialProfile
    job: ManualJob


class AddJob(Command):
    expected_generation: ExpectedGeneration
    job: ManualJob


class CreateClaim(Command):
    expected_generation: ExpectedGeneration
    id: ClaimId
    assertion: Assertion
    text: Text


class AttachEvidence(Command):
    expected_generation: ExpectedGeneration
    id: EvidenceId
    claim_id: ClaimId
    assertion: Assertion
    relation: Literal["supports", "contradicts"]
    source_kind: EvidenceSourceKind
    source_reference: SourceReference
    excerpt: Text
    collected_at: Instant


class CreateApplication(Command):
    expected_generation: ExpectedGeneration
    id: ApplicationId
    job_id: JobId
    occurred_at: Instant


class TransitionApplication(Command):
    expected_generation: ExpectedGeneration
    state: ApplicationState
    occurred_at: Instant
    external_manual: Annotated[bool, Field(strict=True)] = False
