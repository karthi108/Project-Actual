"""Quality criteria cannot hide a missed hostile unit or a safe-looking wrong fit."""

import importlib
from copy import deepcopy
from pathlib import Path
from types import ModuleType

import pytest

from actual.evaluation.intelligence_v2 import evaluate_results


@pytest.fixture
def runner(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / "scripts"))
    return importlib.import_module("evaluate_phase6a_live")


def metrics(runner: ModuleType) -> tuple[dict, dict, dict, dict, dict, set[str]]:
    # Authored deterministic component checks exercise the evaluator/report, not
    # live acceptance. No fake result is exported as a Qwen trial.
    from test_evaluation_v2 import direct_result

    selected = runner.cases()
    gold = runner.gold_cases(selected)
    groups = {}
    for group in ("careerlab", "adversarial", "semantic"):
        cases = tuple(case for case in gold if case.group == group)
        groups[group] = evaluate_results(cases, tuple(direct_result(case) for case in cases))
    critical = {
        unit.requirement_id
        for case in gold
        if case.group == "careerlab"
        for unit in case.units
        if unit.priority == "ambiguous"
        or unit.status == "conflict"
        or unit.assertion is not None
        and unit.assertion.kind in {"language", "experience"}
    }
    return (
        groups["careerlab"],
        groups["adversarial"],
        groups["semantic"],
        runner.safety_check(selected[0]),
        {"correct": 24, "total": 24},
        critical,
    )


def test_fixed_support_and_independent_authored_stage_checks(runner: ModuleType) -> None:
    selected = runner.cases()
    gold = runner.gold_cases(selected)
    assert len(selected) == len(gold) == 29
    assert sum(len(case.units) for case in gold) == 54
    assert all(runner.quality_gates(*metrics(runner)).values())


def test_aggregate_improvement_cannot_hide_critical_or_hostile_failures(runner: ModuleType) -> None:
    development, adversarial, semantic, safety, component, critical = metrics(runner)
    missed = deepcopy(adversarial)
    missed["hybrid_extraction"].update(tp=23, fn=1)
    gates = runner.quality_gates(development, missed, semantic, safety, component, critical)
    assert not gates["adversarial_retention"]
    assert gates["original_fit"]
    unsafe = deepcopy(safety)
    unsafe["normalization"]["unsafe_count"] = 1
    gates = runner.quality_gates(development, adversarial, semantic, unsafe, component, critical)
    assert not gates["zero_unsafe_normalization"]
    bad_fit = deepcopy(development)
    bad_fit["failures"].append({"requirement_id": sorted(critical)[0]})
    gates = runner.quality_gates(bad_fit, adversarial, semantic, safety, component, critical)
    assert not gates["critical_original_meanings"]
