"""Stage faults cannot disappear behind canonical alignment or existing IDs."""

import json
from copy import copy
from dataclasses import replace
from pathlib import Path
from typing import Any
from uuid import UUID, uuid5

import pytest
import test_evidence_matching as evidence_helpers

from actual.careerlab_bridge import ImportContext, map_observable
from actual.core.primitives import ActorId, JobId, OpportunityId, WorkspaceId
from actual.evaluation.intelligence_v2 import (
    CaseResult,
    EvaluationCase,
    SourceGoldUnit,
    evaluate_results,
    load_careerlab_cases,
    load_safety_cases,
    load_supplemental_cases,
)
from actual.job_intelligence.development import load_development
from actual.job_intelligence.extraction import ExtractedAtom, segment_document
from actual.job_intelligence.matching import match_requirements
from actual.job_intelligence.normalize import normalize_requirement
from actual.job_intelligence.service import IntelligenceTrace, UnitTrace
from actual.profile.contracts import Assertion, claim_ref, evidence_ref

ROOT = Path(__file__).resolve().parents[2]
CONTEXT = ImportContext(
    workspace_id=WorkspaceId("workspace_" + "6" * 32), actor_id=ActorId("actor_" + "6" * 32)
)
NAMESPACE = UUID("9d139abb-f1e0-4a1b-bc05-5f2d8a5cb3dd")


def fault_copy(value: Any, *, update: dict[str, Any]) -> Any:
    """Evaluator fault injection only; no production validation is bypassed."""
    changed = copy(value)
    for field, content in update.items():
        object.__setattr__(changed, field, content)
    return changed


@pytest.fixture(scope="module")
def cases() -> tuple[EvaluationCase, ...]:
    worlds = {value.id: map_observable(value, CONTEXT) for value in load_development()[:7]}
    return load_careerlab_cases(
        {key: world.jobs[0] for key, world in worlds.items()},
        {key: world.profile for key, world in worlds.items()},
    )


def direct_result(case: EvaluationCase) -> CaseResult:
    """Deterministic test/component input, not a fake live model acceptance."""
    segments = segment_document(case.job)
    units = []
    for gold in case.units:
        quote = case.job.text[gold.source_start : gold.source_end]
        term = case.job.text[gold.head_start : gold.head_end]
        source_id = next(
            source.id
            for source in segments
            if source.start <= gold.source_start and source.end >= gold.source_end
        )
        atom = ExtractedAtom(
            source_id,
            quote,
            term,
            gold.source_start,
            gold.source_end,
            gold.head_start,
            gold.head_end,
            "qwen",
        )
        requirement = normalize_requirement(
            case.job, quote=quote, term=term, priority=gold.priority, method="qwen"
        )
        units.append(UnitTrace(source_id=source_id, atom=atom, requirement=requirement))
    assessment = match_requirements(
        case.job, case.profile, tuple(unit.requirement for unit in units)
    )
    trace = IntelligenceTrace(
        segments=segments,
        model_source_ids=tuple(sorted({u.source_id for u in units})),
        deterministic_source_ids=(),
        units=tuple(units),
    )
    return CaseResult(case_id=case.case_id, assessment=assessment, trace=trace)


def changed_unit(result: CaseResult, index: int, updates: dict[str, Any]) -> CaseResult:
    unit = result.trace.units[index]
    requirement = unit.requirement.model_copy(update=updates)
    units = list(result.trace.units)
    units[index] = replace(unit, requirement=requirement)
    rows = list(result.assessment.rows)
    rows[index] = fault_copy(rows[index], update={"requirement": requirement})
    return replace(
        result,
        trace=replace(result.trace, units=tuple(units)),
        assessment=fault_copy(result.assessment, update={"rows": tuple(rows)}),
    )


def test_24_authored_units_have_independent_stage_counts(cases: tuple[EvaluationCase, ...]) -> None:
    metrics = evaluate_results(cases, tuple(direct_result(case) for case in cases))
    assert metrics["gold_units"] == 24
    assert metrics["raw_qwen_extraction"]["tp"] == metrics["hybrid_extraction"]["tp"] == 24
    for task in ("importance", "normalization", "evidence_matching", "fit"):
        assert metrics[task]["correct"] == metrics[task]["total"] == 24
    assert metrics["fit"]["classes"]["partial"]["support"] == 0
    assert not metrics["failures"]


