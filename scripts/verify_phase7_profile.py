"""Replay retained synthetic source selections; never run or retest a model.

Only the fixed accepted Phase-6A report supplies discovery IDs. Observable
catalog composition and evaluator composition reuse the accepted boundaries;
gold labels are loaded only after all deterministic runtime calls finish.
"""

import argparse
import asyncio
import hashlib
import json
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from evaluate_phase6a_live import Case, cases, gold_cases

from actual.capabilities.job_requirements import (
    JOB_REQUIREMENTS,
    ExtractionInput,
    ExtractionOutput,
    SourceSegment,
)
from actual.core.primitives import canonical_bytes
from actual.evaluation.intelligence_v2 import CaseResult, evaluate_results
from actual.job_intelligence.errors import IntelligenceFailure
from actual.job_intelligence.extraction import segment_document
from actual.job_intelligence.matching import MATCHING_VERSION
from actual.job_intelligence.service import JobIntelligence
from actual.models.contracts import (
    GenerationSettings,
    PreparedInference,
    ProviderIdentity,
    ProviderReply,
)
from actual.models.errors import ModelFailure
from actual.models.gateway import ModelGateway, canonical_json
from actual.profile.projection import evidence_backed_profile, validate_profile_view

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "docs/phase-6a/evaluation-results-v1.json"
BASELINE_SHA256 = "903990d81e2784e0c2c3fd161c3d97b8159eadedca16a3ca142dea6d45c8e2aa"
GROUPS = ("careerlab", "adversarial", "semantic")
METRIC_KEYS = (
    "gold_cases",
    "gold_units",
    "successful_cases",
    "raw_qwen_extraction",
    "hybrid_extraction",
    "importance",
    "normalization",
    "evidence_matching",
    "fit",
    "evidence_safety_violation_count",
    "profile_or_source_promotion_count",
    "failure_code_counts",
    "failure_stage_counts",
)


@dataclass(frozen=True)
class ReplaySelection:
    trial: int
    case_id: str
    source_ids: tuple[int, ...]
    explicit_ids: tuple[int, ...]


def load_baseline() -> dict[str, Any]:
    if any(path.is_symlink() or path.is_junction() for path in (BASELINE, *BASELINE.parents)):
        raise ValueError("Aliased acceptance report")
    payload = BASELINE.read_bytes()
    if hashlib.sha256(payload).hexdigest() != BASELINE_SHA256:
        raise ValueError("Accepted replay report changed")
    result: dict[str, Any] = json.loads(payload)
    return result


def _source_ids(value: object) -> tuple[int, ...]:
    if (
        type(value) is not list
        or len(value) > 32
        or any(type(item) is not int or not 0 <= item <= 31 for item in value)
        or value != sorted(set(value))
    ):
        raise ValueError("Invalid retained source selection")
    return tuple(value)


def selections(baseline: dict[str, Any], catalog: tuple[Case, ...]) -> tuple[ReplaySelection, ...]:
    """Reject incomplete, duplicated or reclassified acceptance support."""
    expected = [(trial, case.case_id) for trial in (1, 2, 3) for case in catalog]
    if len(catalog) != 29 or len({case.case_id for case in catalog}) != 29:
        raise ValueError("Accepted observable support changed")
    attempts = baseline.get("attempts")
    if (
        baseline.get("schema_version") != "actual-phase6a-evaluation-v1"
        or baseline.get("capability") != JOB_REQUIREMENTS.identifier
        or baseline.get("verdict") != "GO"
        or baseline.get("attempted_calls") != 87
        or baseline.get("gateway_schema_valid_calls") != 87
        or type(attempts) is not list
        or len(attempts) != 87
    ):
        raise ValueError("Complete accepted source selections required")
    result = []
    for index, attempt in enumerate(attempts):
        if (
            type(attempt) is not dict
            or type(attempt.get("trial")) is not int
            or (attempt.get("trial"), attempt.get("case_id")) != expected[index]
            or attempt.get("failure_code") is not None
            or attempt.get("gateway_schema_valid") is not True
        ):
            raise ValueError("Retained attempt ordering or validity changed")
        result.append(
            ReplaySelection(
                trial=attempt["trial"],
                case_id=attempt["case_id"],
                source_ids=_source_ids(attempt.get("model_source_ids")),
                explicit_ids=_source_ids(attempt.get("deterministic_source_ids")),
            )
        )
    trials = baseline.get("trials")
    if (
        type(trials) is not list
        or any(type(trial) is not dict or type(trial.get("trial")) is not int for trial in trials)
        or [trial.get("trial") for trial in trials] != [1, 2, 3]
    ):
        raise ValueError("Complete retained evaluation required")
    return tuple(result)


