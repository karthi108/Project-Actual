"""Versioned source discovery and deterministic composition, without live inference."""

import asyncio
import json

import pytest
from pydantic import ValidationError

from actual.capabilities.job_requirements import (
    JOB_REQUIREMENTS,
    ExtractionInput,
    ExtractionOutput,
    SourceSegment,
)
from actual.career.jobs import Job
from actual.career.requirements import InterpretedRequirement
from actual.career.snapshot import CareerSnapshot
from actual.careerlab.generator import generate_inputs
from actual.careerlab_bridge import ImportContext, map_observable
from actual.core.primitives import ActorId, WorkspaceId, canonical_bytes
from actual.job_intelligence.errors import IntelligenceFailure
from actual.job_intelligence.service import IntelligenceResult, JobIntelligence
from actual.models.contracts import (
    GenerationSettings,
    PreparedInference,
    ProviderIdentity,
    ProviderReply,
)
from actual.models.errors import FailureCode, ModelFailure
from actual.models.gateway import ModelGateway, canonical_json


def world(case: int = 0) -> CareerSnapshot:
    return map_observable(
        generate_inputs()[case],
        ImportContext(
            workspace_id=WorkspaceId("workspace_" + "1" * 32), actor_id=ActorId("actor_" + "2" * 32)
        ),
    )


def output(*source_ids: int) -> dict[str, object]:
    return {"schema_version": "actual-job-source-output-v2", "source_ids": list(source_ids)}


class FakeExtractionProvider:
    def __init__(self, content: str | None = None, failure: ModelFailure | None = None) -> None:
        self.identity = ProviderIdentity(
            provider="fake", model="synthetic-model", endpoint="http://127.0.0.1:11434"
        )
        self.settings = GenerationSettings(max_output_tokens=512)
        self.content = canonical_json(output(1)) if content is None else content
        self.failure = failure
        self.requests: list[PreparedInference] = []

    async def infer(self, request: PreparedInference) -> ProviderReply:
        self.requests.append(request)
        if self.failure is not None:
            raise self.failure
        return ProviderReply(
            content=self.content, model=self.identity.model, model_digest=None, server_version=None
        )


def service(provider: FakeExtractionProvider) -> JobIntelligence:
    return JobIntelligence(ModelGateway(provider, capabilities=(JOB_REQUIREMENTS,)))


def assess(
    provider: FakeExtractionProvider, source: CareerSnapshot | None = None
) -> IntelligenceResult:
    source = world() if source is None else source
    return asyncio.run(service(provider).assess(source.jobs[0], source.profile))


def assess_text(provider: FakeExtractionProvider, text: str) -> tuple[Job, IntelligenceResult]:
    source = world()
    job = source.jobs[0].model_copy(update={"text": text})
    return job, asyncio.run(service(provider).assess(job, source.profile))


def test_source_and_concept_are_bound_to_current_job_and_evidence() -> None:
    source, provider = world(), FakeExtractionProvider()
    before = canonical_bytes(source)
    result = assess(provider, source)
    assert type(result) is IntelligenceResult
    assert result.metadata.capability == "job_requirement_extraction:v2"
    assert result.metadata.schema_version == "actual-job-source-output-v2"
    assert result.metadata.settings.max_output_tokens == 512
    assert result.metadata.proposal_only is True
    row = result.assessment.rows[0]
    assert type(row.requirement) is InterpretedRequirement
    assert row.requirement.assertion.subject == "python"
    assert row.requirement.assertion.value == 2
    assert row.requirement.origin == "deterministic_proposal" and row.requirement.review is None
    assert row.status == "supported" and row.claim_refs and row.evidence_refs
    assert row.requirement.job_digest == source.jobs[0].content_digest
    assert (
        row.requirement.source_quote
        == source.jobs[0].text[row.requirement.source_start : row.requirement.source_end]
    )
    assert (
        row.requirement.term
        == source.jobs[0].text[row.requirement.concept_start : row.requirement.concept_end]
    )
    assert result.trace.model_source_ids == (1,)
    assert result.trace.deterministic_source_ids == (1, 2, 3, 4, 5, 6)
    assert result.assessment.profile_digest == source.profile.content_digest
    assert canonical_bytes(source) == before
    assert source.jobs[0].text not in repr(result)
    assert len(provider.requests) == 1


