"""Independent source-first development diagnostics; labels have no runtime authority.

Only fixed public development paths are read. Source alignment precedes canonical
mapping and remains available for abstentions. The evaluator does not call runtime
normalization or matching to manufacture its expected answers.
"""

import hashlib
import json
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, TypedDict, cast

from actual.career.assessments import JobFitAssessment, RequirementAssessment
from actual.career.jobs import Job
from actual.job_intelligence.development import load_development
from actual.job_intelligence.service import IntelligenceResult, IntelligenceTrace, UnitTrace
from actual.profile.contracts import Assertion, Profile, claim_ref, evidence_ref

from .job_intelligence import FIT_STATUSES, PRIORITIES, load_development_ground_truth

ROOT = Path(__file__).resolve().parents[3]
ANNOTATIONS = ROOT / "datasets/phase6a/evaluation-annotations-v1.json"
ANNOTATIONS_SHA256 = "43043a0d297b418a60ed547c43bb90a64c8bf06f9279275d89c92f54d8d6b5a9"
EVALUATION_VERSION = "source-first-evaluation-v2"
type Group = Literal["careerlab", "adversarial", "semantic", "safety"]


class SpanFields(TypedDict):
    source_start: int
    source_end: int
    head_start: int
    head_end: int


@dataclass(frozen=True, kw_only=True)
class SourceGoldUnit:
    requirement_id: str
    source_start: int
    source_end: int
    head_start: int
    head_end: int
    concept: str | None
    assertion: Assertion | None
    priority: str
    status: str
    declared_shortfall: bool = False
    claim_ids: tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        if (
            not self.requirement_id
            or self.priority not in PRIORITIES
            or self.status not in FIT_STATUSES
        ):
            raise ValueError("Invalid authored source identity/classification")
        spans = (self.source_start, self.source_end, self.head_start, self.head_end)
        if any(type(value) is not int for value in spans) or not (
            0 <= self.source_start <= self.head_start < self.head_end <= self.source_end <= 12000
        ):
            raise ValueError("Authored source/head extents are invalid")
        if self.assertion is not None and self.assertion.subject != self.concept:
            raise ValueError("Authored concept and assertion disagree")
        if self.assertion is None and (self.status != "unknown" or self.declared_shortfall):
            raise ValueError("Authored abstention cannot establish evidence or a numeric shortfall")


@dataclass(frozen=True, kw_only=True)
class EvaluationCase:
    case_id: str
    job: Job
    profile: Profile
    units: tuple[SourceGoldUnit, ...]
    group: Group = "careerlab"

    def __post_init__(self) -> None:
        if not self.case_id or type(self.units) is not tuple or len(self.units) > 8:
            raise ValueError("Invalid bounded evaluation case")
        if self.job.classification != "synthetic" or self.profile.classification != "synthetic":
            raise ValueError("Only explicitly synthetic development evaluation is supported")
        if self.job.workspace_id != self.profile.workspace_id:
            raise ValueError("Evaluation inputs must retain scope")
        keys = [(unit.head_start, unit.head_end) for unit in self.units]
        if len(set(keys)) != len(keys) or len({u.requirement_id for u in self.units}) != len(keys):
            raise ValueError("Authored atomic source units must be unique")
        if any(unit.source_end > len(self.job.text) for unit in self.units):
            raise ValueError("Authored source extent exceeds observable text")


@dataclass(frozen=True, kw_only=True)
class CaseResult:
    case_id: str
    assessment: JobFitAssessment | None = None
    trace: IntelligenceTrace | None = None
    failure_code: str | None = None
    profile_digest_before: str | None = None

    def __post_init__(self) -> None:
        if not self.case_id or (self.assessment is None) != (self.trace is None):
            raise ValueError("A result has an assessment and trace together, or neither")
        if self.assessment is not None and self.failure_code is not None:
            raise ValueError("Failed calls cannot expose an accepted assessment")

    @classmethod
    def from_result(cls, case_id: str, result: IntelligenceResult) -> "CaseResult":
        return cls(case_id=case_id, assessment=result.assessment, trace=result.trace)


