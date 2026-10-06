"""Checkpoint decoding preserves prior predictions without calling model rules."""

import importlib.util
import json
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from types import ModuleType

import pytest
import test_evaluation_v2 as helpers
from test_evaluation_v2 import direct_result, fixture_cases

from actual.evaluation.intelligence_v2 import CaseResult, EvaluationCase
from actual.job_intelligence import matching, normalize
from actual.job_intelligence.service import UnitTrace

ROOT = Path(__file__).resolve().parents[2]
cases = helpers.cases


def codec() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "phase6a_results", ROOT / "scripts/phase6a_results.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_round_trip_all_authored_results_without_raw_content_or_reinference(
    cases: tuple[EvaluationCase, ...],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    all_cases = (
        *cases,
        *fixture_cases(cases[0], "safety"),
        *fixture_cases(cases[0], "supplemental"),
    )
    original = [(case, direct_result(case)) for case in all_cases]

    def reject_rules(*args: object, **kwargs: object) -> None:
        raise AssertionError("Checkpoint restoration must not rerun evaluated rules")

    monkeypatch.setattr(normalize, "normalize_requirement", reject_rules)
    monkeypatch.setattr(matching, "match_requirements", reject_rules)
    module = codec()
    for case, result in original:
        payload = module.encode_result(result)
        text = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        assert len(text.encode()) <= module.MAX_BYTES
        assert case.job.text not in text
        assert all(
            field not in text
            for field in ('"quote":', '"term":', '"text":', '"explanation":', '"source_quote":')
        )
        assert module.decode_result(json.loads(text), case.job, case.profile) == result


def test_failed_result_round_trip_retains_failure_without_inventing_assessment(
    cases: tuple[EvaluationCase, ...],
) -> None:
    module = codec()
    result = CaseResult(case_id=cases[0].case_id, failure_code="timeout")
    payload = module.encode_result(result)
    assert module.decode_result(payload, cases[0].job, cases[0].profile) == result


def test_closed_local_rejection_survives_checkpoint_without_an_assessment_row(
    cases: tuple[EvaluationCase, ...],
) -> None:
    module = codec()
    case = replace(cases[2], units=())
    result = direct_result(case)
    result = replace(
        result,
        trace=replace(
            result.trace,
            units=(
                UnitTrace(source_id=0, failure_stage="extraction", failure_code="unsafe_source"),
            ),
        ),
    )
    payload = module.encode_result(result)
    assert module.decode_result(payload, case.job, case.profile) == result


@pytest.mark.parametrize(
    "fault",
    [
        "source",
        "term",
        "schema",
        "content",
        "explanation",
        "scope",
        "trace_meaning",
        "unit_code",
        "unit_stage",
    ],
)
def test_corrupted_or_content_bearing_payload_fails_closed(
    cases: tuple[EvaluationCase, ...],
    fault: str,
) -> None:
    module = codec()
    case = cases[2]
    payload = deepcopy(module.encode_result(direct_result(case)))
    if fault == "source":
        payload["trace"]["segments"][0]["end"] = 12001
    elif fault == "term":
        payload["assessment"]["rows"][0]["requirement"]["term_start"] = True
    elif fault == "schema":
        payload["schema_version"] = "future"
    elif fault == "content":
        payload["prompt"] = "Unexpected sensitive content"
    elif fault == "explanation":
        payload["assessment"]["rows"][0]["explanation_sha256"] = "0" * 64
    elif fault == "scope":
        payload["assessment"]["profile_digest"] = "0" * 64
    elif fault == "trace_meaning":
        payload["trace"]["units"][0]["requirement"]["priority"] = "preferred"
    elif fault == "unit_code":
        payload["trace"]["units"][0]["failure_stage"] = "extraction"
        payload["trace"]["units"][0]["failure_code"] = "raw_sensitive_content"
    elif fault == "unit_stage":
        payload["trace"]["units"][0]["failure_stage"] = "raw_sensitive_content"
        payload["trace"]["units"][0]["failure_code"] = "unsafe_source"
    with pytest.raises(ValueError):
        module.decode_result(payload, case.job, case.profile)


def test_saved_result_cannot_bind_another_observable_revision(
    cases: tuple[EvaluationCase, ...],
) -> None:
    module = codec()
    case = cases[2]
    payload = module.encode_result(direct_result(case))
    changed = case.job.model_copy(update={"revision": case.job.revision + 1})
    with pytest.raises(ValueError):
        module.decode_result(payload, changed, case.profile)