def test_missing_unit_reports_extraction_without_hiding_other_stages(
    cases: tuple[EvaluationCase, ...],
) -> None:
    case = cases[2]
    original = direct_result(case)
    changed = replace(
        original,
        trace=replace(original.trace, units=original.trace.units[1:]),
        assessment=fault_copy(original.assessment, update={"rows": original.assessment.rows[1:]}),
    )
    metrics = evaluate_results((case,), (changed,))
    assert metrics["raw_qwen_extraction"]["tp"] == 2
    assert metrics["hybrid_extraction"]["tp"] == 1
    assert metrics["hybrid_extraction"]["fn"] == 1
    assert metrics["fit"]["total"] == 2
    assert metrics["cases"][0]["units"][0]["root_stage"] == "EXTRACTION"


def test_deterministic_rescue_does_not_hide_a_raw_model_discovery_miss(
    cases: tuple[EvaluationCase, ...],
) -> None:
    case = cases[2]
    original = direct_result(case)
    changed = replace(
        original,
        trace=replace(
            original.trace,
            model_source_ids=(),
            deterministic_source_ids=original.trace.model_source_ids,
        ),
    )
    metrics = evaluate_results((case,), (changed,))
    assert metrics["raw_qwen_extraction"]["fn"] == 2
    assert metrics["hybrid_extraction"]["tp"] == metrics["fit"]["correct"] == 2
    assert metrics["failure_code_counts"]["missed_model_source_requirement"] == 2
    assert all(
        not unit["raw_model_selected"]
        and unit["deterministic_selected"]
        and unit["root_stage"] is None
        for unit in metrics["cases"][0]["units"]
    )


def test_importance_error_is_measured_without_conflating_normalization(
    cases: tuple[EvaluationCase, ...],
) -> None:
    case = cases[2]
    metrics = evaluate_results(
        (case,), (changed_unit(direct_result(case), 0, {"priority": "preferred"}),)
    )
    assert metrics["importance"]["correct"] == 1
    assert metrics["normalization"]["correct"] == metrics["fit"]["correct"] == 2
    assert metrics["cases"][0]["units"][0]["root_stage"] == "IMPORTANCE_CLASSIFICATION"


def test_wrong_threshold_localizes_normalization_and_downstream_cascades(
    cases: tuple[EvaluationCase, ...],
) -> None:
    case = cases[2]
    original = direct_result(case)
    request = original.trace.units[0].requirement
    changed = changed_unit(
        original,
        0,
        {
            "assertion": Assertion(kind="skill", subject="python", unit="skill_level", value=3),
            "constraints": request.constraints.model_copy(update={"value": 3}),
        },
    )
    metrics = evaluate_results((case,), (changed,))
    assert metrics["normalization"]["correct"] == 1
    assert metrics["normalization"]["unsafe_count"] == 1
    assert metrics["cases"][0]["units"][0]["root_stage"] == "NORMALIZATION"
    assert any(
        row["stage"] == "FIT_DECISION" and row["caused_by"] == "NORMALIZATION"
        for row in metrics["failures"]
    )


def test_wrong_concept_with_real_scoped_evidence_is_not_evidence_fabrication(
    cases: tuple[EvaluationCase, ...],
) -> None:
    case = cases[2]
    original = direct_result(case)
    changed = changed_unit(
        original,
        0,
        {
            "canonical_concept": "fastapi",
            "assertion": Assertion(kind="skill", subject="fastapi", unit="skill_level", value=2),
        },
    )
    rows = list(changed.assessment.rows)
    rows[0] = fault_copy(
        rows[0],
        update={
            "claim_refs": rows[1].claim_refs,
            "evidence_refs": rows[1].evidence_refs,
            "observed_value": rows[1].observed_value,
        },
    )
    changed = replace(
        changed, assessment=fault_copy(changed.assessment, update={"rows": tuple(rows)})
    )
    metrics = evaluate_results((case,), (changed,))
    assert metrics["normalization"]["correct"] == 1
    assert metrics["evidence_safety_violation_count"] == 0
    assert metrics["cases"][0]["units"][0]["root_stage"] == "NORMALIZATION"
    assert any(
        row["code"] == "evidence_selection_cascade" and row["caused_by"] == "NORMALIZATION"
        for row in metrics["failures"]
    )