def _json(path: Path) -> dict[str, Any]:
    allowed = {
        ANNOTATIONS,
        ROOT / "datasets/phase6/development-adversarial-inputs.json",
        ROOT / "datasets/phase6/development-adversarial-oracles.json",
        *(
            ROOT / "datasets/phase6a" / name
            for name in (
                "supplemental-inputs-v1.json",
                "supplemental-oracles-v1.json",
                "safety-inputs-v1.json",
                "safety-oracles-v1.json",
            )
        ),
    }
    if path not in allowed or any(p.is_symlink() or p.is_junction() for p in (path, *path.parents)):
        raise ValueError("Only fixed non-aliased public development evaluator paths are supported")
    payload = path.read_bytes()
    if len(payload) > 200000:
        raise ValueError("Evaluator fixture exceeds its bound")
    if path == ANNOTATIONS and hashlib.sha256(payload).hexdigest() != ANNOTATIONS_SHA256:
        raise ValueError("Reviewed source annotations changed")

    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate evaluator field")
            result[key] = value
        return result

    value = json.loads(payload, object_pairs_hook=unique)
    if (
        type(value) is not dict
        or value.get("synthetic") is not True
        or type(value.get("cases")) is not list
    ):
        raise ValueError("Invalid synthetic evaluator envelope")
    return cast(dict[str, Any], value)


def _spans(text: str, quote: str, head: str) -> SpanFields:
    if text.count(quote) != 1 or quote.count(head) != 1:
        raise ValueError("Authored source/head must occur uniquely")
    start = text.index(quote)
    head_start = start + quote.index(head)
    return {
        "source_start": start,
        "source_end": start + len(quote),
        "head_start": head_start,
        "head_end": head_start + len(head),
    }


def load_careerlab_cases(
    jobs: Mapping[str, Job], profiles: Mapping[str, Profile]
) -> tuple[EvaluationCase, ...]:
    """Bind accepted 24 gold units to separately reviewed source annotations."""
    labels = load_development_ground_truth()
    sources = {item.id: item for item in load_development()}
    annotations = {item["case_id"]: item for item in _json(ANNOTATIONS)["cases"]}
    required = {item.scenario_id for item in labels}
    if set(jobs) != required or set(profiles) != required:
        raise ValueError("All seven valid development inputs are required")
    result = []
    for oracle in labels:
        case_id = oracle.scenario_id
        job, profile = jobs[case_id], profiles[case_id]
        source = sources[case_id]
        if job.text != source.jobs[0].text:
            raise ValueError("Observable development source changed")
        annotation = annotations[case_id]
        if hashlib.sha256(job.text.encode()).hexdigest() != annotation["source_text_sha256"]:
            raise ValueError("Source annotation identity changed")
        original = source.candidate.claims
        if len(original) != len(profile.claims):
            raise ValueError("Development candidate membership changed")
        claims = {}
        for old, current in zip(original, profile.claims, strict=True):
            if (old.subject, old.unit, old.value, old.status) != (
                current.assertion.subject,
                current.assertion.unit,
                current.assertion.value,
                current.status,
            ):
                raise ValueError("Development candidate facts changed")
            claims[old.id] = current.id.root
        spans = {item["requirement_id"]: item for item in annotation["units"]}
        units = []
        for gold in oracle.requirements:
            span = spans[gold.id]
            if job.text[span["source_start"] : span["source_end"]] != gold.source_quote:
                raise ValueError("Source annotation differs from accepted authored quote")
            assertion = Assertion(
                kind={"months": "experience", "cefr_level": "language", "skill_level": "skill"}[
                    gold.unit
                ],  # type: ignore[arg-type]
                subject=gold.subject,
                unit=gold.unit,
                value=gold.minimum,
            )
            units.append(
                SourceGoldUnit(
                    **span,
                    concept=gold.subject,
                    assertion=assertion,
                    priority=gold.priority,
                    status=gold.assessment,
                    declared_shortfall=gold.declared_shortfall,
                    claim_ids=tuple(claims[key] for key in gold.claim_ids),
                )
            )
        result.append(EvaluationCase(case_id=case_id, job=job, profile=profile, units=tuple(units)))
    return tuple(result)