class RetainedSelectionProvider:
    """An in-memory provider double. No HTTP, model loading, tools or inference."""

    def __init__(self, case: Case, selected: tuple[int, ...]) -> None:
        self.identity = ProviderIdentity(
            provider="retained-selection-replay", model="phase6a-source-ids-v1", endpoint="memory"
        )
        self.settings = GenerationSettings(max_output_tokens=512)
        self.calls = 0
        self._selected = selected
        self._expected_input = ExtractionInput(
            synthetic=True,
            segments=tuple(
                SourceSegment(id=part.id, text=part.text) for part in segment_document(case.job)
            ),
        )

    async def infer(self, request: PreparedInference) -> ProviderReply:
        self.calls += 1
        # Exact closed extraction input contains only observable source segments.
        # The provider never receives a Profile, labels, expectations or metrics.
        received = ExtractionInput.model_validate_json(request.input_json)
        if (
            self.calls != 1
            or received != self._expected_input
            or request.instructions != JOB_REQUIREMENTS.instructions
            or request.output_schema_json != canonical_json(ExtractionOutput.model_json_schema())
        ):
            raise ValueError("Replay crossed the accepted extraction boundary")
        return ProviderReply(
            content=ExtractionOutput(
                schema_version="actual-job-source-output-v2", source_ids=self._selected
            ).model_dump_json(),
            model=self.identity.model,
            model_digest=None,
            server_version=None,
        )


