"""Checkpoint failures preserve measured attempts without pretending missing calls ran."""

import asyncio
import importlib
import json
from dataclasses import replace
from pathlib import Path
from types import ModuleType

import pytest

from actual.careerlab.generator import generate_development
from actual.evaluation.job_intelligence import (
    CasePrediction,
    Prediction,
    evaluate_cases,
    evaluate_trial,
    load_adversarial_inputs,
    load_adversarial_oracles,
    load_development_oracles,
)


@pytest.fixture
def journal_module(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / "scripts"))
    return importlib.import_module("phase6_journal")


def configuration() -> dict[str, object]:
    return {
        "provider": "ollama",
        "model": "qwen3:4b-instruct",
        "timeout_seconds": 120,
        "context_tokens": 4096,
        "max_output_tokens": 512,
        "temperature": 0,
        "seed": 42,
    }


def prediction(case_id: str) -> CasePrediction:
    return CasePrediction(
        case_id=case_id,
        predictions=(
            Prediction(
                requirement_id="requirement",
                opportunity_id="opportunity",
                subject="python",
                kind="skill",
                unit="skill_level",
                minimum=2,
                priority="essential",
                status="supported",
                claim_ids=("claim",),
                evidence_ids=("evidence",),
            ),
        ),
        metadata=({"request_id": "request", "identity": {"provider": "ollama", "model": "qwen"}},),
        known_claim_ids=("claim",),
        known_evidence_ids=("evidence",),
    )


def attempt(case_id: str, trial: int = 1) -> dict[str, object]:
    return {
        "attempt_id": "attempt",
        "trial": trial,
        "case_id": case_id,
        "started_at": "2026-10-05T10:00:00Z",
        "finished_at": "2026-10-05T10:00:01Z",
        "duration_ms": 1000,
        "failure_code": None,
        "provider_metadata_available": True,
        "normalization_diagnostics": [],
    }


def test_each_record_is_durable_before_finalization(
    tmp_path: Path,
    journal_module: ModuleType,
) -> None:
    path = tmp_path / "checkpoint.json"
    sources = {"src/actual/example.py": "a" * 64}
    journal = journal_module.TrialJournal(
        path=path,
        case_ids=("first", "second"),
        configuration=configuration(),
        frozen_sources=sources,
    )
    initial = json.loads(path.read_bytes())
    assert initial["status"] == "running"
    assert initial["records"] == initial["attempts"] == []
    journal.record(trial=1, prediction=prediction("first"), attempt=attempt("first"))
    checkpoint = json.loads(path.read_bytes())
    assert checkpoint["requested_configuration"] == configuration()
    assert checkpoint["frozen_sources_sha256"] == sources
    assert checkpoint["records"][0]["prediction"]["case_id"] == "first"
    assert checkpoint["records"][0]["prediction"]["predictions"][0]["minimum"] == 2
    assert len(checkpoint["attempts"]) == len(checkpoint["records"]) == 1
    assert not path.with_name(path.name + ".tmp").exists()


