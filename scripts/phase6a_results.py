"""Durable bounded derived results, reconstructed without repeating inference/rules.

Only offsets, identities, structured meanings and references are serialized.
Complete prompts, responses, source text, terms and explanations are excluded.
"""

import hashlib
import json
import re
from dataclasses import asdict
from typing import Any, cast

from actual.career.assessments import JobFitAssessment, RequirementAssessment
from actual.career.jobs import Job
from actual.career.requirements import InterpretedRequirement
from actual.evaluation.intelligence_v2 import CaseResult
from actual.job_intelligence.errors import IntelligenceCode
from actual.job_intelligence.extraction import DocumentSegment, ExtractedAtom
from actual.job_intelligence.service import IntelligenceTrace, UnitTrace
from actual.profile.contracts import Profile

SCHEMA = "actual-phase6a-derived-result-v1"
MAX_BYTES = 65536


def _check_trace(result: CaseResult) -> None:
    """Check the complete retained graph before durable serialization."""
    if result.assessment is None or result.trace is None:
        return
    trace = result.trace
    if len(trace.segments) > 32 or len(trace.units) > 32:
        raise ValueError("Derived trace exceeds its bound")
    if any(
        type(segment.id) is not int or segment.id != index or type(segment.role_context) is not bool
        for index, segment in enumerate(trace.segments)
    ):
        raise ValueError("Invalid derived segment identities")
    for selected in (trace.model_source_ids, trace.deterministic_source_ids):
        if len(set(selected)) != len(selected) or any(
            type(index) is not int or not 0 <= index < len(trace.segments) for index in selected
        ):
            raise ValueError("Invalid derived source selection")
    rows = {row.requirement.id.root: row.requirement for row in result.assessment.rows}
    seen = set()
    for unit in trace.units:
        if (
            type(unit.source_id) is not int
            or not 0 <= unit.source_id < len(trace.segments)
            or unit.failure_stage not in (None, "extraction", "importance", "normalization")
            or unit.failure_code is not None
            and unit.failure_code not in {code.value for code in IntelligenceCode}
            or (unit.failure_stage is None) != (unit.failure_code is None)
        ):
            raise ValueError("Invalid closed derived unit failure/provenance")
        requirement = unit.requirement
        atom = unit.atom
        if requirement is None:
            if unit.failure_code is None or atom is None and unit.failure_stage != "extraction":
                raise ValueError("A rejected unit preserves its bounded stage and code")
            continue
        if (
            unit.failure_code is not None
            or atom is None
            or requirement.id.root in seen
            or rows.get(requirement.id.root) != requirement
        ):
            raise ValueError("Derived trace and assessment requirement graphs disagree")
        if (
            atom.source_id != unit.source_id
            or requirement.source_start != atom.source_start
            or requirement.source_end != atom.source_end
            or requirement.source_quote != atom.quote
            or requirement.extraction_method != atom.method
        ):
            raise ValueError("Derived interpretation loses its atomic source provenance")
        seen.add(requirement.id.root)
    if seen != set(rows):
        raise ValueError("Derived trace omits an assessment requirement")


def _fields(value: object, expected: set[str]) -> dict[str, Any]:
    if type(value) is not dict or set(value) != expected:
        raise ValueError("Invalid closed derived-result fields")
    return cast(dict[str, Any], value)


def _slice(job: Job, start: object, end: object) -> str:
    if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(job.text):
        raise ValueError("Invalid derived source extent")
    return job.text[start:end]


def _requirement(requirement: InterpretedRequirement) -> dict[str, Any]:
    data = requirement.model_dump(mode="json")
    quote = data.pop("source_quote")
    term = data.pop("term")
    if quote.count(term) != 1:
        raise ValueError("A derived term must retain a unique source location")
    data["term_start"] = requirement.source_start + quote.index(term)
    data["term_end"] = data["term_start"] + len(term)
    return data


def _restore_requirement(value: object, job: Job) -> InterpretedRequirement:
    if type(value) is not dict:
        raise ValueError("Invalid derived requirement")
    data = dict(cast(dict[str, Any], value))
    expected = set(InterpretedRequirement.model_fields) - {"source_quote", "term"}
    _fields(data, expected | {"term_start", "term_end"})
    data["source_quote"] = _slice(job, data["source_start"], data["source_end"])
    data["term"] = _slice(job, data.pop("term_start"), data.pop("term_end"))
    requirement = InterpretedRequirement.model_validate_json(json.dumps(data))
    if (
        requirement.job_id != job.id
        or requirement.job_revision != job.revision
        or requirement.job_digest != job.content_digest
        or requirement.workspace_id != job.workspace_id
    ):
        raise ValueError("Derived requirement belongs to another source revision")
    return requirement