def _identity(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


async def replay() -> dict[str, Any]:
    baseline = load_baseline()
    catalog = cases()
    retained = selections(baseline, catalog)
    by_case = {case.case_id: case for case in catalog}
    results: dict[int, list[CaseResult]] = {1: [], 2: [], 3: []}
    unchanged = 0
    projection_checks = 0
    explicit_matches = 0
    calls = 0
    for attempt in retained:
        case = by_case[attempt.case_id]
        profile_before = canonical_bytes(case.profile)
        job_before = canonical_bytes(case.job)
        as_of = max(
            [case.job.posted_at]
            + [source.collected_at for source in case.profile.evidence]
            + [source.review.reviewed_at for source in case.profile.evidence if source.review]
            + [claim.asserted_at for claim in case.profile.claims if claim.asserted_at]
            + [claim.review.reviewed_at for claim in case.profile.claims if claim.review]
        )
        view = evidence_backed_profile(case.profile, as_of=as_of)
        validate_profile_view(case.profile, view)
        view_before = canonical_bytes(view)
        provider = RetainedSelectionProvider(case, attempt.source_ids)
        gateway = ModelGateway(
            provider,
            capabilities=(JOB_REQUIREMENTS,),
            clock=lambda: datetime(2026, 10, 6, tzinfo=UTC),
            monotonic=lambda: 0.0,
        )
        try:
            result = await JobIntelligence(gateway).assess(case.job, case.profile)
            current = replace(
                CaseResult.from_result(case.case_id, result),
                profile_digest_before=view.profile_digest,
            )
            explicit_matches += result.trace.deterministic_source_ids == attempt.explicit_ids
        except (IntelligenceFailure, ModelFailure) as failure:
            current = CaseResult(case_id=case.case_id, failure_code=failure.code.value)
        calls += provider.calls
        unchanged += profile_before == canonical_bytes(
            case.profile
        ) and job_before == canonical_bytes(case.job)
        projection_checks += view_before == canonical_bytes(
            validate_profile_view(case.profile, evidence_backed_profile(case.profile, as_of=as_of))
        )
        results[attempt.trial].append(current)

    # Only this evaluator-owned stage loads hidden development answers. No
    # further gateway calls occur after gold composition begins.
    gold = gold_cases(catalog)
    trials: list[dict[str, Any]] = []
    for trial in (1, 2, 3):
        groups = {}
        for group in GROUPS:
            group_cases = tuple(case for case in gold if case.group == group)
            identifiers = {case.case_id for case in group_cases}
            observed = evaluate_results(
                group_cases,
                tuple(result for result in results[trial] if result.case_id in identifiers),
            )
            expected = baseline["trials"][trial - 1][group]
            groups[group] = {
                "matches_retained_evaluation": observed == expected,
                "changed_fields": sorted(
                    key
                    for key in set(observed) | set(expected)
                    if observed.get(key) != expected.get(key)
                ),
                "canonical_decisions_match": observed["cases"] == expected["cases"],
                "observed_evaluation_sha256": _identity(observed),
                "retained_evaluation_sha256": _identity(expected),
                "metrics": {key: observed[key] for key in METRIC_KEYS},
                "failures": observed["failures"],
            }
        trials.append({"trial": trial, "groups": groups})
    passed = calls == unchanged == projection_checks == explicit_matches == 87 and all(
        group["matches_retained_evaluation"]
        for trial in trials
        for group in trial["groups"].values()
    )
    return {
        "schema_version": "actual-phase7-profile-replay-v1",
        "scope": (
            "Deterministic replay of retained synthetic source IDs; "
            "no new model inference or AI-quality trial"
        ),
        "accepted_phase6a_commit": "bdc988a",
        "retained_report_sha256": BASELINE_SHA256,
        "capability": JOB_REQUIREMENTS.identifier,
        "matching_version": MATCHING_VERSION,
        "planned_replays": 87,
        "provider_double_calls": calls,
        "profile_and_job_unchanged": unchanged,
        "exact_projection_checks": projection_checks,
        "deterministic_selection_matches": explicit_matches,
        "gold_units_per_trial": len([unit for case in gold for unit in case.units]),
        "trials": trials,
        "verdict": "PASS" if passed else "FAIL",
    }


def write_report(path: Path, report: dict[str, Any]) -> None:
    absolute = path.absolute()
    if not absolute.resolve().is_relative_to(ROOT.resolve()) or any(
        item.is_symlink() or item.is_junction() for item in (absolute, *absolute.parents)
    ):
        raise ValueError("Replay output must remain in the unaliased project")
    with absolute.open("xb") as stream:
        stream.write((canonical_json(report) + "\n").encode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, help="Exclusively create a new replay report in the project"
    )
    arguments = parser.parse_args()
    try:
        report = asyncio.run(replay())
        if arguments.output is not None:
            write_report(arguments.output, report)
            summary = {
                key: report[key]
                for key in (
                    "schema_version",
                    "scope",
                    "verdict",
                    "retained_report_sha256",
                    "matching_version",
                    "provider_double_calls",
                    "profile_and_job_unchanged",
                    "exact_projection_checks",
                    "deterministic_selection_matches",
                    "gold_units_per_trial",
                )
            }
            summary["report_written"] = True
            print(canonical_json(summary))
        else:
            print(canonical_json(report))
        return 0 if report["verdict"] == "PASS" else 1
    except (OSError, ValueError, KeyError, TypeError):
        print(
            canonical_json(
                {
                    "schema_version": "actual-phase7-profile-replay-v1",
                    "verdict": "FAIL",
                    "failure": "replay_integrity_or_output_failure",
                }
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
