"""Fixed, checkpointed Phase-6A development trials; no arbitrary inference intake.

Use ACTUAL_MODEL_MODE=synthetic-development. Source/evaluator identities freeze
before the first call. Gold is loaded after inference, and owned server cleanup
precedes final verdict export. Complete prompts and wire responses are never saved.
"""

import asyncio
import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4, uuid5

import httpx2 as httpx
from phase6_cleanup import cleanup_owned_server
from phase6_journal import TrialJournal
from phase6_monitor import observe_network
from phase6a_results import decode_result, encode_result
from verify_phase5_live import server_environment

from actual.capabilities.job_requirements import JOB_REQUIREMENTS
from actual.career.jobs import Job
from actual.careerlab.validation import validate_input
from actual.careerlab_bridge import ImportContext, map_observable
from actual.core.primitives import ActorId, JobId, OpportunityId, WorkspaceId
from actual.evaluation.intelligence_v2 import (
    CaseResult,
    EvaluationCase,
    evaluate_results,
    load_careerlab_cases,
    load_old_adversarial_cases,
    load_safety_cases,
    load_supplemental_cases,
)
from actual.evaluation.job_intelligence import (
    CasePrediction,
    Prediction,
    component_check,
    development_oracle_identity,
    load_adversarial_inputs,
    load_development_ground_truth,
)
from actual.job_intelligence.development import load_development
from actual.job_intelligence.errors import IntelligenceFailure
from actual.job_intelligence.extraction import ExtractedAtom, segment_document
from actual.job_intelligence.matching import match_requirements
from actual.job_intelligence.normalize import normalize_requirement, source_priority
from actual.job_intelligence.service import IntelligenceTrace, JobIntelligence, UnitTrace
from actual.models.config import OllamaSettings
from actual.models.contracts import (
    Capability,
    GenerationSettings,
    InferenceMetadata,
    InputT,
    OutputT,
    Proposal,
)
from actual.models.errors import ModelFailure
from actual.models.gateway import ModelGateway, canonical_json, metadata_json
from actual.models.ollama import OllamaQwenProvider
from actual.profile.contracts import Profile

ROOT = Path(__file__).resolve().parents[1]
CONTEXT = ImportContext(
    workspace_id=WorkspaceId("workspace_" + "6" * 32),
    actor_id=ActorId("actor_" + "6" * 32),
)
NAMESPACE = UUID("a61b6113-bc8c-4f1d-a274-b451bfec99e0")
INPUT_IDENTITIES = {
    "supplemental-inputs-v1.json": (
        "408c13284bf35ca0eadb0a66f7e45e6568fecb105f9cfda89d94c3e3acb1859f"
    ),
    "safety-inputs-v1.json": "8c8b7531929a714ead3ce069dee9cd74c989a145a994c4da050275a1198c478e",
}


@dataclass(frozen=True)
class Case:
    case_id: str
    job: Job
    profile: Profile
    group: str


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def frozen_sources() -> dict[str, str]:
    paths = [
        ROOT / "docs/phase-6a/design.md",
        ROOT / "pyproject.toml",
        ROOT / "uv.lock",
        *sorted((ROOT / "scripts").glob("*.py")),
        *sorted((ROOT / "src/actual").rglob("*.py")),
        *sorted((ROOT / "datasets/manifests").glob("*.json")),
        *sorted((ROOT / "datasets/phase6").glob("*.json")),
        *sorted((ROOT / "datasets/phase6a").glob("*.json")),
        *sorted((ROOT / "datasets/development/inputs").glob("*.json")),
    ]
    return {path.relative_to(ROOT).as_posix(): digest(path) for path in paths}