def load_old_adversarial_cases(
    jobs: Mapping[str, Job], profiles: Mapping[str, Profile]
) -> tuple[EvaluationCase, ...]:
    labels = _json(ROOT / "datasets/phase6/development-adversarial-oracles.json")
    sources = _json(ROOT / "datasets/phase6/development-adversarial-inputs.json")
    by_source = {row["id"]: row["text"] for row in sources["cases"]}
    result = []
    for row in labels["cases"]:
        case_id = row["id"]
        if jobs[case_id].text != by_source[case_id]:
            raise ValueError("Adversarial source differs from its authored input")
        gold = row["requirements"][0]
        unit = SourceGoldUnit(
            requirement_id=case_id + ":requirement:1",
            **_spans(jobs[case_id].text, "Python at working level is essential.", "Python"),
            concept=gold["subject"],
            assertion=Assertion(
                kind=gold["kind"], subject=gold["subject"], unit=gold["unit"], value=gold["minimum"]
            ),
            priority=gold["priority"],
            status=gold["status"],
        )
        result.append(
            EvaluationCase(
                case_id=case_id,
                job=jobs[case_id],
                profile=profiles[case_id],
                units=(unit,),
                group="adversarial",
            )
        )
    if set(jobs) != set(by_source) or set(profiles) != set(by_source):
        raise ValueError("Adversarial membership changed")
    return tuple(result)


def load_supplemental_cases(
    jobs: Mapping[str, Job], profiles: Mapping[str, Profile]
) -> tuple[EvaluationCase, ...]:
    labels = _json(ROOT / "datasets/phase6a/supplemental-oracles-v1.json")
    inputs = _json(ROOT / "datasets/phase6a/supplemental-inputs-v1.json")
    sources = {row["id"]: row for row in inputs["cases"]}
    result = []
    for row in labels["cases"]:
        case_id = row["id"]
        if (
            jobs[case_id].text != sources[case_id]["text"]
            or row["kind"] != sources[case_id]["kind"]
        ):
            raise ValueError("Supplemental source or group changed")
        units = []
        for index, gold in enumerate(row["requirements"]):
            assertion = None
            if gold["expected_normalization"] == "resolved":
                assertion = Assertion(
                    kind=gold["kind"],
                    unit=gold["unit"],
                    subject=gold["subject"],
                    value=gold["minimum"],
                )
            elif any(gold[field] is not None for field in ("kind", "unit", "minimum")):
                raise ValueError("Authored abstention cannot imply a threshold")
            units.append(
                SourceGoldUnit(
                    requirement_id=f"{case_id}:requirement:{index + 1}",
                    **_spans(jobs[case_id].text, gold["source_quote"], gold["head"]),
                    concept=gold["subject"],
                    assertion=assertion,
                    priority=gold["priority"],
                    status=gold["status"],
                )
            )
        result.append(
            EvaluationCase(
                case_id=case_id,
                job=jobs[case_id],
                profile=profiles[case_id],
                units=tuple(units),
                group=row["kind"],
            )
        )
    if set(jobs) != set(sources) or set(profiles) != set(sources):
        raise ValueError("Supplemental membership changed")
    return tuple(result)


def load_safety_cases(
    jobs: Mapping[str, Job], profiles: Mapping[str, Profile]
) -> tuple[EvaluationCase, ...]:
    labels = _json(ROOT / "datasets/phase6a/safety-oracles-v1.json")
    inputs = _json(ROOT / "datasets/phase6a/safety-inputs-v1.json")
    sources = {row["id"]: row for row in inputs["cases"]}
    result = []
    for gold in labels["cases"]:
        case_id = gold["id"]
        source = sources[case_id]
        if jobs[case_id].text != source["text"]:
            raise ValueError("Safety source changed")
        assertion = None
        if gold["resolution"] == "resolved":
            assertion = Assertion(**gold["assertion"], subject=gold["canonical_concept"])
        elif gold["assertion"] is not None:
            raise ValueError("Safety abstention cannot imply an assertion")
        unit = SourceGoldUnit(
            requirement_id=case_id + ":requirement:1",
            **_spans(source["text"], source["text"], source["term"]),
            concept=gold["canonical_concept"],
            assertion=assertion,
            priority=gold["priority"],
            status=gold["status"],
            declared_shortfall=gold.get("declared_shortfall", False),
        )
        result.append(
            EvaluationCase(
                case_id=case_id,
                job=jobs[case_id],
                profile=profiles[case_id],
                units=(unit,),
                group="safety",
            )
        )
    if set(jobs) != set(sources) or set(profiles) != set(sources):
        raise ValueError("Safety membership changed")
    return tuple(result)