@pytest.mark.parametrize("operation", ["fsync", "replace"])
def test_atomic_write_failure_preserves_previous_checkpoint_and_rolls_back_memory(
    operation: str,
    tmp_path: Path,
    journal_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "checkpoint.json"
    journal = journal_module.TrialJournal(
        path=path,
        case_ids=("first", "second"),
        configuration=configuration(),
        frozen_sources={},
    )
    journal.record(trial=1, prediction=prediction("first"), attempt=attempt("first"))
    before = path.read_bytes()

    def fail(*args: object, **kwargs: object) -> None:
        raise OSError("synthetic checkpoint fault")

    monkeypatch.setattr(journal_module.os, operation, fail)
    with pytest.raises(OSError, match="synthetic checkpoint"):
        journal.record(trial=1, prediction=prediction("second"), attempt=attempt("second"))
    assert path.read_bytes() == before
    assert [item.case_id for _, item in journal.records] == ["first"]
    assert [item["case_id"] for item in journal.attempts] == ["first"]
    assert not path.with_name(path.name + ".tmp").exists()


def test_out_of_order_duplicate_or_unknown_attempt_never_changes_checkpoint(
    tmp_path: Path,
    journal_module: ModuleType,
) -> None:
    path = tmp_path / "checkpoint.json"
    journal = journal_module.TrialJournal(
        path=path,
        case_ids=("first", "second"),
        configuration=configuration(),
        frozen_sources={},
    )
    before = path.read_bytes()
    with pytest.raises(ValueError, match="order"):
        journal.record(trial=1, prediction=prediction("second"), attempt=attempt("second"))
    assert path.read_bytes() == before
    journal.record(trial=1, prediction=prediction("first"), attempt=attempt("first"))
    before = path.read_bytes()
    for row, trial in (
        (prediction("first"), 1),
        (prediction("second"), 2),
        (prediction("unrecognized"), 1),
    ):
        with pytest.raises(ValueError, match="order"):
            journal.record(trial=trial, prediction=row, attempt=attempt(row.case_id, trial))
        assert path.read_bytes() == before


@pytest.mark.parametrize(
    "field", ["prompt", "response", "job_text", "quote", "raw_prompt", "raw_response"]
)
def test_model_content_is_rejected_even_inside_metadata(
    field: str,
    tmp_path: Path,
    journal_module: ModuleType,
) -> None:
    path = tmp_path / "checkpoint.json"
    journal = journal_module.TrialJournal(
        path=path,
        case_ids=("first",),
        configuration=configuration(),
        frozen_sources={},
    )
    row = replace(prediction("first"), metadata=({"identity": {field: "content canary"}},))
    before = path.read_bytes()
    with pytest.raises(ValueError, match="content"):
        journal.record(trial=1, prediction=row, attempt=attempt("first"))
    assert path.read_bytes() == before
    assert not journal.records


def test_unknown_attempt_fields_cannot_smuggle_model_content(
    tmp_path: Path,
    journal_module: ModuleType,
) -> None:
    path = tmp_path / "checkpoint.json"
    journal = journal_module.TrialJournal(
        path=path,
        case_ids=("first",),
        configuration=configuration(),
        frozen_sources={},
    )
    payload = {**attempt("first"), "raw_model_response": "not allowed"}
    with pytest.raises(ValueError, match="order"):
        journal.record(trial=1, prediction=prediction("first"), attempt=payload)
    assert json.loads(path.read_bytes())["records"] == []


def test_finalize_retains_completed_attempts_and_fills_all_missing_trial_slots(
    tmp_path: Path,
    journal_module: ModuleType,
) -> None:
    pairs = generate_development()[:7]
    opportunities = {
        pair.inputs.id: {job.id: job.canonical_opportunity for job in pair.inputs.jobs}
        for pair in pairs
    }
    gold = load_development_oracles(opportunities, oracles=tuple(pair.oracle for pair in pairs))
    attacks = load_adversarial_oracles(
        {row.case_id: "opportunity" for row in load_adversarial_inputs()}
    )
    ids = tuple(row.case_id for row in (*gold, *attacks))
    path = tmp_path / "checkpoint.json"
    journal = journal_module.TrialJournal(
        path=path,
        case_ids=ids,
        configuration=configuration(),
        frozen_sources={},
    )
    completed = CasePrediction(case_id=ids[0], failure_code="invalid_requirement")
    journal.record(
        trial=1,
        prediction=completed,
        attempt={
            **attempt(ids[0]),
            "failure_code": "invalid_requirement",
            "provider_metadata_available": False,
        },
    )
    trials = journal.finalize("network_inspection_failure")
    checkpoint = json.loads(path.read_bytes())
    assert checkpoint["status"] == "aborted"
    assert checkpoint["abort_code"] == "network_inspection_failure"
    assert len(checkpoint["records"]) == len(checkpoint["attempts"]) == 1
    assert len(trials) == 3 and all(len(rows) == 11 for rows in trials)
    assert trials[0][0] == completed
    assert all(row.failure_code == "not_attempted" for row in trials[0][1:])
    assert all(row.failure_code == "not_attempted" for rows in trials[1:] for row in rows)
    for index, trial in enumerate(trials, start=1):
        development = evaluate_cases(gold, trial[:7])
        adversarial = evaluate_cases(attacks, trial[7:])
        assert development["gold_units"] == 24
        assert development["fit"]["total"] == development["importance"]["total"] == 24
        assert development["successful_inference_cases"] == 0
        assert (
            evaluate_trial(
                trial=index,
                development=development,
                adversarial=adversarial,
                component_correct=24,
                component_total=24,
            )["verdict"]
            == "NO_GO"
        )
    with pytest.raises(ValueError, match="order"):
        journal.record(trial=1, prediction=prediction(ids[1]), attempt=attempt(ids[1]))


def test_complete_trials_preserve_prediction_types_and_exact_attempt_count(
    tmp_path: Path,
    journal_module: ModuleType,
) -> None:
    journal = journal_module.TrialJournal(
        path=tmp_path / "checkpoint.json",
        case_ids=("case",),
        configuration=configuration(),
        frozen_sources={},
    )
    for trial in (1, 2, 3):
        journal.record(trial=trial, prediction=prediction("case"), attempt=attempt("case", trial))
    final = journal.finalize()
    assert journal.status == "complete"
    assert journal.abort_code is None
    assert len(journal.records) == len(journal.attempts) == 3
    assert all(type(rows[0].predictions[0]) is Prediction for rows in final)
    assert all(rows[0].failure_code is None for rows in final)
    checkpoint = json.loads(journal.path.read_bytes())
    assert checkpoint["status"] == "complete"


def test_new_journal_never_overwrites_previous_evidence_and_abort_text_is_closed(
    tmp_path: Path,
    journal_module: ModuleType,
) -> None:
    path = tmp_path / "checkpoint.json"
    original = journal_module.TrialJournal(
        path=path,
        case_ids=("case",),
        configuration=configuration(),
        frozen_sources={},
    )
    before = path.read_bytes()
    with pytest.raises(ValueError, match="new local"):
        journal_module.TrialJournal(
            path=path,
            case_ids=("case",),
            configuration=configuration(),
            frozen_sources={},
        )
    assert path.read_bytes() == before
    with pytest.raises(ValueError, match="fixed safe"):
        original.finalize("Full exception with raw content")
    assert path.read_bytes() == before


def test_missing_or_duplicate_case_configuration_is_rejected(
    tmp_path: Path,
    journal_module: ModuleType,
) -> None:
    for case_ids, config in (
        ((), configuration()),
        (("case", "case"), configuration()),
        (("case",), {"provider": "ollama"}),
    ):
        with pytest.raises(ValueError, match="identities"):
            journal_module.TrialJournal(
                path=tmp_path / "checkpoint.json",
                case_ids=case_ids,
                configuration=config,
                frozen_sources={},
            )


@pytest.fixture
def live_helper(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / "scripts"))
    return importlib.import_module("evaluate_phase6a_live")