def fixed_inputs(name: str) -> list[dict[str, Any]]:
    """Read input-only fixtures through fixed hash-bound paths, never oracle files."""
    if name not in INPUT_IDENTITIES:
        raise ValueError("Unsupported input catalog")
    path = ROOT / "datasets/phase6a" / name
    if any(item.is_symlink() or item.is_junction() for item in (path, *path.parents)):
        raise ValueError("Aliased input catalog")
    payload = path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != INPUT_IDENTITIES[name]:
        raise ValueError("Observable synthetic catalog changed")
    value = json.loads(payload)
    if value.get("synthetic") is not True or type(value.get("cases")) is not list:
        raise ValueError("Explicit synthetic input required")
    rows: list[dict[str, Any]] = value["cases"]
    return rows


def case_job(base: Case, identity: str, text: str) -> Job:
    return Job.model_validate(
        base.job.model_copy(
            update={
                "id": JobId("job_" + uuid5(NAMESPACE, identity).hex),
                "opportunity_id": OpportunityId("opportunity_" + uuid5(NAMESPACE, identity).hex),
                "revision": 2,
                "text": text,
                "source_reference": "phase6a:" + identity,
            }
        )
    )


def cases() -> tuple[Case, ...]:
    ordinary = []
    for value in load_development():
        if value.id == "CAREER-DEV-008":
            if tuple(item.code for item in validate_input(value)) != ("application_transition",):
                raise ValueError("Accepted negative fixture changed")
            try:
                map_observable(value, CONTEXT)
            except ValueError:
                continue
            raise ValueError("Negative fixture entered runtime")
        world = map_observable(value, CONTEXT)
        seen = set()
        for job in world.jobs:
            if job.opportunity_id not in seen:
                ordinary.append(Case(value.id, job, world.profile, "careerlab"))
                seen.add(job.opportunity_id)
    if len(ordinary) != 7:
        raise ValueError("Development support changed")
    base = ordinary[0]
    attacks = [
        Case(row.case_id, case_job(base, row.case_id, row.text), base.profile, "adversarial")
        for row in load_adversarial_inputs()
    ]
    supplemental = [
        Case(row["id"], case_job(base, row["id"], row["text"]), base.profile, row["kind"])
        for row in fixed_inputs("supplemental-inputs-v1.json")
    ]
    selected = tuple(ordinary + attacks + supplemental)
    if len(selected) != 29 or len({case.case_id for case in selected}) != 29:
        raise ValueError("Preregistered support changed")
    return selected


class RecordingGateway(ModelGateway):
    """Retain only accepted inference metadata for the current attempt."""

    last_metadata: InferenceMetadata | None = None

    async def run(
        self, capability: Capability[InputT, OutputT], request: InputT
    ) -> Proposal[OutputT]:
        self.last_metadata = None
        result = await super().run(capability, request)
        self.last_metadata = result.metadata
        return result


def atomic_results(path: Path, results: list[dict[str, Any]]) -> None:
    """Durably preserve all completed derived predictions without recomputation."""
    temporary = path.with_suffix(".tmp")
    payload = canonical_json({"schema_version": "phase6a-results-v1", "records": results}) + "\n"
    with temporary.open("wb") as output:
        output.write(payload.encode())
        output.flush()
        os.fsync(output.fileno())
    os.replace(temporary, path)


