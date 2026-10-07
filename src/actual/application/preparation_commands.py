"""Closed preparation intents; no caller authority, prose or external destination."""

from typing import Annotated, Literal

from pydantic import BeforeValidator, Field

from actual.career.preparation_context import MaterialKind
from actual.core.primitives import ClaimId, CVId, Digest, DraftId, JobId, Label, Revision, Text

from .commands import Command, ExpectedGeneration


def _json_array(value: object) -> object:
    """FastAPI validates decoded JSON in strict Python mode; admit only JSON arrays."""
    return tuple(value) if type(value) is list else value


class CreateCV(Command):
    expected_generation: ExpectedGeneration
    id: CVId
    name: Label
    claim_ids: Annotated[
        tuple[ClaimId, ...], BeforeValidator(_json_array), Field(min_length=1, max_length=64)
    ]


class SourceSelection(Command):
    quote: Text
    term: Annotated[str, Field(strict=True, min_length=1, max_length=128)]
    priority: Literal["essential", "preferred", "ambiguous"]


class CompareCVs(Command):
    expected_generation: ExpectedGeneration
    job_id: JobId
    selections: Annotated[
        tuple[SourceSelection, ...], BeforeValidator(_json_array), Field(max_length=8)
    ] = ()


class PrepareDraft(Command):
    expected_generation: ExpectedGeneration
    id: DraftId
    job_id: JobId
    cv_id: CVId
    material_kind: MaterialKind


class ReviseDraft(Command):
    expected_generation: ExpectedGeneration
    expected_revision: Revision
    expected_digest: Digest
    job_id: JobId
    cv_id: CVId
    material_kind: MaterialKind


class ReviewDraft(Command):
    expected_generation: ExpectedGeneration
    expected_revision: Revision
    expected_digest: Digest
    decision: Literal["accepted", "rejected"]
