"""Retained source IDs verify profile integration, never pretend to rerun Qwen."""

import asyncio
import importlib
import json
from copy import deepcopy
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from actual.capabilities.job_requirements import ExtractionInput
from actual.job_intelligence.errors import IntelligenceFailure
from actual.models.contracts import PreparedInference
from actual.models.ollama import OllamaQwenProvider


@pytest.fixture
def helper(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / "scripts"))
    return importlib.import_module("verify_phase7_profile")


def test_all_retained_selections_preserve_independent_metrics_without_inference(
    helper: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("Live provider construction is forbidden during replay")

    monkeypatch.setattr(OllamaQwenProvider, "__init__", forbidden)
    captured: list[dict[str, Any]] = []
    infer = helper.RetainedSelectionProvider.infer

    async def spy(provider: object, request: PreparedInference) -> object:
        value = ExtractionInput.model_validate_json(request.input_json)
        captured.append(value.model_dump(mode="json"))
        return await infer(provider, request)

    monkeypatch.setattr(helper.RetainedSelectionProvider, "infer", spy)
    report = asyncio.run(helper.replay())
    assert report["verdict"] == "PASS"
    assert report["provider_double_calls"] == report["profile_and_job_unchanged"] == 87
    assert report["exact_projection_checks"] == report["deterministic_selection_matches"] == 87
    assert report["gold_units_per_trial"] == 54
    assert "no new model inference" in report["scope"]
    for trial in report["trials"]:
        for name, group in trial["groups"].items():
            assert group["matches_retained_evaluation"] and group["canonical_decisions_match"]
            assert group["changed_fields"] == []
            assert group["observed_evaluation_sha256"] == group["retained_evaluation_sha256"]
            assert group["metrics"]["evidence_safety_violation_count"] == 0
            assert group["metrics"]["profile_or_source_promotion_count"] == 0
            assert (
                group["metrics"]["gold_units"]
                == {"careerlab": 24, "adversarial": 24, "semantic": 6}[name]
            )
        assert trial["groups"]["careerlab"]["metrics"]["raw_qwen_extraction"]["fp"] == 1
        assert trial["groups"]["careerlab"]["failures"]
    assert len(captured) == 87
    for value in captured:
        assert set(value) == {"schema_version", "synthetic", "segments"}
        assert value["synthetic"] is True
        assert all(set(part) == {"id", "text"} for part in value["segments"])


@pytest.mark.parametrize(
    "fault", ["missing", "duplicate", "reordered", "boolean_trial", "invalid_source", "failed_call"]
)
def test_replay_rejects_incomplete_or_invalid_retained_attempts(
    helper: ModuleType, fault: str
) -> None:
    baseline = deepcopy(helper.load_baseline())
    attempts = baseline["attempts"]
    if fault == "missing":
        attempts.pop()
    elif fault == "duplicate":
        attempts[1] = deepcopy(attempts[0])
    elif fault == "reordered":
        attempts[0], attempts[1] = attempts[1], attempts[0]
    elif fault == "boolean_trial":
        attempts[0]["trial"] = True
    elif fault == "invalid_source":
        attempts[0]["model_source_ids"] = [32]
    else:
        attempts[0]["failure_code"] = "timeout"
    with pytest.raises(ValueError):
        helper.selections(baseline, helper.cases())


def test_runtime_failure_keeps_denominators_and_fails_replay(
    helper: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def failure(self: object, job: object, profile: object) -> object:
        raise IntelligenceFailure("input_rejected")

    monkeypatch.setattr(helper.JobIntelligence, "assess", failure)
    report = asyncio.run(helper.replay())
    assert report["verdict"] == "FAIL" and report["planned_replays"] == 87
    assert report["provider_double_calls"] == 0
    for trial in report["trials"]:
        assert trial["groups"]["careerlab"]["metrics"]["fit"]["total"] == 24
        assert trial["groups"]["careerlab"]["metrics"]["fit"]["correct"] == 0
        assert trial["groups"]["careerlab"]["changed_fields"]


def test_output_is_exclusive_and_no_model_content_is_written(
    helper: ModuleType, tmp_path: Path
) -> None:
    report = {"schema_version": "actual-phase7-profile-replay-v1", "verdict": "PASS"}
    path = tmp_path / "new-replay.json"
    helper.write_report(path, report)
    assert json.loads(path.read_text(encoding="utf-8")) == report
    before = path.read_bytes()
    with pytest.raises(FileExistsError):
        helper.write_report(path, {"verdict": "FAIL"})
    assert path.read_bytes() == before


def test_baseline_file_hash_is_verified_before_any_replay(
    helper: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    replacement = tmp_path / "modified-report.json"
    replacement.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(helper, "BASELINE", replacement)
    with pytest.raises(ValueError, match="changed"):
        helper.load_baseline()