def _explanation(row: RequirementAssessment) -> str:
    """Closed v2 template reconstruction; no interpretation or evidence decisions."""
    requirement = row.requirement
    if requirement.resolution == "abstained":
        return "Requirement meaning is unresolved; candidate support is not assessed."
    assert requirement.assertion is not None
    subject, needed = requirement.assertion.subject, requirement.assertion.value
    unit, value = requirement.assertion.unit, row.observed_value
    if row.reason == "reviewed_support":
        return f"Reviewed {subject} support {value} {unit} covers the stated minimum {needed}."
    if row.reason == "reviewed_skill_shortfall":
        return f"Reviewed {subject} skill level {value} is below the required level {needed}."
    if row.reason == "reviewed_threshold_shortfall":
        return f"Reviewed {subject} value {value} {unit} falls below the stated minimum {needed}."
    if row.reason == "reviewed_no_support":
        return f"Reviewed {subject} evidence explicitly records no scoped support."
    if row.reason == "conflicting_evidence":
        return f"Current reviewed {subject} evidence conflicts; resolve it before acceptance."
    return (
        f"Current reviewed support for {subject} is missing or insufficient; "
        "declarations remain unverified."
    )


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def encode_result(result: CaseResult) -> dict[str, Any]:
    _check_trace(result)
    if re.fullmatch(r"[A-Z0-9-]{1,80}", result.case_id) is None:
        raise ValueError("Only bounded declared case identifiers are retained")
    if (
        result.failure_code is not None
        and re.fullmatch(r"[a-z_]{1,80}", result.failure_code) is None
    ):
        raise ValueError("Only closed safe failure codes are retained")
    matrix = None
    trace = None
    if result.assessment is not None and result.trace is not None:
        checked = JobFitAssessment.model_validate(result.assessment)
        matrix = checked.model_dump(mode="json", exclude={"rows"})
        rows = []
        for row in checked.rows:
            if row.explanation != _explanation(row):
                raise ValueError("Arbitrary explanation content cannot be checkpointed")
            values = row.model_dump(mode="json", exclude={"requirement", "explanation"})
            values["requirement"] = _requirement(row.requirement)
            values["explanation_sha256"] = _digest(row.explanation)
            rows.append(values)
        matrix["rows"] = rows
        units = []
        for unit in result.trace.units:
            atom = asdict(unit.atom) if unit.atom is not None else None
            if atom is not None:
                atom.pop("quote")
                atom.pop("term")
            units.append(
                {
                    "source_id": unit.source_id,
                    "atom": atom,
                    "requirement": _requirement(unit.requirement) if unit.requirement else None,
                    "failure_stage": unit.failure_stage,
                    "failure_code": unit.failure_code,
                }
            )
        trace = {
            "segments": [
                {"id": s.id, "start": s.start, "end": s.end, "role_context": s.role_context}
                for s in result.trace.segments
            ],
            "model_source_ids": list(result.trace.model_source_ids),
            "deterministic_source_ids": list(result.trace.deterministic_source_ids),
            "units": units,
        }
    payload = {
        "schema_version": SCHEMA,
        "case_id": result.case_id,
        "failure_code": result.failure_code,
        "profile_digest_before": result.profile_digest_before,
        "assessment": matrix,
        "trace": trace,
    }
    if len(json.dumps(payload, sort_keys=True, allow_nan=False).encode()) > MAX_BYTES:
        raise ValueError("Derived result exceeds its bound")
    return payload