async def predict(
    service: JobIntelligence,
    gateway: RecordingGateway,
    case: Case,
    trial: int,
    journal: TrialJournal,
    retained: list[dict[str, Any]],
    result_path: Path,
) -> None:
    before = case.profile.content_digest
    started, tick = datetime.now(UTC), time.monotonic()
    failure_code = None
    gateway.last_metadata = None
    outcome = CaseResult(case_id=case.case_id, failure_code="not_attempted")
    cancelled = False
    try:
        result = await service.assess(case.job, case.profile)
        outcome = replace(
            CaseResult.from_result(case.case_id, result), profile_digest_before=before
        )
    except (ModelFailure, IntelligenceFailure) as failure:
        failure_code = failure.code.value
        outcome = CaseResult(
            case_id=case.case_id, failure_code=failure_code, profile_digest_before=before
        )
    except asyncio.CancelledError:
        failure_code = "cancelled_by_supervision"
        outcome = CaseResult(
            case_id=case.case_id, failure_code=failure_code, profile_digest_before=before
        )
        cancelled = True
    metadata = ()
    if gateway.last_metadata is not None:
        safe = json.loads(metadata_json(gateway.last_metadata))
        safe["identity"].pop("endpoint", None)
        metadata = (safe,)
    rows = outcome.assessment.rows if outcome.assessment else ()
    predictions = tuple(
        Prediction(
            requirement_id=row.requirement.id.root,
            opportunity_id=case.job.opportunity_id.root,
            subject=row.requirement.assertion.subject if row.requirement.assertion else None,
            kind=row.requirement.assertion.kind if row.requirement.assertion else None,
            unit=row.requirement.assertion.unit if row.requirement.assertion else None,
            minimum=row.requirement.assertion.value if row.requirement.assertion else None,
            priority=row.requirement.priority,
            status=row.status,
            declared_shortfall=row.declared_shortfall,
            claim_ids=tuple(ref.claim_id.root for ref in row.claim_refs),
            evidence_ids=tuple(ref.evidence_id.root for ref in row.evidence_refs),
        )
        for row in rows
    )
    retained.append({"trial": trial, "result": encode_result(outcome)})
    # If either checkpoint write fails supervision aborts; never silently discard
    # earlier completed results. The v2 payload is sufficient for source-first scoring.
    atomic_results(result_path, retained)
    journal.record(
        trial=trial,
        prediction=CasePrediction(
            case_id=case.case_id,
            predictions=predictions,
            failure_code=failure_code,
            metadata=metadata,
            known_claim_ids=tuple(item.id.root for item in case.profile.claims),
            known_evidence_ids=tuple(item.id.root for item in case.profile.evidence),
            profile_unchanged=before == case.profile.content_digest,
        ),
        attempt={
            "attempt_id": uuid4().hex,
            "trial": trial,
            "case_id": case.case_id,
            "started_at": started.isoformat(),
            "finished_at": datetime.now(UTC).isoformat(),
            "duration_ms": (time.monotonic() - tick) * 1000,
            "failure_code": failure_code,
            "provider_metadata_available": bool(metadata),
            "gateway_schema_valid": gateway.last_metadata is not None,
            "model_source_ids": outcome.trace.model_source_ids if outcome.trace else (),
            "deterministic_source_ids": outcome.trace.deterministic_source_ids
            if outcome.trace
            else (),
        },
    )
    print(
        canonical_json({"trial": trial, "case": case.case_id, "failure": failure_code}), flush=True
    )
    if cancelled:
        raise asyncio.CancelledError


async def run_trials(
    settings: OllamaSettings,
    selected: tuple[Case, ...],
    journal: TrialJournal,
    retained: list[dict[str, Any]],
    result_path: Path,
) -> None:
    gateway = RecordingGateway(OllamaQwenProvider(settings), capabilities=(JOB_REQUIREMENTS,))
    service = JobIntelligence(gateway)
    for trial in (1, 2, 3):
        for case in selected:
            await predict(service, gateway, case, trial, journal, retained, result_path)


async def supervise(
    inference: asyncio.Task[None], observation: asyncio.Task[int], stopped: asyncio.Event
) -> tuple[str | None, int | None]:
    abort_code = None
    samples = None
    try:
        done, _ = await asyncio.wait({observation, inference}, return_when=asyncio.FIRST_COMPLETED)
        if observation in done:
            await observation
            abort_code = "network_observation_ended_early"
        else:
            await inference
    except Exception:
        abort_code = (
            "network_inspection_failed" if observation.done() else "evaluation_pipeline_failed"
        )
    finally:
        if not inference.done():
            inference.cancel()
            await asyncio.gather(inference, return_exceptions=True)
        stopped.set()
        observed = (await asyncio.gather(observation, return_exceptions=True))[0]
        if isinstance(observed, int):
            samples = observed
        else:
            abort_code = "network_inspection_failed"
    return abort_code, samples


