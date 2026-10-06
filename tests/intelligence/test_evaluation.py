"""Honest task denominators, fixed gates and public-development evaluator isolation."""

import json
from dataclasses import replace
from pathlib import Path

import pytest

from actual.careerlab.generator import generate_development
from actual.careerlab_bridge import ImportContext
from actual.core.primitives import ActorId, WorkspaceId
from actual.evaluation import job_intelligence as evaluation
from actual.evaluation.job_intelligence import (
    CasePrediction,
    GoldCase,
    GoldRequirement,
    Prediction,
    component_check,
    evaluate_cases,
    evaluate_trial,
    evaluation_summary,
    load_adversarial_inputs,
    load_adversarial_oracles,
    load_development_oracles,
)


def gold_cases() -> tuple[GoldCase, ...]:
    pairs = generate_development()[:7]
    opportunities = {
        pair.inputs.id: {job.id: job.canonical_opportunity for job in pair.inputs.jobs}
        for pair in pairs
    }
    return load_development_oracles(opportunities, oracles=tuple(pair.oracle for pair in pairs))


def perfect(cases: tuple[GoldCase, ...]) -> tuple[CasePrediction, ...]:
    result = []
    for case in cases:
        predictions = tuple(
            Prediction(
                requirement_id=f"prediction:{index}",
                opportunity_id=item.opportunity_id,
                subject=item.subject,
                kind=item.kind,
                unit=item.unit,
                minimum=item.minimum,
                priority=item.priority,
                status=item.status,
                declared_shortfall=item.declared_shortfall,
                claim_ids=(f"claim:{item.subject}",),
                evidence_ids=(f"evidence:{item.subject}",),
            )
            for index, item in enumerate(case.requirements)
        )
        result.append(
            CasePrediction(
                case_id=case.case_id,
                predictions=predictions,
                known_claim_ids=tuple(ref for item in predictions for ref in item.claim_ids),
                known_evidence_ids=tuple(ref for item in predictions for ref in item.evidence_ids),
            )
        )
    return tuple(result)


def adversarial_metrics() -> dict[str, object]:
    ids = {item.case_id: "adversarial-opportunity" for item in load_adversarial_inputs()}
    gold = load_adversarial_oracles(ids)
    return evaluate_cases(gold, perfect(gold))


def test_public_support_counts_and_per_task_counts_are_exact() -> None:
    gold = gold_cases()
    metrics = evaluate_cases(gold, perfect(gold))
    assert metrics["gold_cases"] == 7
    assert metrics["gold_units"] == 24
    assert metrics["support_by_subject"] == {
        "python": 7,
        "fastapi": 5,
        "azure": 3,
        "french": 3,
        "experience": 2,
        "llm_integration": 4,
    }
    assert metrics["extraction"]["tp"] == 24
    for key in ("importance", "normalization", "fit", "declared_shortfall"):
        assert metrics[key]["correct"] == metrics[key]["total"] == 24
    assert metrics["fit_case_vector_agreement"]["correct"] == 7
    assert metrics["fit"]["classes"]["partial"]["support"] == 0
    assert metrics["fit"]["classes"]["partial"]["f1"] is None
    assert metrics["fit"]["macro_f1_supported_classes"] == 1.0
    assert not metrics["failures"]


def test_missing_case_never_disappears_from_denominators() -> None:
    gold = gold_cases()
    predictions = perfect(gold)
    metrics = evaluate_cases(gold, predictions[1:])
    assert metrics["gold_units"] == 24
    assert metrics["extraction"]["tp"] == 18
    assert metrics["extraction"]["fn"] == 6
    assert metrics["importance"]["total"] == 24
    assert metrics["fit"]["total"] == 24
    assert metrics["cases"][0]["inference_failure"] == "missing_case"
    assert metrics["fit"]["confusion_matrix"]["supported"]["missing"] == 3


@pytest.mark.parametrize(
    "failure,category",
    [
        ("timeout", "model_timeout"),
        ("invalid_output", "schema_failure"),
        ("output_limit", "schema_failure"),
        ("model_not_found", "inference_failure"),
    ],
)
def test_every_provider_failure_is_retained(failure: str, category: str) -> None:
    gold = gold_cases()
    predictions = perfect(gold)
    failed = CasePrediction(case_id=gold[0].case_id, failure_code=failure)
    metrics = evaluate_cases(gold, (failed, *predictions[1:]))
    assert metrics["successful_inference_cases"] == 6
    assert metrics["failure_category_counts"][category] == 1
    assert metrics["extraction"]["fn"] == 6
    assert metrics["cases"][0]["predictions"] == []