def test_existing_wrong_subject_refs_are_not_positive_support(
    cases: tuple[EvaluationCase, ...],
) -> None:
    case = cases[2]
    original = direct_result(case)
    rows = list(original.assessment.rows)
    rows[0] = fault_copy(
        rows[0], update={"claim_refs": rows[1].claim_refs, "evidence_refs": rows[1].evidence_refs}
    )
    changed = replace(
        original, assessment=fault_copy(original.assessment, update={"rows": tuple(rows)})
    )
    metrics = evaluate_results((case,), (changed,))
    assert metrics["evidence_safety_violation_count"] > 0
    assert metrics["normalization"]["correct"] == 2
    assert metrics["cases"][0]["units"][0]["root_stage"] == "EVIDENCE_MATCHING"
    assert "wrong_claim_scope" in metrics["failure_code_counts"]


@pytest.mark.parametrize("positive_status", ["supported", "partial"])
def test_generic_reviewed_months_cannot_establish_backend_category_support(
    positive_status: str,
) -> None:
    job = evidence_helpers.source_job("Five years of backend experience are essential.")
    profile = evidence_helpers.candidate(
        60,
        subject="experience",
        kind="experience",
        unit="months",
    )
    start = job.text.index("experience")
    case = EvaluationCase(
        case_id="SYNTHETIC-BACKEND-CATEGORY",
        job=job,
        profile=profile,
        units=(
            SourceGoldUnit(
                requirement_id="synthetic-backend-category:1",
                source_start=0,
                source_end=len(job.text),
                head_start=start,
                head_end=start + len("experience"),
                concept="experience",
                assertion=Assertion(
                    kind="experience", subject="experience", unit="months", value=60
                ),
                priority="essential",
                status="unknown",
                claim_ids=(),
            ),
        ),
        group="safety",
    )
    original = direct_result(case)
    row = original.assessment.rows[0]
    assert row.requirement.constraints.experience_scope == "legacy_backend"
    assert row.status == "unknown" and not row.claim_refs and not row.evidence_refs
    assert not evaluate_results((case,), (original,))["failures"]
    changed_row = fault_copy(
        row,
        update={
            "status": positive_status,
            "observed_value": 60,
            "reason": "reviewed_support",
            "claim_refs": (claim_ref(profile.claims[0]),),
            "evidence_refs": (evidence_ref(profile.evidence[0]),),
        },
    )
    changed = replace(
        original, assessment=fault_copy(original.assessment, update={"rows": (changed_row,)})
    )
    metrics = evaluate_results((case,), (changed,))
    assert metrics["normalization"]["correct"] == 1
    assert metrics["fit"]["correct"] == 0
    assert metrics["failure_code_counts"]["unsupported_experience_scope"] == 1
    assert not any("fabricated_or_stale" in row["code"] for row in metrics["failures"])


@pytest.mark.parametrize(
    "case_index,subject", [(0, "azure"), (4, "fastapi"), (4, "llm_integration")]
)
def test_existing_unreviewed_or_withdrawn_references_cannot_establish_positive_fit(
    cases: tuple[EvaluationCase, ...],
    case_index: int,
    subject: str,
) -> None:
    case = cases[case_index]
    original = direct_result(case)
    rows = list(original.assessment.rows)
    index = next(i for i, row in enumerate(rows) if row.requirement.canonical_concept == subject)
    row = rows[index]
    assert row.status == "unknown" and row.claim_refs and row.evidence_refs
    rows[index] = fault_copy(
        row,
        update={
            "status": "supported",
            "observed_value": row.requirement.assertion.value,
            "declared_shortfall": False,
            "reason": "reviewed_support",
        },
    )
    changed = replace(
        original, assessment=fault_copy(original.assessment, update={"rows": tuple(rows)})
    )
    metrics = evaluate_results((case,), (changed,))
    assert "unsupported_positive" in metrics["failure_code_counts"]
    assert metrics["evidence_safety_violation_count"] > 0
    assert metrics["cases"][0]["units"][index]["root_stage"] == "EVIDENCE_MATCHING"


