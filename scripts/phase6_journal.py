"""Atomic synthetic evaluation checkpoints; no model content or runtime intake."""

import json
import os
import re
from dataclasses import asdict, replace
from pathlib import Path

from actual.evaluation.job_intelligence import CasePrediction, Prediction
from actual.models.gateway import canonical_json

ATTEMPT_FIELDS = {
    "attempt_id",
    "trial",
    "case_id",
    "started_at",
    "finished_at",
    "duration_ms",
    "failure_code",
    "provider_metadata_available",
    "normalization_diagnostics",
    "gateway_schema_valid",
    "stage_trace",
    "model_source_ids",
    "deterministic_source_ids",
}
CONFIG_FIELDS = {
    "provider",
    "model",
    "timeout_seconds",
    "context_tokens",
    "max_output_tokens",
    "temperature",
    "seed",
}
FORBIDDEN_FIELDS = {
    "prompt",
    "prompts",
    "raw_prompt",
    "response",
    "responses",
    "raw_response",
    "job_text",
    "quote",
    "excerpt",
    "source_text",
    "text",
    "term",
}
TRACE_FIELDS = {
    "source_id",
    "source_start",
    "source_end",
    "term_start",
    "term_end",
    "concept_start",
    "concept_end",
    "method",
    "concept",
    "kind",
    "unit",
    "value",
    "comparator",
    "priority",
    "normalization_status",
    "unresolved_reason",
    "reason",
    "experience_scope",
    "failure_stage",
    "failure_code",
    "fit_status",
    "fit_reason",
    "declared_shortfall",
    "observed_value",
    "proposal_only",
    "schema_version",
    "requirement_id",
    "claim_ids",
    "evidence_ids",
    "source_sha256",
}
TRACE_ENUMS = {
    "method": {"deterministic", "qwen"},
    "concept": {"python", "fastapi", "azure", "llm_integration", "french", "experience"},
    "kind": {"skill", "language", "experience"},
    "unit": {"skill_level", "cefr_level", "months"},
    "comparator": {"minimum", "unsupported"},
    "priority": {"essential", "preferred", "ambiguous"},
    "normalization_status": {"resolved", "abstained"},
    "experience_scope": {
        "generic",
        "legacy_backend",
        "professional",
        "internship",
        "academic",
        "personal_project",
        "open_source",
        "unknown",
    },
    "failure_stage": {"extraction", "importance", "normalization", "evidence_matching", "fit"},
    "fit_status": {"supported", "partial", "gap", "unknown", "conflict"},
    "fit_reason": {
        "reviewed_support",
        "reviewed_skill_shortfall",
        "reviewed_threshold_shortfall",
        "reviewed_no_support",
        "unreviewed_or_missing",
        "conflicting_evidence",
        "unresolved_requirement",
    },
    "schema_version": {"actual-core-v1", "actual-job-source-output-v2"},
    "unresolved_reason": {
        "unknown_term",
        "ambiguous_alias",
        "unknown_skill_level",
        "unknown_language_level",
        "unknown_experience_duration",
        "unsupported_experience_scope",
        "unsupported_version_constraint",
        "unsupported_constraint",
        "negated_requirement",
    },
}
TRACE_ENUMS["reason"] = TRACE_ENUMS["unresolved_reason"] | TRACE_ENUMS["fit_reason"]


def _validate_diagnostics(attempt: dict[str, object]) -> None:
    """Stage diagnostics contain only closed labels, numeric spans and scoped IDs."""
    for field in ("model_source_ids", "deterministic_source_ids"):
        if field not in attempt:
            continue
        identifiers = attempt[field]
        if not isinstance(identifiers, (tuple, list)) or len(identifiers) > 32:
            raise ValueError("Bounded source IDs are required")
        if any(type(item) is not int or not 0 <= item <= 31 for item in identifiers):
            raise ValueError("Source IDs require bounded exact integers")
        if tuple(identifiers) != tuple(sorted(set(identifiers))):
            raise ValueError("Source IDs must be unique and ordered")
    if "stage_trace" not in attempt:
        return
    rows = attempt["stage_trace"]
    if not isinstance(rows, (tuple, list)) or len(rows) > 32:
        raise ValueError("A bounded stage trace is required")
    for row in rows:
        if type(row) is not dict or set(row) - TRACE_FIELDS:
            raise ValueError("Stage trace fields must be explicit")
        for key, value in row.items():
            if value is None:
                continue
            if key in TRACE_ENUMS:
                if type(value) is not str or value not in TRACE_ENUMS[key]:
                    raise ValueError("Stage trace labels are closed")
            elif key in (
                "source_id",
                "source_start",
                "source_end",
                "term_start",
                "term_end",
                "concept_start",
                "concept_end",
                "value",
                "observed_value",
            ):
                maximum = (
                    31
                    if key == "source_id"
                    else 600
                    if key in ("value", "observed_value")
                    else 12000
                )
                if type(value) is not int or not 0 <= value <= maximum:
                    raise ValueError("Stage trace spans/values are bounded integers")
            elif key in ("declared_shortfall", "proposal_only"):
                if type(value) is not bool or key == "proposal_only" and value is not True:
                    raise ValueError("Stage diagnostic flags retain exact Boolean meaning")
            elif key == "failure_code":
                if type(value) is not str or re.fullmatch(r"[a-z][a-z0-9_]{0,63}", value) is None:
                    raise ValueError("Stage failure codes cannot contain exception text")
            elif key == "source_sha256":
                if type(value) is not str or re.fullmatch(r"[a-f0-9]{64}", value) is None:
                    raise ValueError("Source identity is a bounded SHA-256 digest")
            elif key == "requirement_id":
                if (
                    type(value) is not str
                    or re.fullmatch(r"requirement_[a-f0-9]{32}", value) is None
                ):
                    raise ValueError("Requirement diagnostic IDs are opaque")
            elif key in ("claim_ids", "evidence_ids"):
                prefix, maximum = ("claim", 128) if key == "claim_ids" else ("evidence", 256)
                if (
                    not isinstance(value, (tuple, list))
                    or len(value) > maximum
                    or any(
                        type(item) is not str
                        or re.fullmatch(prefix + r"_[a-f0-9]{32}", item) is None
                        for item in value
                    )
                    or len(set(value)) != len(value)
                ):
                    raise ValueError("Evidence diagnostic IDs remain bounded and opaque")