def gold_cases(selected: tuple[Case, ...]) -> tuple[EvaluationCase, ...]:
    """Evaluator-only composition: called after all model attempts have ended."""

    def maps(group: str, prefix: str = "") -> tuple[dict[str, Job], dict[str, Profile]]:
        chosen = [
            case for case in selected if case.group == group and case.case_id.startswith(prefix)
        ]
        return ({c.case_id: c.job for c in chosen}, {c.case_id: c.profile for c in chosen})

    supplemental = [case for case in selected if case.case_id.startswith("P6A-")]
    return (
        load_careerlab_cases(*maps("careerlab"))
        + load_old_adversarial_cases(*maps("adversarial", "P6-"))
        + load_supplemental_cases(
            {c.case_id: c.job for c in supplemental}, {c.case_id: c.profile for c in supplemental}
        )
    )


def safety_check(base: Case) -> dict[str, Any]:
    inputs = fixed_inputs("safety-inputs-v1.json")
    jobs, profiles, predictions = {}, {}, []
    for record in inputs:
        case_id = record["id"]
        job = case_job(base, case_id, record["text"])
        jobs[case_id], profiles[case_id] = job, base.profile
        segments = segment_document(job)
        term_start = job.text.index(record["term"])
        atom = ExtractedAtom(
            source_id=0,
            quote=job.text,
            term=record["term"],
            source_start=0,
            source_end=len(job.text),
            term_start=term_start,
            term_end=term_start + len(record["term"]),
            method="deterministic",
        )
        req = normalize_requirement(
            job,
            quote=job.text,
            term=record["term"],
            priority=source_priority(job.text),
            method="deterministic",
        )
        assessment = match_requirements(job, base.profile, (req,))
        predictions.append(
            CaseResult(
                case_id=case_id,
                assessment=assessment,
                trace=IntelligenceTrace(
                    segments=segments,
                    model_source_ids=(),
                    deterministic_source_ids=(0,),
                    units=(UnitTrace(source_id=0, atom=atom, requirement=req),),
                ),
            )
        )
    return evaluate_results(load_safety_cases(jobs, profiles), tuple(predictions))


def quality_gates(
    development: dict[str, Any],
    adversarial: dict[str, Any],
    semantic: dict[str, Any],
    safety: dict[str, Any],
    component: dict[str, Any],
    critical: set[str],
) -> dict[str, bool]:
    """Fixed development criteria; never infer a hiring probability."""

    def prf(metrics: dict[str, Any]) -> bool:
        return all(
            metrics[key] is not None and metrics[key] >= 0.90 for key in ("precision", "recall")
        )

    # Select critical identities from authored labels, never model decisions.
    critical_failures = [
        error for error in development["failures"] if error["requirement_id"] in critical
    ]
    combined = (development, adversarial, semantic, safety)
    return {
        "original_raw_discovery": prf(development["raw_qwen_extraction"]),
        "original_hybrid_discovery": prf(development["hybrid_extraction"]),
        "original_importance": development["importance"]["correct"] >= 22,
        "original_normalization": development["normalization"]["correct"] >= 22,
        "original_fit": development["fit"]["correct"] >= 22,
        "critical_original_meanings": not critical_failures,
        "adversarial_retention": adversarial["hybrid_extraction"]["tp"] == 24
        and adversarial["hybrid_extraction"]["fp"] == 0
        and adversarial["hybrid_extraction"]["fn"] == 0,
        "adversarial_contamination": adversarial["raw_qwen_extraction"]["fp"] == 0,
        "semantic_utility": semantic["raw_qwen_extraction"]["tp"] == 6
        and semantic["raw_qwen_extraction"]["fp"] == 0
        and semantic["raw_qwen_extraction"]["fn"] == 0,
        "safety_exact": safety["normalization"]["correct"] == 24
        and safety["fit"]["correct"] == 24
        and safety["normalization"]["correct_abstention"] == 20,
        "zero_unsafe_normalization": all(x["normalization"]["unsafe_count"] == 0 for x in combined),
        "zero_fabrication_or_promotion": all(
            x["evidence_safety_violation_count"] == 0
            and x["profile_or_source_promotion_count"] == 0
            for x in combined
        ),
        "component_exact": component["correct"] == component["total"] == 24,
        "schema_and_calls": sum(x["successful_cases"] for x in combined[:3]) == 29,
    }