def test_clipped_source_cannot_receive_full_ambiguity_coverage(
    cases: tuple[EvaluationCase, ...],
) -> None:
    case = cases[5]
    original = direct_result(case)
    units = list(original.trace.units)
    atom = units[1].atom
    end = case.job.text.index(";", atom.source_start) + 1
    units[1] = replace(
        units[1], atom=replace(atom, quote=case.job.text[atom.source_start : end], source_end=end)
    )
    changed = replace(original, trace=replace(original.trace, units=tuple(units)))
    metrics = evaluate_results((case,), (changed,))
    assert metrics["hybrid_extraction"]["tp"] == 1
    assert metrics["hybrid_extraction"]["fn"] == 1
    assert metrics["cases"][0]["units"][1]["root_stage"] == "EXTRACTION"


def test_correct_canonical_value_cannot_rescue_a_forged_interpretation_source(
    cases: tuple[EvaluationCase, ...],
) -> None:
    case = cases[2]
    original = direct_result(case)
    units = list(original.trace.units)
    units[0] = replace(
        units[0],
        requirement=fault_copy(
            units[0].requirement,
            update={"source_quote": units[0].requirement.source_quote.replace("Python", "Pyth0n")},
        ),
    )
    changed = replace(original, trace=replace(original.trace, units=tuple(units)))
    metrics = evaluate_results((case,), (changed,))
    assert metrics["hybrid_extraction"]["tp"] == 1
    assert metrics["hybrid_extraction"]["fp"] == metrics["hybrid_extraction"]["fn"] == 1
    assert metrics["normalization"]["correct"] == metrics["fit"]["correct"] == 1
    assert metrics["cases"][0]["units"][0]["root_stage"] == "EXTRACTION"


def test_final_status_error_is_distinct_from_reference_matching(
    cases: tuple[EvaluationCase, ...],
) -> None:
    case = cases[2]
    original = direct_result(case)
    rows = list(original.assessment.rows)
    rows[0] = fault_copy(
        rows[0],
        update={"status": "unknown", "observed_value": None, "reason": "unreviewed_or_missing"},
    )
    changed = replace(
        original, assessment=fault_copy(original.assessment, update={"rows": tuple(rows)})
    )
    metrics = evaluate_results((case,), (changed,))
    assert metrics["evidence_matching"]["correct"] == 2
    assert metrics["fit"]["correct"] == 1
    assert metrics["cases"][0]["units"][0]["root_stage"] == "FIT_DECISION"


def test_unresolved_source_units_never_collapse_under_a_null_key(
    cases: tuple[EvaluationCase, ...],
) -> None:
    case = cases[2]
    result = direct_result(case)
    for index in range(2):
        result = changed_unit(
            result,
            index,
            {
                "canonical_concept": None,
                "assertion": None,
                "resolution": "abstained",
                "reason": "unknown_term",
            },
        )
    metrics = evaluate_results((case,), (result,))
    assert metrics["hybrid_extraction"]["tp"] == 2
    assert metrics["hybrid_extraction"]["fp"] == 0
    assert "duplicate_atomic_source" not in metrics["failure_code_counts"]


def test_unexpected_positive_rows_receive_independent_reference_checks(
    cases: tuple[EvaluationCase, ...],
) -> None:
    original_case = cases[2]
    negative = replace(original_case, units=())
    result = direct_result(original_case)
    request = result.trace.units[0].requirement
    result = changed_unit(
        result,
        0,
        {
            "canonical_concept": "azure",
            "assertion": Assertion(kind="skill", subject="azure", unit="skill_level", value=2),
            "constraints": request.constraints.model_copy(update={"value": 2}),
        },
    )
    metrics = evaluate_results((negative,), (result,))
    assert metrics["hybrid_extraction"]["fp"] == 2
    assert metrics["evidence_safety_violation_count"] > 0
    assert "wrong_evidence_scope" in metrics["failure_code_counts"]


