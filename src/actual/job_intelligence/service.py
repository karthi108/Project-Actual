"""Read-only synthetic discovery, interpretation and evidence stages."""

from dataclasses import dataclass, field, replace

from pydantic import ValidationError

from actual.capabilities.job_requirements import JOB_REQUIREMENTS, ExtractionInput, SourceSegment
from actual.career.assessments import JobFitAssessment
from actual.career.jobs import Job
from actual.career.requirements import ExtractionMethod, InterpretedRequirement
from actual.models.contracts import InferenceMetadata
from actual.models.gateway import ModelGateway
from actual.profile.contracts import Profile

from .errors import IntelligenceFailure
from .extraction import (
    DocumentSegment,
    ExtractedAtom,
    explicit_sources,
    instruction_like,
    segment_document,
    source_atoms,
)
from .matching import checked_profile, match_requirements
from .normalize import checked_job, normalize_requirement, source_context, source_priority


@dataclass(frozen=True, kw_only=True)
class UnitTrace:
    source_id: int
    atom: ExtractedAtom | None = field(default=None, repr=False)
    requirement: InterpretedRequirement | None = field(default=None, repr=False)
    failure_stage: str | None = None
    failure_code: str | None = None


@dataclass(frozen=True, kw_only=True)
class IntelligenceTrace:
    segments: tuple[DocumentSegment, ...] = field(repr=False)
    model_source_ids: tuple[int, ...]
    deterministic_source_ids: tuple[int, ...]
    units: tuple[UnitTrace, ...] = field(repr=False)


@dataclass(frozen=True, kw_only=True)
class IntelligenceResult:
    assessment: JobFitAssessment = field(repr=False)
    metadata: InferenceMetadata
    trace: IntelligenceTrace = field(repr=False)


class JobIntelligence:
    """The model discovers source; deterministic stages retain fact/evidence boundaries."""

    def __init__(self, gateway: ModelGateway) -> None:
        self._gateway = gateway

    async def assess(self, job: Job, profile: Profile) -> IntelligenceResult:
        if type(job) is not Job or type(profile) is not Profile:
            raise IntelligenceFailure("input_rejected")
        try:
            source = checked_job(job)
            candidate = checked_profile(profile)
            if (
                source.classification != "synthetic"
                or candidate.classification != "synthetic"
                or source.workspace_id != candidate.workspace_id
            ):
                raise IntelligenceFailure("input_rejected")
            segments = segment_document(source)
            request = ExtractionInput(
                synthetic=True,
                segments=tuple(SourceSegment(id=item.id, text=item.text) for item in segments),
            )
        except (ValidationError, ValueError, TypeError, UnicodeError, RecursionError):
            raise IntelligenceFailure("input_rejected") from None

        # Accepted provider failures still propagate explicitly; no silent retry/repair.
        proposal = await self._gateway.run(JOB_REQUIREMENTS, request)
        selected = proposal.value.source_ids
        if any(index >= len(segments) for index in selected):
            raise IntelligenceFailure("invalid_requirement")
        explicit = explicit_sources(segments)
        units = []
        requirements = []
        for index in sorted(set(selected) | set(explicit)):
            segment = segments[index]
            if segment.role_context or instruction_like(segment.text):
                units.append(
                    UnitTrace(
                        source_id=index,
                        failure_stage="extraction",
                        failure_code="unsafe_source",
                    )
                )
                continue
            method: ExtractionMethod = "deterministic" if index in explicit else "qwen"
            for atom in source_atoms(segment, method=method):
                left, right, context = source_context(
                    source.text, atom.source_start, atom.source_end
                )
                atom = replace(atom, quote=context, source_start=left, source_end=right)
                try:
                    priority = source_priority(atom.quote)
                except IntelligenceFailure as failure:
                    units.append(
                        UnitTrace(
                            source_id=index,
                            atom=atom,
                            failure_stage="importance",
                            failure_code=failure.code.value,
                        )
                    )
                    continue
                try:
                    requirement = normalize_requirement(
                        source,
                        quote=atom.quote,
                        term=atom.term,
                        priority=priority,
                        method=method,
                    )
                    requirements.append(requirement)
                    units.append(UnitTrace(source_id=index, atom=atom, requirement=requirement))
                except IntelligenceFailure as failure:
                    # Preserve local rejection, without deleting independent genuine units.
                    units.append(
                        UnitTrace(
                            source_id=index,
                            atom=atom,
                            failure_stage="normalization",
                            failure_code=failure.code.value,
                        )
                    )
        if len(requirements) > 8:
            raise IntelligenceFailure("invalid_assessment")
        assessment = match_requirements(source, candidate, tuple(requirements))
        return IntelligenceResult(
            assessment=assessment,
            metadata=proposal.metadata,
            trace=IntelligenceTrace(
                segments=segments,
                model_source_ids=selected,
                deterministic_source_ids=explicit,
                units=tuple(units),
            ),
        )