def test_duplicate_prediction_cannot_inflate_true_positives() -> None:
    gold = gold_cases()
    predictions = perfect(gold)
    first = predictions[0]
    duplicate = replace(first.predictions[0], requirement_id="extra-duplicate")
    changed = replace(first, predictions=(*first.predictions, duplicate))
    metrics = evaluate_cases(gold, (changed, *predictions[1:]))
    assert metrics["extraction"]["tp"] == 24
    assert metrics["extraction"]["fp"] == 1
    assert metrics["extraction"]["precision"] == 24 / 25
    assert metrics["failure_category_counts"]["duplicate_requirement"] == 1


def test_alignment_does_not_hide_wrong_threshold_importance_or_fit() -> None:
    gold = gold_cases()
    predictions = perfect(gold)
    first = predictions[0]
    changed_row = replace(first.predictions[0], minimum=3, priority="preferred", status="unknown")
    changed = replace(first, predictions=(changed_row, *first.predictions[1:]))
    metrics = evaluate_cases(gold, (changed, *predictions[1:]))
    assert metrics["extraction"]["tp"] == 24
    assert metrics["extraction"]["f1"] == 1.0
    assert metrics["normalization"]["correct"] == 23
    assert metrics["importance"]["correct"] == 23
    assert metrics["fit"]["correct"] == 23
    assert all(item["rationale"] for item in metrics["failures"])
    normalization_error = next(
        item for item in metrics["failures"] if item["category"] == "wrong_normalization"
    )
    assert normalization_error["expected"] == ["skill", "skill_level", 2]
    assert normalization_error["observed"] == ["skill", "skill_level", 3]


def test_unknown_subject_is_both_false_positive_and_missed_gold_unit() -> None:
    gold = gold_cases()
    predictions = perfect(gold)
    first = predictions[0]
    row = replace(first.predictions[0], subject=None, kind=None, unit=None, minimum=None)
    changed = replace(first, predictions=(row, *first.predictions[1:]))
    metrics = evaluate_cases(gold, (changed, *predictions[1:]))
    assert metrics["extraction"]["tp"] == 23
    assert metrics["extraction"]["fp"] == metrics["extraction"]["fn"] == 1
    assert metrics["extraction"]["by_subject"]["unresolved"]["support"] == 0


@pytest.mark.parametrize(
    "change,category",
    [
        ({"status": "supported"}, "unsupported_skill_match"),
        ({"claim_ids": ("fabricated-claim",)}, "fabricated_reference"),
        ({"evidence_ids": ()}, "missing_positive_evidence"),
    ],
)
def test_positive_support_safety_failures_are_independent_of_average_quality(
    change: dict[str, object],
    category: str,
) -> None:
    gold = gold_cases()
    predictions = perfect(gold)
    first = predictions[0]
    # Azure is unknown; Python is supported. Each test targets the relevant scope.
    index = 2 if category == "unsupported_skill_match" else 0
    rows = list(first.predictions)
    rows[index] = replace(rows[index], **change)
    changed = replace(first, predictions=tuple(rows))
    metrics = evaluate_cases(gold, (changed, *predictions[1:]))
    assert metrics["failure_category_counts"][category] == 1
    report = evaluate_trial(
        trial=1,
        development=metrics,
        adversarial=adversarial_metrics(),
        component_correct=24,
        component_total=24,
    )
    assert report["verdict"] == "NO_GO"
    assert not report["gates"]["zero_critical_truthfulness_errors"]


def test_profile_mutation_is_a_critical_gate_failure() -> None:
    gold = gold_cases()
    predictions = perfect(gold)
    changed = replace(predictions[0], profile_unchanged=False)
    metrics = evaluate_cases(gold, (changed, *predictions[1:]))
    assert metrics["fit"]["correct"] == 24
    assert metrics["failure_category_counts"]["profile_promotion"] == 1
    assert (
        evaluate_trial(
            trial=1,
            development=metrics,
            adversarial=adversarial_metrics(),
            component_correct=24,
            component_total=24,
        )["verdict"]
        == "NO_GO"
    )


@pytest.mark.parametrize("subject", ["experience", "french", "azure", "llm_integration"])
def test_missing_critical_requirement_blocks_aggregate_pass(subject: str) -> None:
    gold = gold_cases()
    predictions = perfect(gold)
    case_index = {"experience": 0, "french": 0, "azure": 5, "llm_integration": 3}[subject]
    changed = replace(
        predictions[case_index],
        predictions=tuple(
            item for item in predictions[case_index].predictions if item.subject != subject
        ),
    )
    all_predictions = (*predictions[:case_index], changed, *predictions[case_index + 1 :])
    metrics = evaluate_cases(gold, all_predictions)
    assert metrics["extraction"]["recall"] == 23 / 24
    report = evaluate_trial(
        trial=1,
        development=metrics,
        adversarial=adversarial_metrics(),
        component_correct=24,
        component_total=24,
    )
    assert report["gates"]["extraction_recall_at_least_0_90"]
    assert report["verdict"] == "NO_GO"