def _no_content(value: object) -> None:
    if isinstance(value, dict):
        if set(value) & FORBIDDEN_FIELDS:
            raise ValueError("Evaluation checkpoint rejects model content")
        for item in value.values():
            _no_content(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _no_content(item)


class TrialJournal:
    def __init__(
        self,
        *,
        path: Path,
        case_ids: tuple[str, ...],
        configuration: dict[str, object],
        frozen_sources: dict[str, str],
    ) -> None:
        if (
            not case_ids
            or len(set(case_ids)) != len(case_ids)
            or set(configuration) != CONFIG_FIELDS
        ):
            raise ValueError("Fixed evaluation case/configuration identities required")
        if (
            path.exists()
            or path.is_symlink()
            or path.parent.is_symlink()
            or path.parent.is_junction()
        ):
            raise ValueError("A new local checkpoint identity is required")
        self.path = path
        self.case_ids = case_ids
        self.configuration = dict(configuration)
        self.frozen_sources = dict(frozen_sources)
        self.records: list[tuple[int, CasePrediction]] = []
        self.attempts: list[dict[str, object]] = []
        self.status = "running"
        self.abort_code: str | None = None
        self._write()

    def _write(self) -> None:
        body = {
            "schema_version": "actual-phase6-evaluation-checkpoint-v1",
            "status": self.status,
            "abort_code": self.abort_code,
            "planned_trials": 3,
            "case_ids": self.case_ids,
            "requested_configuration": self.configuration,
            "frozen_sources_sha256": self.frozen_sources,
            "attempts": self.attempts,
            "records": [{"trial": trial, "prediction": asdict(row)} for trial, row in self.records],
        }
        _no_content(body)
        # Encode before touching the current valid checkpoint.
        payload = (canonical_json(body) + "\n").encode("utf-8")
        self.path.parent.mkdir(exist_ok=True)
        temporary = self.path.with_name(self.path.name + ".tmp")
        try:
            with temporary.open("wb") as output:
                output.write(payload)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, self.path)
        finally:
            temporary.unlink(missing_ok=True)

    def record(self, *, trial: int, prediction: CasePrediction, attempt: dict[str, object]) -> None:
        expected_trial = len(self.records) // len(self.case_ids) + 1
        expected_case = self.case_ids[len(self.records) % len(self.case_ids)]
        if (
            self.status != "running"
            or expected_trial > 3
            or type(trial) is not int
            or trial != expected_trial
            or prediction.case_id != expected_case
            or set(attempt) - ATTEMPT_FIELDS
            or attempt.get("trial") != trial
            or attempt.get("case_id") != expected_case
        ):
            raise ValueError("Evaluation attempts must follow the declared case/trial order")
        # Revalidate metadata/derived values before checkpointing caller objects.
        checked = replace(
            prediction,
            predictions=tuple(Prediction(**asdict(item)) for item in prediction.predictions),
            metadata=tuple(json.loads(canonical_json(item)) for item in prediction.metadata),
        )
        _no_content(asdict(checked))
        _no_content(attempt)
        _validate_diagnostics(attempt)
        # Snapshot nested diagnostics too: later caller mutation cannot rewrite an
        # already completed attempt when another checkpoint is committed.
        checked_attempt: dict[str, object] = json.loads(canonical_json(attempt))
        self.records.append((trial, checked))
        self.attempts.append(checked_attempt)
        try:
            self._write()
        except Exception:
            self.records.pop()
            self.attempts.pop()
            raise

    def finalize(self, error_code: str | None = None) -> tuple[tuple[CasePrediction, ...], ...]:
        if error_code is not None and re.fullmatch(r"[a-z][a-z0-9_]{0,63}", error_code) is None:
            raise ValueError("A fixed safe abort code is required")
        completed = len(self.records) == 3 * len(self.case_ids)
        self.abort_code = error_code or (None if completed else "evaluation_incomplete")
        self.status = "complete" if completed and self.abort_code is None else "aborted"
        self._write()
        results = {(trial, row.case_id): row for trial, row in self.records}
        return tuple(
            tuple(
                results.get(
                    (trial, case_id), CasePrediction(case_id=case_id, failure_code="not_attempted")
                )
                for case_id in self.case_ids
            )
            for trial in (1, 2, 3)
        )