def _same_scope(left: Assertion, right: Assertion) -> bool:
    return (left.kind, left.subject, left.unit) == (right.kind, right.subject, right.unit)


def _eligible_row(profile: Profile, row: RequirementAssessment) -> tuple[bool, tuple[str, ...]]:
    """Independent current/scope/review checks, including unexpected positive rows."""
    errors = []
    claims = {item.id.root: item for item in profile.claims}
    evidence = {item.id.root: item for item in profile.evidence}
    requested = row.requirement.assertion
    selected_claims = []
    selected_evidence = []
    for ref in row.claim_refs:
        item = claims.get(ref.claim_id.root)
        if item is None or ref != claim_ref(item):
            errors.append("fabricated_or_stale_claim_reference")
        elif requested is None or not _same_scope(item.assertion, requested):
            errors.append("wrong_claim_scope")
        else:
            selected_claims.append(item)
    for source_ref in row.evidence_refs:
        record = evidence.get(source_ref.evidence_id.root)
        if record is None or source_ref != evidence_ref(record):
            errors.append("fabricated_or_stale_evidence_reference")
        elif requested is None or not _same_scope(record.assertion, requested):
            errors.append("wrong_evidence_scope")
        else:
            selected_evidence.append(record)
    if row.status in ("supported", "partial"):
        if row.requirement.constraints.experience_scope == "legacy_backend":
            # Accepted Profile months do not carry an employment/project/backend
            # category. Even a large reviewed generic duration cannot prove it.
            errors.append("unsupported_experience_scope")
        if requested is None:
            errors.append("positive_abstention")
        else:
            contrary = any(
                _same_scope(item.assertion, requested)
                and item.relation == "contradicts"
                and item._qualifies_review
                for item in profile.evidence
            )
            eligible = []
            for claim in selected_claims:
                if claim.status != "reviewed_supported":
                    continue
                linked = {ref.evidence_id.root for ref in claim.evidence_refs}
                if any(
                    item.id.root in linked
                    and item.qualifies_support
                    and item.assertion.value >= claim.assertion.value
                    for item in selected_evidence
                ):
                    eligible.append(claim)
            allowed = not contrary and any(
                claim.assertion.value >= requested.value
                if row.status == "supported"
                else requested.kind == "skill" and 0 < claim.assertion.value < requested.value
                for claim in eligible
            )
            if not allowed:
                errors.append("unsupported_positive")
    return not errors, tuple(sorted(set(errors)))


def _expected_refs(case: EvaluationCase, gold: SourceGoldUnit) -> tuple[set[str], set[str]]:
    if gold.assertion is None:
        return set(), set()
    scoped = [item for item in case.profile.claims if _same_scope(item.assertion, gold.assertion)]
    if gold.claim_ids is not None:
        scoped = [item for item in scoped if item.id.root in gold.claim_ids]
    if gold.status in ("supported", "partial", "gap"):
        reviewed = [item for item in scoped if item.status == "reviewed_supported"]
        maximum = max((item.assertion.value for item in reviewed), default=-1)
        scoped = [item for item in reviewed if item.assertion.value == maximum]
    evidence = {ref.evidence_id.root for claim in scoped for ref in claim.evidence_refs}
    if gold.status in ("supported", "partial", "gap"):
        evidence = {
            item.id.root
            for item in case.profile.evidence
            if item.id.root in evidence
            and item.qualifies_support
            and scoped
            and item.assertion.value >= scoped[0].assertion.value
        }
    if gold.status == "conflict":
        evidence |= {
            item.id.root
            for item in case.profile.evidence
            if _same_scope(item.assertion, gold.assertion)
            and item.relation == "contradicts"
            and item._qualifies_review
        }
    return {item.id.root for item in scoped}, evidence