def test_threshold_boundary_allows_two_noncritical_misses_but_not_three() -> None:
    gold = gold_cases()
    predictions = perfect(gold)
    changed = replace(predictions[0], predictions=predictions[0].predictions[2:])
    two_misses = evaluate_cases(gold, (changed, *predictions[1:]))
    report = evaluate_trial(
        trial=1,
        development=two_misses,
        adversarial=adversarial_metrics(),
        component_correct=24,
        component_total=24,
    )
    assert report["verdict"] == "GO"
    second = replace(predictions[2], predictions=predictions[2].predictions[1:])
    three_misses = evaluate_cases(gold, (changed, predictions[1], second, *predictions[3:]))
    assert (
        evaluate_trial(
            trial=1,
            development=three_misses,
            adversarial=adversarial_metrics(),
            component_correct=24,
            component_total=24,
        )["verdict"]
        == "NO_GO"
    )


def test_adversarial_sources_have_separate_oracles_and_exact_genuine_units() -> None:
    sources = load_adversarial_inputs()
    assert len(sources) == 4
    payload = evaluation.ADVERSARIAL_INPUT_PATH.read_text(encoding="utf-8")
    for forbidden in ("requirements", "expected", "status", "secret_canary", "SYNTHETIC-CANARY-"):
        assert forbidden not in payload
    assert all(item.text.startswith("SYNTHETIC POSTING.") for item in sources)
    oracle = load_adversarial_oracles({item.case_id: "opportunity" for item in sources})
    assert all(len(item.requirements) == 1 for item in oracle)
    assert all(item.requirements[0].subject == "python" for item in oracle)
    assert all(item.requirements[0].minimum == 2 for item in oracle)


def test_three_trials_cannot_hide_a_failed_trial_or_enlarge_support() -> None:
    gold = gold_cases()
    development = evaluate_cases(gold, perfect(gold))
    trials = tuple(
        evaluate_trial(
            trial=number,
            development=development,
            adversarial=adversarial_metrics(),
            component_correct=24 if number != 2 else 23,
            component_total=24,
        )
        for number in (1, 2, 3)
    )
    summary = evaluation_summary(trials, dataset_identity={"dataset_sha256": "example"})
    assert summary["verdict"] == "NO_GO"
    assert summary["development_case_support"] == 7
    assert summary["distinct_source_text_support"] == 6
    assert summary["trials_are_not_independent_samples"]
    assert summary["overall_recommendation_accuracy"] is None
    assert summary["locked_test"] == summary["validation"] == "unmaterialized"
    assert json.loads(json.dumps(summary))["verdict"] == "NO_GO"
    with pytest.raises(ValueError, match="three planned"):
        evaluation_summary(trials[:2], dataset_identity={})


def test_component_checks_compare_all_24_authored_units_without_model_calls() -> None:
    pairs = generate_development()
    context = ImportContext(
        workspace_id=WorkspaceId("workspace_" + "1" * 32),
        actor_id=ActorId("actor_" + "2" * 32),
    )
    result = component_check(
        tuple(pair.inputs for pair in pairs),
        context,
        tuple(pair.oracle for pair in pairs[:7]),
    )
    assert result == {"correct": 24, "total": 24, "errors": []}


def test_oracle_reader_rejects_locked_paths_before_reading(tmp_path: Path) -> None:
    path = tmp_path / "locked_test" / "case.json"
    with pytest.raises(ValueError, match="public-development"):
        evaluation._checked_file(path, tmp_path)


def test_evaluation_inputs_reject_ambiguous_or_inconsistent_internal_data() -> None:
    gold = gold_cases()
    with pytest.raises(ValueError, match="unique"):
        GoldCase(case_id="duplicate", requirements=(gold[0].requirements[0],) * 2)
    with pytest.raises(ValueError, match="outside"):
        evaluate_cases(gold, (CasePrediction(case_id="unrecognized"),))
    with pytest.raises(ValueError, match="unique"):
        evaluate_cases(gold, (perfect(gold)[0],) * 2)
    with pytest.raises(ValueError, match="accepted predictions"):
        replace(perfect(gold)[0], failure_code="timeout")
    with pytest.raises(ValueError, match="allowlisted"):
        CasePrediction(case_id="case", metadata=({"raw_prompt": "not retained"},))
    with pytest.raises(ValueError, match="complete"):
        replace(perfect(gold)[0].predictions[0], minimum=None)
    with pytest.raises(ValueError):
        replace(gold[0].requirements[0], minimum=True)
    with pytest.raises(ValueError, match="boolean"):
        replace(gold[0].requirements[0], declared_shortfall=1)