def build_report(
    journal: TrialJournal,
    selected: tuple[Case, ...],
    retained: list[dict[str, Any]],
    error_code: str | None,
) -> dict[str, Any]:
    if frozen_sources() != journal.frozen_sources:
        error_code = "frozen_sources_changed"
    journal.finalize(error_code)
    gold = gold_cases(selected)
    critical = {
        unit.requirement_id
        for case in gold
        if case.group == "careerlab"
        for unit in case.units
        if unit.priority == "ambiguous"
        or unit.status == "conflict"
        or unit.assertion is not None
        and unit.assertion.kind in {"experience", "language"}
    }
    safety = safety_check(selected[0])
    component = component_check(load_development(), CONTEXT, load_development_ground_truth())
    by_case = {case.case_id: case for case in selected}
    trials = []
    for trial in (1, 2, 3):
        predictions = tuple(
            decode_result(
                row["result"],
                by_case[row["result"]["case_id"]].job,
                by_case[row["result"]["case_id"]].profile,
            )
            for row in retained
            if row["trial"] == trial
        )
        groups = {}
        for group in ("careerlab", "adversarial", "semantic"):
            group_cases = tuple(case for case in gold if case.group == group)
            identifiers = {case.case_id for case in group_cases}
            groups[group] = evaluate_results(
                group_cases, tuple(row for row in predictions if row.case_id in identifiers)
            )
        gates = quality_gates(
            groups["careerlab"],
            groups["adversarial"],
            groups["semantic"],
            safety,
            component,
            critical,
        )
        trials.append(
            {
                "trial": trial,
                **groups,
                "gates": gates,
                "verdict": "GO" if all(gates.values()) else "NO_GO",
            }
        )
    schema_valid = sum(item["gateway_schema_valid"] is True for item in journal.attempts)
    return {
        "schema_version": "actual-phase6a-evaluation-v1",
        "scope": "CareerLab public development performance; no held-out or real-world accuracy",
        "accepted_base_commit": "09d765352eacfe61e6cb43c3ecc13c4338d26412",
        "capability": JOB_REQUIREMENTS.identifier,
        "requested_configuration": journal.configuration,
        "frozen_sources_sha256": journal.frozen_sources,
        "dataset_identity": development_oracle_identity(),
        "trials": trials,
        "deterministic_safety": safety,
        "deterministic_component": component,
        "attempts": journal.attempts,
        "model_metadata": [asdict(row)["metadata"] for _, row in journal.records],
        "planned_calls": 87,
        "attempted_calls": len(journal.attempts),
        "gateway_schema_valid_calls": schema_valid,
        "evaluation_abort_code": error_code,
        "verdict": "GO"
        if error_code is None
        and len(journal.attempts) == schema_valid == 87
        and all(item["verdict"] == "GO" for item in trials)
        else "NO_GO",
    }