def test_observation_failure_cancels_in_flight_inference_with_safe_code(
    live_helper: ModuleType,
) -> None:
    async def run() -> None:
        stopped = asyncio.Event()
        cancelled = asyncio.Event()

        async def inference() -> None:
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                cancelled.set()
                raise

        async def observation() -> int:
            await asyncio.sleep(0)
            raise RuntimeError("raw network exception content canary")

        infer_task = asyncio.create_task(inference())
        observer_task = asyncio.create_task(observation())
        outcome = await asyncio.wait_for(
            live_helper.supervise(infer_task, observer_task, stopped), timeout=5
        )
        assert outcome == ("network_inspection_failed", None)
        assert cancelled.is_set() and stopped.is_set()
        assert infer_task.done() and observer_task.done()
        assert "canary" not in repr(outcome)

    asyncio.run(run())


def test_successful_inference_stops_monitor_and_preserves_sample_count(
    live_helper: ModuleType,
) -> None:
    async def run() -> None:
        stopped = asyncio.Event()
        monitor_stopped = asyncio.Event()

        async def inference() -> None:
            await asyncio.sleep(0)

        async def observation() -> int:
            await stopped.wait()
            monitor_stopped.set()
            return 7

        infer_task = asyncio.create_task(inference())
        observer_task = asyncio.create_task(observation())
        outcome = await asyncio.wait_for(
            live_helper.supervise(infer_task, observer_task, stopped), timeout=5
        )
        assert outcome == (None, 7)
        assert stopped.is_set() and monitor_stopped.is_set()
        assert infer_task.done() and observer_task.done()

    asyncio.run(run())


def test_inference_exception_stops_monitor_and_maps_to_safe_pipeline_code(
    live_helper: ModuleType,
) -> None:
    async def run() -> None:
        stopped = asyncio.Event()

        async def inference() -> None:
            await asyncio.sleep(0)
            raise RuntimeError("raw model prompt and response canary")

        async def observation() -> int:
            await stopped.wait()
            return 3

        infer_task = asyncio.create_task(inference())
        observer_task = asyncio.create_task(observation())
        outcome = await asyncio.wait_for(
            live_helper.supervise(infer_task, observer_task, stopped), timeout=5
        )
        assert outcome == ("evaluation_pipeline_failed", 3)
        assert stopped.is_set() and infer_task.done() and observer_task.done()
        assert "canary" not in repr(outcome)

    asyncio.run(run())


def test_early_monitor_completion_aborts_inference_instead_of_claiming_success(
    live_helper: ModuleType,
) -> None:
    async def run() -> None:
        stopped = asyncio.Event()
        cancelled = asyncio.Event()

        async def inference() -> None:
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                cancelled.set()
                raise

        async def observation() -> int:
            await asyncio.sleep(0)
            return 4

        infer_task = asyncio.create_task(inference())
        observer_task = asyncio.create_task(observation())
        outcome = await asyncio.wait_for(
            live_helper.supervise(infer_task, observer_task, stopped), timeout=5
        )
        assert outcome == ("network_observation_ended_early", 4)
        assert stopped.is_set() and cancelled.is_set()

    asyncio.run(run())