def test_explicit_recovery_is_separately_measured_from_empty_model_discovery() -> None:
    result = assess(FakeExtractionProvider(canonical_json(output())))
    assert result.trace.model_source_ids == ()
    assert result.trace.deterministic_source_ids == (1, 2, 3, 4, 5, 6)
    assert [row.requirement.assertion.subject for row in result.assessment.rows] == [
        "python",
        "fastapi",
        "azure",
        "french",
        "experience",
        "llm_integration",
    ]
    assert [row.status for row in result.assessment.rows] == [
        "supported",
        "supported",
        "unknown",
        "unknown",
        "gap",
        "supported",
    ]
    assert [row.requirement.assertion.value for row in result.assessment.rows] == [
        2,
        2,
        3,
        4,
        60,
        2,
    ]
    assert result.assessment.rows[2].declared_shortfall is True
    assert result.assessment.rows[3].declared_shortfall is True
    assert result.assessment.rows[4].observed_value == 12


def test_narrative_empty_discovery_has_no_score_or_recommendation() -> None:
    _, result = assess_text(
        FakeExtractionProvider(canonical_json(output())),
        "SYNTHETIC POSTING. The team maintains inventory software.",
    )
    assert result.assessment.rows == ()
    assert result.trace.model_source_ids == result.trace.deterministic_source_ids == ()
    assert not hasattr(result.assessment, "score")
    assert not hasattr(result.assessment, "recommendation")


def test_semantic_discovery_retains_uncertain_meaning_without_parser_credit() -> None:
    job, result = assess_text(
        FakeExtractionProvider(), "SYNTHETIC POSTING. French fluency welcomed."
    )
    assert result.trace.deterministic_source_ids == ()
    assert result.trace.model_source_ids == (1,)
    row = result.assessment.rows[0]
    assert row.requirement.priority == "ambiguous"
    assert row.requirement.resolution == "abstained"
    assert row.requirement.reason == "unknown_language_level"
    assert row.requirement.assertion is None and row.status == "unknown"
    assert row.requirement.extraction_method == "qwen"
    assert (
        row.requirement.source_quote
        == job.text[row.requirement.source_start : row.requirement.source_end]
    )
    assert not row.evidence_refs


def test_azure_ambiguity_keeps_independent_python_decision() -> None:
    result = assess(FakeExtractionProvider(canonical_json(output(1, 2))), world(5))
    assert len(result.assessment.rows) == 2
    python, azure = result.assessment.rows
    assert python.status == "supported"
    assert azure.requirement.priority == "ambiguous"
    assert not any(unit.failure_code for unit in result.trace.units)


@pytest.mark.parametrize(
    "content",
    [
        "not JSON",
        "",
        "{}",
        '{"schema_version":"actual-job-source-output-v2"}',
        '{"schema_version":"actual-job-source-output-v2","source_ids":[',
        canonical_json({**output(), "evidence": []}),
        canonical_json({**output(), "source_ids": [True]}),
        canonical_json({**output(), "source_ids": ["1"]}),
        canonical_json(output(-1)),
        canonical_json(output(32)),
        canonical_json(output(1, 1)),
        canonical_json(output(2, 1)),
        canonical_json(output(*range(33))),
        canonical_json({"schema_version": "actual-job-requirements-output-v1", "requirements": []}),
    ],
)
def test_malformed_output_fails_closed_once(content: str) -> None:
    provider = FakeExtractionProvider(content)
    with pytest.raises(ModelFailure) as captured:
        assess(provider)
    assert captured.value.code == FailureCode.INVALID_OUTPUT
    assert str(captured.value) == "invalid_output"
    assert len(provider.requests) == 1