async def verify() -> bool:
    settings = OllamaSettings.from_environment()
    if settings.model != "qwen3:4b-instruct":
        raise ValueError("The preregistered run requires its unchanged local model")
    settings = replace(
        settings,
        generation=GenerationSettings(
            timeout_seconds=120,
            context_tokens=4096,
            max_output_tokens=512,
        ),
    )
    executable = shutil.which("ollama")
    if executable is None:
        raise RuntimeError("Installed Ollama required")
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    local = replace(settings, base_url=f"http://127.0.0.1:{port}")
    selected = cases()
    run_id = uuid4().hex
    journal = TrialJournal(
        path=ROOT / f"evaluation-runs/phase6a-{run_id}.checkpoint.json",
        case_ids=tuple(case.case_id for case in selected),
        configuration={"provider": "ollama", "model": local.model, **asdict(local.generation)},
        frozen_sources=frozen_sources(),
    )
    result_path = ROOT / f"evaluation-runs/phase6a-{run_id}.results.json"
    retained: list[dict[str, Any]] = []
    atomic_results(result_path, retained)
    process: subprocess.Popen[bytes] | None = None
    abort_code, samples = None, None
    started = datetime.now(UTC).isoformat()
    verified = False
    try:
        process = subprocess.Popen(
            [executable, "serve"],
            env=server_environment(port),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        async with asyncio.timeout(15):
            async with httpx.AsyncClient(
                trust_env=False, follow_redirects=False, timeout=1
            ) as client:
                while True:
                    if process.poll() is not None:
                        raise RuntimeError("Owned server exited")
                    try:
                        response = await client.get(local.base_url + "/api/status")
                        if (
                            response.status_code == 200
                            and response.json().get("cloud", {}).get("disabled") is True
                        ):
                            break
                    except (httpx.ConnectError, httpx.TimeoutException):
                        pass
                    await asyncio.sleep(0.2)
        inspected = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                f"Get-NetTCPConnection -State Listen -LocalPort {port} | "
                "Select-Object LocalAddress,OwningProcess | ConvertTo-Json -Compress",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if inspected.returncode != 0 or json.loads(inspected.stdout) != {
            "LocalAddress": "127.0.0.1",
            "OwningProcess": process.pid,
        }:
            raise RuntimeError("Owned loopback identity unverified")
        verified = True
        stopped = asyncio.Event()
        observation = asyncio.create_task(observe_network(process.pid, stopped))
        inference = asyncio.create_task(run_trials(local, selected, journal, retained, result_path))
        abort_code, samples = await supervise(inference, observation, stopped)
    except asyncio.CancelledError:
        # First cancellation preserves attempts and produces a partial NO-GO
        # after owned cleanup. Repeated/forced process termination is not recoverable.
        abort_code = "cancelled_by_supervision"
    except (
        RuntimeError,
        TimeoutError,
        OSError,
        ValueError,
        subprocess.TimeoutExpired,
        httpx.HTTPError,
    ):
        abort_code = "verification_environment"
    finally:
        if process is not None:
            try:
                cleanup_owned_server(process)
            except (RuntimeError, OSError, subprocess.TimeoutExpired):
                abort_code = "owned_server_cleanup_failed"
    # Cleanup is an acceptance prerequisite, not an exception after a GO report.
    report = build_report(journal, selected, retained, abort_code)
    report["run_id"] = run_id
    report["environment"] = {
        "started_at": started,
        "finished_at": datetime.now(UTC).isoformat(),
        "owned_loopback_process_verified": verified,
        "cloud_disabled": verified,
        "tcp_observation_samples": samples,
        "network_inspection": "passed" if samples is not None else "failed",
        "owned_process_cleanup": "failed"
        if abort_code == "owned_server_cleanup_failed"
        else "passed",
        "model_downloads": 0,
        "application_state_writes": 0,
    }
    destination = ROOT / f"evaluation-runs/phase6a-{run_id}.report.json"
    destination.write_text(canonical_json(report) + "\n", encoding="utf-8", newline="\n")
    print(
        canonical_json(
            {
                "evaluation": "recorded",
                "verdict": report["verdict"],
                "attempts": len(journal.attempts),
                "report": destination.relative_to(ROOT).as_posix(),
            }
        ),
        flush=True,
    )
    return bool(report["verdict"] == "GO")


if __name__ == "__main__":
    if len(sys.argv) != 1:
        print('{"evaluation":"failed","error_code":"unsupported_arguments"}')
        raise SystemExit(2)
    try:
        if not asyncio.run(verify()):
            raise SystemExit(1)
    except (ModelFailure, IntelligenceFailure) as failure:
        print(canonical_json({"evaluation": "failed", "error_code": failure.code.value}))
        raise SystemExit(1) from None
    except (
        RuntimeError,
        TimeoutError,
        OSError,
        ValueError,
        subprocess.TimeoutExpired,
        httpx.HTTPError,
    ):
        print('{"evaluation":"failed","error_code":"verification_environment"}')
        raise SystemExit(1) from None