def test_empty_predictions_and_undeclared_gold_corruption_fail_honestly() -> None:
    gold = gold_cases()
    metrics = evaluate_cases(gold, tuple(CasePrediction(case_id=item.case_id) for item in gold))
    assert metrics["extraction"]["precision"] is None
    assert metrics["extraction"]["recall"] == 0
    assert metrics["normalization"]["rate"] == 0
    assert (
        evaluate_trial(
            trial=1,
            development=metrics,
            adversarial=adversarial_metrics(),
            component_correct=24,
            component_total=24,
        )["verdict"]
        == "NO_GO"
    )
    with pytest.raises(ValueError, match="seven"):
        load_development_oracles({}, oracles=())
    with pytest.raises(ValueError, match="nonempty"):
        evaluate_cases((), ())


def test_wrong_opportunity_cannot_match_another_source_requirement() -> None:
    requirement = GoldRequirement(
        requirement_id="gold",
        opportunity_id="original",
        subject="python",
        kind="skill",
        unit="skill_level",
        minimum=2,
        priority="essential",
        status="supported",
    )
    gold = (GoldCase(case_id="case", requirements=(requirement,)),)
    original = perfect(gold)[0]
    other = replace(original.predictions[0], opportunity_id="other")
    metrics = evaluate_cases(gold, (replace(original, predictions=(other,)),))
    assert metrics["extraction"]["tp"] == 0
    assert metrics["extraction"]["fp"] == metrics["extraction"]["fn"] == 1


def test_development_oracle_identity_binds_the_accepted_phase5_manifest() -> None:
    identity = evaluation.development_oracle_identity()
    assert identity["accepted_milestone"] == "09d7653"
    assert identity["manifest_file_sha256"] == (
        "1478f970bab1a8b6e178aa3bd7d2ccb122165170560bf3ac829e1ce09932de18"
    )
    assert set(identity["oracle_sha256"]) == set(evaluation.DEVELOPMENT_CASE_IDS)
    assert identity["oracle_sha256"]["CAREER-DEV-001"] == (
        "066372f4cd7e7b84d55476c888c4575a90a59f76cb275018cbe5d5a431a69fd4"
    )


def test_corrupted_oracle_is_rejected_before_deserialization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = evaluation._checked_file

    def corrupted(path: Path, root: Path) -> bytes:
        if path.parent == evaluation.DEVELOPMENT_ORACLE_ROOT:
            return b"{}"
        return original(path, root)

    def unexpected_parse(*args: object, **kwargs: object) -> object:
        pytest.fail("Corrupted label bytes must never reach the decoder")

    monkeypatch.setattr(evaluation, "_checked_file", corrupted)
    monkeypatch.setattr(evaluation, "load_record", unexpected_parse)
    with pytest.raises(ValueError, match="accepted manifest hash"):
        evaluation.load_development_ground_truth()


def test_relabelled_in_memory_oracles_fail_binding_even_with_unchanged_counts() -> None:
    pairs = generate_development()[:7]
    original = pairs[0].oracle
    changed_requirement = replace(original.requirements[0], minimum=1)
    changed_oracle = replace(
        original, requirements=(changed_requirement, *original.requirements[1:])
    )
    labels = (changed_oracle, *(pair.oracle for pair in pairs[1:]))
    opportunities = {
        pair.inputs.id: {job.id: job.canonical_opportunity for job in pair.inputs.jobs}
        for pair in pairs
    }
    with pytest.raises(ValueError, match="accepted manifest hash"):
        load_development_oracles(opportunities, oracles=labels)
    context = ImportContext(
        workspace_id=WorkspaceId("workspace_" + "1" * 32),
        actor_id=ActorId("actor_" + "2" * 32),
    )
    with pytest.raises(ValueError, match="accepted manifest hash"):
        component_check(tuple(pair.inputs for pair in pairs), context, labels)


def test_changed_manifest_fails_before_label_files_are_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed_paths = []

    def altered_manifest(path: Path, root: Path) -> bytes:
        observed_paths.append(path)
        return b"{}"

    monkeypatch.setattr(evaluation, "_checked_file", altered_manifest)
    with pytest.raises(ValueError, match="manifest identity changed"):
        evaluation.load_development_ground_truth()
    assert observed_paths == [evaluation.ACCEPTED_MANIFEST_PATH]