def fixture_cases(base: EvaluationCase, stem: str) -> tuple[EvaluationCase, ...]:
    path = ROOT / f"datasets/phase6a/{stem}-inputs-v1.json"
    values = json.loads(path.read_bytes())["cases"]
    jobs = {
        row["id"]: base.job.model_copy(
            update={
                "id": JobId("job_" + uuid5(NAMESPACE, row["id"]).hex),
                "opportunity_id": OpportunityId("opportunity_" + uuid5(NAMESPACE, row["id"]).hex),
                "revision": 2,
                "text": row["text"],
                "source_reference": "phase6a:" + row["id"],
            }
        )
        for row in values
    }
    profiles = {key: base.profile for key in jobs}
    return (load_safety_cases if stem == "safety" else load_supplemental_cases)(jobs, profiles)


def test_authored_semantic_abstentions_and_negative_controls(
    cases: tuple[EvaluationCase, ...],
) -> None:
    extras = fixture_cases(cases[0], "supplemental")
    semantic = tuple(case for case in extras if case.group == "semantic")
    metrics = evaluate_results(semantic, tuple(direct_result(case) for case in semantic))
    assert metrics["gold_cases"] == 8 and metrics["gold_units"] == 6
    assert metrics["normalization"]["correct_abstention"] == 6
    assert metrics["normalization"]["unsafe_count"] == 0
    assert metrics["raw_qwen_extraction"]["fp"] == 0


def test_all_authored_safety_expectations_remain_independent_of_runtime_rules(
    cases: tuple[EvaluationCase, ...],
) -> None:
    safety = fixture_cases(cases[0], "safety")
    metrics = evaluate_results(safety, tuple(direct_result(case) for case in safety))
    assert metrics["gold_units"] == 24
    assert metrics["normalization"]["correct_abstention"] == 20
    assert metrics["normalization"]["correct_resolution"] == 4
    assert metrics["fit"]["correct"] == 24
    assert metrics["normalization"]["unsafe_count"] == 0


def test_unsafe_precision_is_worse_than_a_missing_or_safe_abstention(
    cases: tuple[EvaluationCase, ...],
) -> None:
    case = fixture_cases(cases[0], "safety")[3]
    result = direct_result(case)
    request = result.trace.units[0].requirement
    result = changed_unit(
        result,
        0,
        {
            "assertion": Assertion(
                kind="experience", subject="experience", unit="months", value=60
            ),
            "resolution": "resolved",
            "reason": None,
            "constraints": request.constraints.model_copy(
                update={"experience_scope": "generic", "comparator": "minimum", "value": 60}
            ),
        },
    )
    metrics = evaluate_results((case,), (result,))
    assert metrics["normalization"]["unsafe_count"] == 1
    assert metrics["normalization"]["correct_abstention"] == 0
    assert "unsafe_false_certainty" in metrics["failure_code_counts"]


def test_missing_failed_cases_keep_denominators_and_do_not_invent_stage_results(
    cases: tuple[EvaluationCase, ...],
) -> None:
    metrics = evaluate_results(
        cases, (CaseResult(case_id=cases[0].case_id, failure_code="timeout"),)
    )
    assert metrics["gold_units"] == metrics["fit"]["total"] == 24
    assert metrics["raw_qwen_extraction"]["fn"] == metrics["hybrid_extraction"]["fn"] == 24
    assert metrics["successful_cases"] == 0


def test_loader_and_evaluator_reject_membership_and_source_changes(
    cases: tuple[EvaluationCase, ...],
) -> None:
    with pytest.raises(ValueError):
        evaluate_results(cases, (CaseResult(case_id="future-held-out"),))
    with pytest.raises(ValueError):
        evaluate_results(cases, (CaseResult(case_id=cases[0].case_id),) * 2)
    with pytest.raises(ValueError):
        load_careerlab_cases(
            {case.case_id: case.job for case in cases[:-1]},
            {case.case_id: case.profile for case in cases},
        )