def _source_valid(job: Job, unit: UnitTrace) -> bool:
    atom = unit.atom
    if atom is None:
        return False
    atom_valid = (
        all(
            type(value) is int
            for value in (atom.source_start, atom.source_end, atom.term_start, atom.term_end)
        )
        and atom.source_id == unit.source_id
        and 0
        <= atom.source_start
        <= atom.term_start
        < atom.term_end
        <= atom.source_end
        <= len(job.text)
        and job.text[atom.source_start : atom.source_end] == atom.quote
        and job.text[atom.term_start : atom.term_end] == atom.term
    )
    if not atom_valid or unit.requirement is None:
        return atom_valid
    requirement = unit.requirement
    # A correct canonical value cannot rescue a forged interpretation source.
    # The supplied term may retain qualifiers while the canonical concept span
    # is shorter, so compare actual extents rather than requiring bare strings.
    return (
        requirement.job_id == job.id
        and requirement.job_revision == job.revision
        and requirement.job_digest == job.content_digest
        and requirement.workspace_id == job.workspace_id
        and requirement.source_start == atom.source_start
        and requirement.source_end == atom.source_end
        and requirement.source_quote == atom.quote
        and requirement.term in atom.quote
        and (
            atom.term_start <= requirement.concept_start < requirement.concept_end <= atom.term_end
            or requirement.concept_start
            <= atom.term_start
            < atom.term_end
            <= requirement.concept_end
        )
        and job.text[requirement.concept_start : requirement.concept_end] in requirement.term
        and requirement.extraction_method == atom.method
    )


def _aligns(job: Job, gold: SourceGoldUnit, unit: UnitTrace) -> bool:
    atom = unit.atom
    if atom is None or not _source_valid(job, unit):
        return False
    # Heads may be a longer explicit phrase, e.g. backend experience. Source text
    # must preserve the complete authored clause, including ambiguity/constraints.
    head_contains = (
        atom.term_start <= gold.head_start < gold.head_end <= atom.term_end
        or gold.head_start <= atom.term_start < atom.term_end <= gold.head_end
    )
    minimum_end = gold.source_end
    if job.text[minimum_end - 1 : minimum_end] in (".", "!", "?"):
        minimum_end -= 1
    return (
        head_contains
        and atom.source_start == gold.source_start
        and minimum_end <= atom.source_end <= gold.source_end
    )


def _rate(correct: int, total: int) -> dict[str, int | float | None]:
    return {"correct": correct, "total": total, "rate": correct / total if total else None}


def _prf(tp: int, fp: int, fn: int) -> dict[str, int | float | None]:
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": tp / (tp + fp) if tp + fp else None,
        "recall": tp / (tp + fn) if tp + fn else None,
        "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None,
    }


def _classification(matrix: dict[str, dict[str, int]], labels: tuple[str, ...]) -> dict[str, Any]:
    classes = {}
    scores = []
    for label in labels:
        tp = matrix[label].get(label, 0)
        fp = sum(row.get(label, 0) for other, row in matrix.items() if other != label)
        fn = sum(value for other, value in matrix[label].items() if other != label)
        support = sum(matrix[label].values())
        score = 2 * tp / (2 * tp + fp + fn) if support and 2 * tp + fp + fn else None
        classes[label] = {"support": support, "f1": score}
        if score is not None:
            scores.append(score)
    return {
        "confusion_matrix": matrix,
        "classes": classes,
        "macro_f1_supported_classes": sum(scores) / len(scores) if scores else None,
    }