def test_nonexistent_source_id_cannot_bind_a_posting() -> None:
    provider = FakeExtractionProvider(canonical_json(output(31)))
    with pytest.raises(IntelligenceFailure) as captured:
        assess(provider)
    assert captured.value.code.value == "invalid_requirement"
    assert len(provider.requests) == 1


def test_spans_count_characters_while_input_bounds_count_utf8() -> None:
    quote = "Python at working level is essential."
    prefix = "SYNTHETIC POSTING. équipe café. "
    job, result = assess_text(FakeExtractionProvider(canonical_json(output(2))), prefix + quote)
    requirement = result.assessment.rows[0].requirement
    assert requirement.source_start == len(prefix)
    assert requirement.source_start != len(prefix.encode("utf-8"))
    assert job.text[requirement.source_start : requirement.source_end] == quote
    assert job.text[requirement.concept_start : requirement.concept_end] == "Python"


def test_model_timeout_propagates_without_faking_deterministic_success() -> None:
    source, provider = world(), FakeExtractionProvider(failure=ModelFailure(FailureCode.TIMEOUT))
    before = canonical_bytes(source)
    with pytest.raises(ModelFailure) as captured:
        assess(provider, source)
    assert captured.value.code == FailureCode.TIMEOUT
    assert len(provider.requests) == 1
    assert canonical_bytes(source) == before


@pytest.mark.parametrize("synthetic", [False, 1, "true", None])
def test_synthetic_marker_requires_exact_true(synthetic: object) -> None:
    with pytest.raises(ValidationError):
        ExtractionInput.model_validate(
            {"synthetic": synthetic, "segments": (SourceSegment(id=0, text="Python required."),)}
        )


def test_input_boundary_never_truncates() -> None:
    assert ExtractionInput(synthetic=True, segments=(SourceSegment(id=0, text="x" * 1024),))
    assert ExtractionInput(synthetic=True, segments=(SourceSegment(id=0, text="é" * 512),))
    for text in ("x" * 1025, "é" * 513, "  ", "\ud800"):
        with pytest.raises((ValidationError, UnicodeError)):
            ExtractionInput(synthetic=True, segments=(SourceSegment(id=0, text=text),))
    source, provider = world(), FakeExtractionProvider()
    long_job = source.jobs[0].model_copy(update={"text": "x" * 1025})
    with pytest.raises(IntelligenceFailure):
        asyncio.run(service(provider).assess(long_job, source.profile))
    assert provider.requests == []


@pytest.mark.parametrize("ids", [(1,), (0, 0), (1, 0)])
def test_source_ids_are_contiguous_and_ordered(ids: tuple[int, ...]) -> None:
    with pytest.raises(ValidationError):
        ExtractionInput(
            synthetic=True,
            segments=tuple(SourceSegment(id=index, text="sentence") for index in ids),
        )


def test_closed_versioned_immutable_output() -> None:
    parsed = ExtractionOutput.model_validate_json(json.dumps(output(1, 2)))
    assert parsed.source_ids == (1, 2)
    for change in ({"schema_version": "future"}, {"priority": "essential"}, {"claim_ids": []}):
        with pytest.raises(ValidationError):
            ExtractionOutput.model_validate_json(json.dumps({**output(), **change}))
    with pytest.raises(ValidationError):
        parsed.source_ids = ()


def test_unregistered_capability_cannot_call_provider() -> None:
    from actual.capabilities.probe import PROBE

    provider = FakeExtractionProvider()
    gateway = ModelGateway(provider, capabilities=(PROBE,))
    with pytest.raises(ModelFailure) as captured:
        asyncio.run(
            gateway.run(
                JOB_REQUIREMENTS,
                ExtractionInput(synthetic=True, segments=(SourceSegment(id=0, text="Python"),)),
            )
        )
    assert captured.value.code == FailureCode.UNSUPPORTED_CAPABILITY
    assert provider.requests == []