def decode_result(payload: object, job: Job, profile: Profile) -> CaseResult:
    data = _fields(
        payload,
        {
            "schema_version",
            "case_id",
            "failure_code",
            "profile_digest_before",
            "assessment",
            "trace",
        },
    )
    if (
        data["schema_version"] != SCHEMA
        or job.classification != "synthetic"
        or profile.classification != "synthetic"
    ):
        raise ValueError("Derived result version/privacy differs")
    if len(json.dumps(payload, sort_keys=True, allow_nan=False).encode()) > MAX_BYTES:
        raise ValueError("Derived result exceeds its bound")
    if data["assessment"] is None:
        if data["trace"] is not None:
            raise ValueError("Incomplete derived result")
        result = CaseResult(
            case_id=data["case_id"],
            failure_code=data["failure_code"],
            profile_digest_before=data["profile_digest_before"],
        )
        encode_result(result)
        return result
    matrix = _fields(data["assessment"], set(JobFitAssessment.model_fields))
    matrix = dict(matrix)
    restored_rows = []
    if type(matrix["rows"]) is not list or len(matrix["rows"]) > 8:
        raise ValueError("Invalid derived rows")
    for value in matrix["rows"]:
        fields = set(RequirementAssessment.model_fields) - {"explanation"}
        values = dict(_fields(value, fields | {"explanation_sha256"}))
        checksum = values.pop("explanation_sha256")
        requirement = _restore_requirement(values["requirement"], job)
        values["requirement"] = requirement.model_dump(mode="json")
        # Rendering needs only closed row scalars; domain validation follows.
        provisional = RequirementAssessment.model_validate_json(
            json.dumps({**values, "explanation": "Pending template reconstruction"})
        )
        values["explanation"] = _explanation(provisional)
        if _digest(values["explanation"]) != checksum:
            raise ValueError("Derived explanation version/content differs")
        restored_rows.append(values)
    matrix["rows"] = restored_rows
    assessment = JobFitAssessment.model_validate_json(json.dumps(matrix))
    if (
        assessment.job_id != job.id
        or assessment.job_digest != job.content_digest
        or assessment.profile_id != profile.id
        or assessment.profile_digest != profile.content_digest
        or assessment.workspace_id != job.workspace_id
        or assessment.workspace_id != profile.workspace_id
    ):
        raise ValueError("Derived result references a different source/profile")
    saved = _fields(
        data["trace"], {"segments", "model_source_ids", "deterministic_source_ids", "units"}
    )
    if type(saved["segments"]) is not list or len(saved["segments"]) > 32:
        raise ValueError("Invalid derived segments")
    segments = []
    for index, item in enumerate(saved["segments"]):
        value = _fields(item, {"id", "start", "end", "role_context"})
        if (
            type(value["id"]) is not int
            or value["id"] != index
            or type(value["role_context"]) is not bool
        ):
            raise ValueError("Derived segment identities are not consecutive")
        segments.append(
            DocumentSegment(
                value["id"],
                value["start"],
                value["end"],
                _slice(job, value["start"], value["end"]),
                value["role_context"],
            )
        )
    for key in ("model_source_ids", "deterministic_source_ids"):
        values = saved[key]
        if (
            type(values) is not list
            or len(values) > 32
            or len(set(values)) != len(values)
            or any(type(index) is not int or not 0 <= index < len(segments) for index in values)
        ):
            raise ValueError("Invalid derived source selection")
    if type(saved["units"]) is not list or len(saved["units"]) > 32:
        raise ValueError("Invalid derived atomic units")
    units = []
    for item in saved["units"]:
        values = _fields(
            item, {"source_id", "atom", "requirement", "failure_stage", "failure_code"}
        )
        if type(values["source_id"]) is not int or not 0 <= values["source_id"] < len(segments):
            raise ValueError("Invalid derived unit source")
        atom = None
        if values["atom"] is not None:
            a = _fields(
                values["atom"],
                {"source_id", "source_start", "source_end", "term_start", "term_end", "method"},
            )
            if (
                a["method"] not in ("qwen", "deterministic")
                or a["source_id"] != values["source_id"]
            ):
                raise ValueError("Invalid derived extraction provenance")
            atom = ExtractedAtom(
                quote=_slice(job, a["source_start"], a["source_end"]),
                term=_slice(job, a["term_start"], a["term_end"]),
                **a,
            )
        traced_requirement = (
            _restore_requirement(values["requirement"], job)
            if values["requirement"] is not None
            else None
        )
        units.append(
            UnitTrace(
                source_id=values["source_id"],
                atom=atom,
                requirement=traced_requirement,
                failure_stage=values["failure_stage"],
                failure_code=values["failure_code"],
            )
        )
    trace = IntelligenceTrace(
        segments=tuple(segments),
        model_source_ids=tuple(saved["model_source_ids"]),
        deterministic_source_ids=tuple(saved["deterministic_source_ids"]),
        units=tuple(units),
    )
    result = CaseResult(
        case_id=data["case_id"],
        assessment=assessment,
        trace=trace,
        failure_code=data["failure_code"],
        profile_digest_before=data["profile_digest_before"],
    )
    if encode_result(result) != payload:
        raise ValueError("Derived result cannot round-trip exactly")
    return result