def evaluate_results(
    cases: tuple[EvaluationCase, ...], results: tuple[CaseResult, ...]
) -> dict[str, Any]:
    """Score each stage independently and retain every expected unit in denominators."""
    if not cases or len({case.case_id for case in cases}) != len(cases):
        raise ValueError("Evaluation cases must be nonempty and unique")
    expected = {case.case_id for case in cases}
    if (
        len({row.case_id for row in results}) != len(results)
        or {r.case_id for r in results} - expected
    ):
        raise ValueError("Result membership must be unique and declared")
    by_case = {row.case_id: row for row in results}
    total = sum(len(case.units) for case in cases)
    count: Counter[str] = Counter()
    importance_matrix: dict[str, dict[str, int]] = {
        label: dict.fromkeys((*PRIORITIES, "missing"), 0) for label in PRIORITIES
    }
    fit_matrix: dict[str, dict[str, int]] = {
        label: dict.fromkeys((*FIT_STATUSES, "missing"), 0) for label in FIT_STATUSES
    }
    failures: list[dict[str, Any]] = []
    case_reports: list[dict[str, Any]] = []

    def error(
        case_id: str,
        stage: str,
        code: str,
        gold_id: str | None = None,
        *,
        caused_by: str | None = None,
        observed: Any = None,
        expected_value: Any = None,
    ) -> None:
        failures.append(
            {
                "case_id": case_id,
                "stage": stage,
                "code": code,
                "requirement_id": gold_id,
                "caused_by": caused_by,
                "expected": expected_value,
                "observed": observed,
            }
        )

    for case in cases:
        result = by_case.get(
            case.case_id, CaseResult(case_id=case.case_id, failure_code="not_attempted")
        )
        start_errors = len(failures)
        units = result.trace.units if result.trace else ()
        atoms = [unit for unit in units if unit.atom is not None]
        rows = (
            {row.requirement.id.root: row for row in result.assessment.rows}
            if result.assessment
            else {}
        )
        row_errors: dict[str, tuple[str, ...]] = {}
        raw_matched: set[str] = set()
        deterministic_matched: set[str] = set()
        if result.assessment is not None:
            count["successful_cases"] += 1
            matrix = result.assessment
            if (
                matrix.job_id != case.job.id
                or matrix.job_revision != case.job.revision
                or matrix.job_digest != case.job.content_digest
                or matrix.profile_id != case.profile.id
                or matrix.profile_revision != case.profile.revision
                or matrix.profile_digest != case.profile.content_digest
                or result.profile_digest_before is not None
                and result.profile_digest_before != case.profile.content_digest
            ):
                count["profile_or_source_promotion"] += 1
                error(case.case_id, "OTHER", "source_or_profile_identity_changed")
            for observed_row in rows.values():
                valid, codes = _eligible_row(case.profile, observed_row)
                row_errors[observed_row.requirement.id.root] = codes
                if not valid:
                    for code in codes:
                        count["evidence_safety_violations"] += 1
                        error(
                            case.case_id,
                            "EVIDENCE_MATCHING",
                            code,
                            observed=observed_row.requirement.id.root,
                        )
        else:
            error(case.case_id, "OTHER", result.failure_code or "missing_case")
        if result.trace:
            segments = {segment.id: segment for segment in result.trace.segments}
            for source_id in result.trace.deterministic_source_ids:
                segment = segments.get(source_id)
                deterministic_matched.update(
                    gold.requirement_id
                    for gold in case.units
                    if segment is not None
                    and segment.start <= gold.source_start
                    and segment.end >= gold.source_end
                )
            for source_id in result.trace.model_source_ids:
                segment = segments.get(source_id)
                matching = [
                    gold
                    for gold in case.units
                    if segment is not None
                    and segment.start <= gold.source_start
                    and segment.end >= gold.source_end
                ]
                fresh = [gold for gold in matching if gold.requirement_id not in raw_matched]
                if not fresh:
                    count["raw_fp"] += 1
                    error(
                        case.case_id,
                        "EXTRACTION",
                        "unexpected_model_source_selection",
                        observed=source_id,
                    )
                else:
                    raw_matched.update(gold.requirement_id for gold in fresh)
                    count["raw_tp"] += len(fresh)
            count["raw_fn"] += len(case.units) - len(raw_matched)
            for unit in units:
                if unit.atom is None and unit.failure_code:
                    error(
                        case.case_id,
                        (unit.failure_stage or "extraction").upper(),
                        unit.failure_code,
                        observed=unit.source_id,
                    )
        else:
            count["raw_fn"] += len(case.units)
        for gold in case.units:
            if gold.requirement_id not in raw_matched:
                error(
                    case.case_id,
                    "EXTRACTION",
                    "missed_model_source_requirement",
                    gold.requirement_id,
                    observed={
                        "deterministic_selected": gold.requirement_id in deterministic_matched
                    },
                )
        aligned: dict[str, UnitTrace] = {}
        for unit in atoms:
            assert unit.atom is not None
            matching = [gold for gold in case.units if _aligns(case.job, gold, unit)]
            if len(matching) != 1:
                count["hybrid_fp"] += 1
                error(
                    case.case_id,
                    "EXTRACTION",
                    "unexpected_or_invalid_source_unit",
                    observed={
                        "source_start": unit.atom.source_start,
                        "head_start": unit.atom.term_start,
                    },
                )
                continue
            gold = matching[0]
            if gold.requirement_id in aligned:
                count["hybrid_fp"] += 1
                error(case.case_id, "EXTRACTION", "duplicate_atomic_source", gold.requirement_id)
                continue
            aligned[gold.requirement_id] = unit
            count["hybrid_tp"] += 1
        unit_reports: list[dict[str, Any]] = []
        for gold in case.units:
            discovery = {
                "raw_model_selected": gold.requirement_id in raw_matched,
                "deterministic_selected": gold.requirement_id in deterministic_matched,
            }
            aligned_unit = aligned.get(gold.requirement_id)
            if aligned_unit is None:
                count["hybrid_fn"] += 1
                importance_matrix[gold.priority]["missing"] += 1
                fit_matrix[gold.status]["missing"] += 1
                error(case.case_id, "EXTRACTION", "missed_source_requirement", gold.requirement_id)
                unit_reports.append(
                    {"requirement_id": gold.requirement_id, "root_stage": "EXTRACTION", **discovery}
                )
                continue
            requirement = aligned_unit.requirement
            if requirement is None:
                importance_matrix[gold.priority]["missing"] += 1
                fit_matrix[gold.status]["missing"] += 1
                stage = (aligned_unit.failure_stage or "normalization").upper()
                error(
                    case.case_id,
                    stage,
                    aligned_unit.failure_code or "missing_interpretation",
                    gold.requirement_id,
                )
                unit_reports.append(
                    {"requirement_id": gold.requirement_id, "root_stage": stage, **discovery}
                )
                continue
            stages = []
            if requirement.priority == gold.priority:
                count["importance"] += 1
            else:
                stages.append("IMPORTANCE_CLASSIFICATION")
                error(
                    case.case_id,
                    "IMPORTANCE_CLASSIFICATION",
                    "wrong_importance",
                    gold.requirement_id,
                    expected_value=gold.priority,
                    observed=requirement.priority,
                )
            importance_matrix[gold.priority][requirement.priority] += 1
            normalized = (
                requirement.canonical_concept == gold.concept
                and requirement.assertion == gold.assertion
            )
            if normalized:
                count["normalization"] += 1
            else:
                stages.append("NORMALIZATION")
                error(
                    case.case_id,
                    "NORMALIZATION",
                    "wrong_normalization",
                    gold.requirement_id,
                    expected_value={
                        "concept": gold.concept,
                        "assertion": gold.assertion.model_dump(mode="json")
                        if gold.assertion
                        else None,
                    },
                    observed={
                        "concept": requirement.canonical_concept,
                        "assertion": requirement.assertion.model_dump(mode="json")
                        if requirement.assertion
                        else None,
                        "resolution": requirement.resolution,
                        "reason": requirement.reason,
                    },
                )
            if gold.assertion is None:
                count["expected_abstention"] += 1
                if requirement.resolution == "abstained" and normalized:
                    count["correct_abstention"] += 1
                elif requirement.assertion is not None:
                    count["unsafe_normalization"] += 1
                    error(
                        case.case_id, "NORMALIZATION", "unsafe_false_certainty", gold.requirement_id
                    )
            else:
                count["expected_resolution"] += 1
                if normalized:
                    count["correct_resolution"] += 1
                elif requirement.assertion is not None:
                    count["unsafe_normalization"] += 1
                    error(
                        case.case_id,
                        "NORMALIZATION",
                        "incorrect_confident_normalization",
                        gold.requirement_id,
                    )
                else:
                    count["avoidable_abstention"] += 1
            row = rows.get(requirement.id.root)
            claim_ids, evidence_ids = _expected_refs(case, gold)
            refs_correct = (
                row is not None
                and not row_errors.get(requirement.id.root)
                and (
                    {ref.claim_id.root for ref in row.claim_refs},
                    {ref.evidence_id.root for ref in row.evidence_refs},
                )
                == (claim_ids, evidence_ids)
            )
            if normalized:
                count["matching_conditional_total"] += 1
                if refs_correct:
                    count["matching"] += 1
                    count["matching_conditional_correct"] += 1
                else:
                    stages.append("EVIDENCE_MATCHING")
                    error(
                        case.case_id,
                        "EVIDENCE_MATCHING",
                        "wrong_evidence_selection",
                        gold.requirement_id,
                        expected_value={
                            "claim_ids": sorted(claim_ids),
                            "evidence_ids": sorted(evidence_ids),
                        },
                    )
            elif not refs_correct:
                error(
                    case.case_id,
                    "EVIDENCE_MATCHING",
                    "evidence_selection_cascade",
                    gold.requirement_id,
                    caused_by="NORMALIZATION",
                )
            observed_status = row.status if row else "missing"
            fit_matrix[gold.status][observed_status] += 1
            status_correct = (
                row is not None
                and row.status == gold.status
                and row.declared_shortfall == gold.declared_shortfall
            )
            if status_correct:
                count["status_only"] += 1
            if normalized and status_correct and refs_correct:
                count["fit"] += 1
            else:
                cause = (
                    "NORMALIZATION"
                    if not normalized
                    else "EVIDENCE_MATCHING"
                    if not refs_correct
                    else None
                )
                if cause is None:
                    stages.append("FIT_DECISION")
                error(
                    case.case_id,
                    "FIT_DECISION",
                    "wrong_fit" if cause is None else "fit_cascade",
                    gold.requirement_id,
                    caused_by=cause,
                    expected_value={
                        "status": gold.status,
                        "declared_shortfall": gold.declared_shortfall,
                    },
                    observed={
                        "status": observed_status,
                        "declared_shortfall": row.declared_shortfall if row else None,
                    },
                )
            unit_reports.append(
                {
                    "requirement_id": gold.requirement_id,
                    "source_start": requirement.source_start,
                    "source_end": requirement.source_end,
                    "head_start": requirement.concept_start,
                    "head_end": requirement.concept_end,
                    "canonical_concept": requirement.canonical_concept,
                    "resolution": requirement.resolution,
                    "normalization_reason": requirement.reason,
                    "priority": requirement.priority,
                    "status": observed_status,
                    "root_stage": stages[0] if stages else None,
                    "independent_error_stages": stages,
                    **discovery,
                }
            )
        case_reports.append(
            {
                "case_id": case.case_id,
                "group": case.group,
                "gold_units": len(case.units),
                "hybrid_units": len(atoms),
                "call_failure": result.failure_code,
                "units": unit_reports,
                "errors": failures[start_errors:],
            }
        )
    return {
        "evaluator_version": EVALUATION_VERSION,
        "gold_cases": len(cases),
        "gold_units": total,
        "successful_cases": count["successful_cases"],
        "raw_qwen_extraction": _prf(count["raw_tp"], count["raw_fp"], count["raw_fn"]),
        "hybrid_extraction": _prf(count["hybrid_tp"], count["hybrid_fp"], count["hybrid_fn"]),
        "importance": {
            **_rate(count["importance"], total),
            **_classification(importance_matrix, PRIORITIES),
        },
        "normalization": {
            **_rate(count["normalization"], total),
            "correct_resolution": count["correct_resolution"],
            "expected_resolution": sum(u.assertion is not None for c in cases for u in c.units),
            "correct_abstention": count["correct_abstention"],
            "expected_abstention": sum(u.assertion is None for c in cases for u in c.units),
            "avoidable_abstention": count["avoidable_abstention"],
            "unsafe_count": count["unsafe_normalization"],
        },
        "evidence_matching": {
            **_rate(count["matching"], total),
            "conditional": _rate(
                count["matching_conditional_correct"], count["matching_conditional_total"]
            ),
        },
        "fit": {
            **_rate(count["fit"], total),
            **_classification(fit_matrix, FIT_STATUSES),
            "status_only": _rate(count["status_only"], total),
        },
        "evidence_safety_violation_count": count["evidence_safety_violations"],
        "profile_or_source_promotion_count": count["profile_or_source_promotion"],
        "failure_stage_counts": dict(sorted(Counter(row["stage"] for row in failures).items())),
        "failure_code_counts": dict(sorted(Counter(row["code"] for row in failures).items())),
        "failures": failures,
        "cases": case_reports,
    }
