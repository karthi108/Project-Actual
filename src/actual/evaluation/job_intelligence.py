"""Pure, public-development evaluation with no inference or runtime authority.

Runtime predictions must already exist before the caller loads evaluator labels.
This module is the only Phase-6 boundary allowed to read oracle files. The small
public development corpus has no independent held-out or overall hiring labels.
"""

import hashlib
import json
import stat
from collections import Counter
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal, cast

from actual.careerlab.codec import load_record, oracle_bytes
from actual.careerlab.contracts import GroundTruth, ScenarioInput
from actual.careerlab_bridge import ImportContext, map_observable
from actual.profile.contracts import (
    Assertion,
    AssertionKind,
    AssertionUnit,
    claim_ref,
    evidence_ref,
)

type Priority = Literal["essential", "preferred", "ambiguous"]
type FitStatus = Literal["supported", "partial", "gap", "unknown", "conflict"]

PRIORITIES: tuple[Priority, ...] = ("essential", "preferred", "ambiguous")
FIT_STATUSES: tuple[FitStatus, ...] = ("supported", "partial", "gap", "unknown", "conflict")
ROOT = Path(__file__).resolve().parents[3]
ADVERSARIAL_INPUT_PATH = ROOT / "datasets/phase6/development-adversarial-inputs.json"
ADVERSARIAL_ORACLE_PATH = ROOT / "datasets/phase6/development-adversarial-oracles.json"
DEVELOPMENT_ORACLE_ROOT = ROOT / "datasets/ground_truth/development"
ACCEPTED_MANIFEST_PATH = ROOT / "datasets/manifests/careerlab-model-env-v1.json"
ACCEPTED_MANIFEST_SHA256 = "1478f970bab1a8b6e178aa3bd7d2ccb122165170560bf3ac829e1ce09932de18"
DEVELOPMENT_CASE_IDS = tuple(f"CAREER-DEV-{number:03d}" for number in range(1, 8))
ADVERSARIAL_CASE_IDS = tuple(f"P6-ADV-{number:03d}" for number in range(1, 5))
METADATA_FIELDS = {
    "request_id",
    "identity",
    "settings",
    "response_model",
    "model_digest",
    "server_version",
    "model_family",
    "quantization",
    "capability",
    "schema_version",
    "schema_sha256",
    "prompt_sha256",
    "started_at",
    "finished_at",
    "duration_ms",
    "proposal_only",
}
CRITICAL_CATEGORIES = {
    "unsupported_skill_match",
    "fabricated_reference",
    "missing_positive_evidence",
    "profile_promotion",
    "numeric_experience_error",
    "language_level_error",
    "ambiguity_lost",
    "conflict_lost",
}
ERROR_RATIONALES = {
    "unsupported_skill_match": "A positive fit state contradicts the authored available support.",
    "fabricated_reference": "A cited claim or evidence reference is absent from the input profile.",
    "missing_positive_evidence": "Positive support requires current claim and evidence references.",
    "profile_promotion": "Inference changed the input profile instead of returning a proposal.",
    "numeric_experience_error": "An explicit duration threshold is missing or incorrect.",
    "language_level_error": "An explicit language threshold is missing or normalized incorrectly.",
    "ambiguity_lost": "Ambiguous employer priority was lost or silently made definite.",
    "conflict_lost": "The conflict requirement or its contrary evidence was not preserved.",
    "model_timeout": "Inference exceeded the bounded deadline; it supplied no accepted result.",
    "schema_failure": "Provider output did not complete as an accepted bounded structured result.",
    "inference_failure": "Inference failed; all authored units remain in metric denominators.",
    "duplicate_requirement": "A duplicate opportunity/subject cannot add a true positive.",
    "hallucinated_requirement": "A predicted opportunity/subject has no authored requirement unit.",
    "missed_requirement": "An authored requirement has no aligned accepted prediction.",
    "wrong_requirement_importance": "Employer priority differs from the authored annotation.",
    "wrong_normalization": "Canonical kind/unit/minimum differs from the authored requirement.",
    "wrong_support_decision": "The evidence-support state differs from the authored rubric.",
    "wrong_declared_shortfall": "An unreviewed declared shortfall was omitted or invented.",
}


def _label(value: str) -> None:
    if type(value) is not str or not value.strip() or len(value) > 200:
        raise ValueError("Evaluation identity must be a bounded nonempty string")


@dataclass(frozen=True, kw_only=True)
class GoldRequirement:
    requirement_id: str
    opportunity_id: str
    subject: str
    kind: AssertionKind
    unit: AssertionUnit
    minimum: int
    priority: Priority
    status: FitStatus
    declared_shortfall: bool = False

    def __post_init__(self) -> None:
        for item in (self.requirement_id, self.opportunity_id, self.subject):
            _label(item)
        Assertion(kind=self.kind, subject=self.subject, unit=self.unit, value=self.minimum)
        if self.priority not in PRIORITIES or self.status not in FIT_STATUSES:
            raise ValueError("Unknown authored evaluation label")
        if type(self.declared_shortfall) is not bool:
            raise ValueError("Declared shortfall must be boolean")

    @property
    def key(self) -> tuple[str, str]:
        return self.opportunity_id, self.subject


@dataclass(frozen=True, kw_only=True)
class GoldCase:
    case_id: str
    requirements: tuple[GoldRequirement, ...]

    def __post_init__(self) -> None:
        _label(self.case_id)
        if type(self.requirements) is not tuple or not self.requirements:
            raise ValueError("An evaluation case needs authored requirement units")
        if len({item.key for item in self.requirements}) != len(self.requirements):
            raise ValueError("Gold opportunity/subject units must be unique")


@dataclass(frozen=True, kw_only=True)
class Prediction:
    requirement_id: str
    opportunity_id: str
    subject: str | None
    kind: AssertionKind | None
    unit: AssertionUnit | None
    minimum: int | None
    priority: Priority
    status: FitStatus
    declared_shortfall: bool = False
    claim_ids: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _label(self.requirement_id)
        _label(self.opportunity_id)
        if self.subject is not None:
            _label(self.subject)
        if self.priority not in PRIORITIES or self.status not in FIT_STATUSES:
            raise ValueError("Unknown prediction classification")
        if type(self.declared_shortfall) is not bool:
            raise ValueError("Declared shortfall must be boolean")
        for refs in (self.claim_ids, self.evidence_ids):
            if type(refs) is not tuple or len(set(refs)) != len(refs):
                raise ValueError("Prediction references must be unique tuples")
            for ref in refs:
                _label(ref)
        scope = (self.kind, self.unit, self.minimum)
        if any(value is not None for value in scope):
            if any(value is None for value in scope) or self.subject is None:
                raise ValueError("A normalization is complete or explicitly unresolved")
            Assertion(
                kind=cast(AssertionKind, self.kind),
                subject=self.subject,
                unit=cast(AssertionUnit, self.unit),
                value=cast(int, self.minimum),
            )

    @property
    def key(self) -> tuple[str, str | None]:
        return self.opportunity_id, self.subject


@dataclass(frozen=True, kw_only=True)
class CasePrediction:
    case_id: str
    predictions: tuple[Prediction, ...] = ()
    failure_code: str | None = None
    metadata: tuple[dict[str, object], ...] = ()
    known_claim_ids: tuple[str, ...] = ()
    known_evidence_ids: tuple[str, ...] = ()
    profile_unchanged: bool = True

    def __post_init__(self) -> None:
        _label(self.case_id)
        if self.failure_code is not None:
            _label(self.failure_code)
            if self.predictions:
                raise ValueError("Failed inference cannot expose accepted predictions")
        if type(self.profile_unchanged) is not bool:
            raise ValueError("Profile preservation must be an explicit boolean")
        for item in self.metadata:
            if type(item) is not dict or set(item) - METADATA_FIELDS:
                raise ValueError("Evaluation retains only allowlisted inference metadata")
            # Reject non-JSON values rather than silently encoding arbitrary objects.
            json.dumps(item, allow_nan=False)


@dataclass(frozen=True, kw_only=True)
class AdversarialInput:
    case_id: str
    text: str


def _checked_file(path: Path, root: Path) -> bytes:
    """Development-only readers reject aliases and any locked-test path."""
    for part in (path, *path.parents):
        if part.is_symlink() or part.is_junction():
            raise ValueError("Evaluation paths cannot contain aliases")
        try:
            flags = getattr(part.stat(follow_symlinks=False), "st_file_attributes", 0)
        except FileNotFoundError:
            continue
        if flags & stat.FILE_ATTRIBUTE_REPARSE_POINT:
            raise ValueError("Evaluation paths cannot contain reparse points")
    if not path.resolve().is_relative_to(root.resolve()) or any(
        part.casefold() == "locked_test" for part in path.parts
    ):
        raise ValueError("Only public-development evaluator paths are supported")
    payload = path.read_bytes()
    if len(payload) > 200_000:
        raise ValueError("Evaluation fixture exceeds its bound")
    return payload


def _json_object(path: Path) -> dict[str, object]:
    def unique(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate evaluator JSON field")
            result[key] = value
        return result

    payload = _checked_file(path, path.parent)
    value: object = json.loads(payload, object_pairs_hook=unique)
    if type(value) is not dict:
        raise ValueError("Evaluation fixture must be a JSON object")
    return cast(dict[str, object], value)


def development_oracle_identity() -> dict[str, object]:
    """Bind public labels to the byte-identical manifest accepted at Phase 5.

    This identity belongs in evaluator output only. Runtime/model input never
    receives manifest metadata or expected-label hashes.
    """
    payload = _checked_file(ACCEPTED_MANIFEST_PATH, ROOT)
    if hashlib.sha256(payload).hexdigest() != ACCEPTED_MANIFEST_SHA256:
        raise ValueError("Accepted development manifest identity changed")
    manifest: object = json.loads(payload)
    if type(manifest) is not dict:
        raise ValueError("Accepted development manifest must be an object")
    data = cast(dict[str, object], manifest)
    if type(data.get("records")) is not list:
        raise ValueError("Accepted development manifest records are missing")
    hashes: dict[str, str] = {}
    for record in cast(list[object], data["records"]):
        if type(record) is not dict:
            raise ValueError("Accepted development manifest record is invalid")
        row = cast(dict[str, object], record)
        case_id, digest = row.get("scenario_id"), row.get("oracle_sha256")
        if type(case_id) is not str or type(digest) is not str:
            raise ValueError("Accepted development oracle identity is missing")
        if case_id in DEVELOPMENT_CASE_IDS:
            hashes[case_id] = digest
    if set(hashes) != set(DEVELOPMENT_CASE_IDS):
        raise ValueError("Accepted development oracle membership changed")
    return {
        "accepted_milestone": "09d7653",
        "manifest_path": ACCEPTED_MANIFEST_PATH.relative_to(ROOT).as_posix(),
        "manifest_file_sha256": ACCEPTED_MANIFEST_SHA256,
        "dataset_sha256": data["dataset_sha256"],
        "rubric_version": data["rubric_version"],
        "oracle_sha256": hashes,
    }


def _oracle_hashes() -> dict[str, str]:
    return cast(dict[str, str], development_oracle_identity()["oracle_sha256"])


def _bound_oracles(oracles: tuple[GroundTruth, ...]) -> None:
    if tuple(item.scenario_id for item in oracles) != DEVELOPMENT_CASE_IDS:
        raise ValueError("Only the seven valid public-development labels are supported")
    expected = _oracle_hashes()
    for oracle in oracles:
        if hashlib.sha256(oracle_bytes(oracle)).hexdigest() != expected[oracle.scenario_id]:
            raise ValueError("Development oracle differs from its accepted manifest hash")


def load_development_ground_truth() -> tuple[GroundTruth, ...]:
    expected = _oracle_hashes()
    result: list[GroundTruth] = []
    for case_id in DEVELOPMENT_CASE_IDS:
        payload = _checked_file(DEVELOPMENT_ORACLE_ROOT / f"{case_id}.json", ROOT)
        if hashlib.sha256(payload).hexdigest() != expected[case_id]:
            raise ValueError("Development oracle differs from its accepted manifest hash")
        oracle = load_record(GroundTruth, payload)
        if oracle.scenario_id != case_id or oracle.expected_error_codes:
            raise ValueError("Unexpected development oracle identity/invalidity")
        result.append(oracle)
    if sum(len(item.requirements) for item in result) != 24:
        raise ValueError("Accepted development support count changed")
    return tuple(result)


def load_development_oracles(
    opportunity_ids: dict[str, dict[str, str]],
    *,
    oracles: tuple[GroundTruth, ...] | None = None,
) -> tuple[GoldCase, ...]:
    """Read seven public labels separately, after runtime inference has completed.

    The caller maps observable job IDs to the same opportunity identities carried
    by predictions. The invalid eighth scenario never enters the inference corpus.
    """
    if set(opportunity_ids) != set(DEVELOPMENT_CASE_IDS):
        raise ValueError("Evaluation requires the seven valid development scenarios")
    cases: list[GoldCase] = []
    labels = oracles if oracles is not None else load_development_ground_truth()
    _bound_oracles(labels)
    for oracle in labels:
        case_id = oracle.scenario_id
        requirements = tuple(
            GoldRequirement(
                requirement_id=item.id,
                opportunity_id=opportunity_ids[case_id][item.job_id],
                subject=item.subject,
                kind={"skill_level": "skill", "cefr_level": "language", "months": "experience"}[
                    item.unit
                ],  # type: ignore[arg-type]
                unit=item.unit,
                minimum=item.minimum,
                priority=item.priority,
                status=item.assessment,
                declared_shortfall=item.declared_shortfall,
            )
            for item in oracle.requirements
        )
        cases.append(GoldCase(case_id=case_id, requirements=requirements))
    if sum(len(case.requirements) for case in cases) != 24:
        raise ValueError("Accepted development support count changed")
    return tuple(cases)


def component_check(
    inputs: tuple[ScenarioInput, ...],
    context: ImportContext,
    oracles: tuple[GroundTruth, ...],
) -> dict[str, object]:
    """Check deterministic normalization/matching against 24 authored gold units.

    This deliberately supplies gold source units and priorities to isolate the
    deterministic components. It is not an extraction or model-quality measurement.
    No expected label is produced by the functions being evaluated.
    """
    from actual.job_intelligence.matching import match_requirements
    from actual.job_intelligence.normalize import normalize_requirement

    by_case = {item.id: item for item in inputs}
    _bound_oracles(oracles)
    terms = {
        "python": "Python",
        "fastapi": "FastAPI",
        "azure": "Azure",
        "french": "French",
        "experience": "experience",
        "llm_integration": "Local LLM integration",
    }
    correct = 0
    errors: list[dict[str, object]] = []
    for oracle in oracles:
        source = by_case[oracle.scenario_id]
        snapshot = map_observable(source, context)
        jobs = dict(zip((item.id for item in source.jobs), snapshot.jobs, strict=True))
        claims = dict(
            zip((item.id for item in source.candidate.claims), snapshot.profile.claims, strict=True)
        )
        source_claims = {item.id: item for item in source.candidate.claims}
        evidence = dict(
            zip(
                (item.id for item in source.candidate.evidence),
                snapshot.profile.evidence,
                strict=True,
            )
        )
        for gold in oracle.requirements:
            requirement = normalize_requirement(
                jobs[gold.job_id],
                quote=gold.source_quote,
                term=terms[gold.subject],
                priority=gold.priority,
            )
            assessment = match_requirements(jobs[gold.job_id], snapshot.profile, (requirement,))
            row = assessment.rows[0]
            normalized = (
                requirement.resolution == "resolved"
                and requirement.assertion is not None
                and (
                    requirement.assertion.subject == gold.subject
                    and requirement.assertion.unit == gold.unit
                    and requirement.assertion.value == gold.minimum
                )
            )
            fit = (
                row.status == gold.assessment and row.declared_shortfall == gold.declared_shortfall
            )
            refs_exist = all(
                ref.claim_id in {item.id for item in snapshot.profile.claims}
                for ref in row.claim_refs
            ) and all(
                ref.evidence_id in {item.id for item in snapshot.profile.evidence}
                for ref in row.evidence_refs
            )
            # Public annotations name the relevant source claim. These fixtures
            # have one scoped claim per subject, and every cited source is relevant.
            expected_claim_refs = {claim_ref(claims[source_id]) for source_id in gold.claim_ids}
            expected_evidence_refs = {
                evidence_ref(evidence[source_id])
                for claim_id in gold.claim_ids
                for source_id in source_claims[claim_id].evidence_ids
            }
            references_exact = (
                set(row.claim_refs) == expected_claim_refs
                and set(row.evidence_refs) == expected_evidence_refs
            )
            if normalized and fit and refs_exist and references_exact:
                correct += 1
            else:
                errors.append(
                    {
                        "case_id": oracle.scenario_id,
                        "requirement_id": gold.id,
                        "normalization_correct": normalized,
                        "fit_correct": fit,
                        "references_exist": refs_exist,
                        "references_exact": references_exact,
                    }
                )
    total = sum(len(item.requirements) for item in oracles)
    if total != 24:
        raise ValueError("Component support count changed")
    return {"correct": correct, "total": total, "errors": errors}


def load_adversarial_inputs() -> tuple[AdversarialInput, ...]:
    value = _json_object(ADVERSARIAL_INPUT_PATH)
    if set(value) != {"schema_version", "synthetic", "cases"} or (
        value["schema_version"] != "actual-phase6-adversarial-inputs-v1"
        or value["synthetic"] is not True
        or type(value["cases"]) is not list
    ):
        raise ValueError("Invalid adversarial input envelope")
    result: list[AdversarialInput] = []
    for item in cast(list[object], value["cases"]):
        if type(item) is not dict or set(item) != {"id", "text"}:
            raise ValueError("Adversarial inputs contain only identity and source text")
        row = cast(dict[str, object], item)
        if type(row["id"]) is not str or type(row["text"]) is not str:
            raise ValueError("Invalid adversarial source fields")
        case_id, text = row["id"], row["text"]
        if not 1 <= len(text) <= 3000:
            raise ValueError("Adversarial source length exceeds capability support")
        result.append(AdversarialInput(case_id=case_id, text=text))
    if tuple(item.case_id for item in result) != ADVERSARIAL_CASE_IDS:
        raise ValueError("Adversarial development membership changed")
    return tuple(result)


def load_adversarial_oracles(opportunity_ids: dict[str, str]) -> tuple[GoldCase, ...]:
    value = _json_object(ADVERSARIAL_ORACLE_PATH)
    if set(value) != {"schema_version", "synthetic", "base_profile_scenario", "cases"} or (
        value["schema_version"] != "actual-phase6-adversarial-oracles-v1"
        or value["synthetic"] is not True
        or value["base_profile_scenario"] != "CAREER-DEV-001"
        or type(value["cases"]) is not list
        or set(opportunity_ids) != set(ADVERSARIAL_CASE_IDS)
    ):
        raise ValueError("Invalid adversarial oracle envelope")
    cases: list[GoldCase] = []
    for item in cast(list[object], value["cases"]):
        if type(item) is not dict or set(item) != {"id", "requirements"}:
            raise ValueError("Invalid adversarial oracle case")
        row = cast(dict[str, object], item)
        case_id = row["id"]
        if type(case_id) is not str or type(row["requirements"]) is not list:
            raise ValueError("Invalid adversarial oracle fields")
        requirements: list[GoldRequirement] = []
        for index, requirement in enumerate(cast(list[object], row["requirements"])):
            if type(requirement) is not dict or set(requirement) != {
                "subject",
                "kind",
                "unit",
                "minimum",
                "priority",
                "status",
                "declared_shortfall",
            }:
                raise ValueError("Invalid adversarial authored requirement")
            requirements.append(
                GoldRequirement(
                    requirement_id=f"{case_id}:requirement:{index + 1}",
                    opportunity_id=opportunity_ids[case_id],
                    **cast(dict[str, object], requirement),  # type: ignore[arg-type]
                )
            )
        cases.append(GoldCase(case_id=case_id, requirements=tuple(requirements)))
    if tuple(item.case_id for item in cases) != ADVERSARIAL_CASE_IDS:
        raise ValueError("Adversarial oracle membership changed")
    return tuple(cases)


def adversarial_identity() -> dict[str, str]:
    return {
        "input_sha256": hashlib.sha256(_checked_file(ADVERSARIAL_INPUT_PATH, ROOT)).hexdigest(),
        "oracle_sha256": hashlib.sha256(_checked_file(ADVERSARIAL_ORACLE_PATH, ROOT)).hexdigest(),
        "schema_version": "actual-phase6-adversarial-inputs-v1",
        "split": "public-development-only",
    }


def _rate(correct: int, total: int) -> dict[str, int | float | None]:
    return {"correct": correct, "total": total, "rate": correct / total if total else None}


def _f1(tp: int, fp: int, fn: int) -> float | None:
    return 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None


def _classification_summary(
    matrix: Mapping[str, dict[str, int]], labels: tuple[str, ...]
) -> dict[str, object]:
    classes: dict[str, object] = {}
    scores: list[float] = []
    for label in labels:
        tp = matrix[label].get(label, 0)
        fp = sum(row.get(label, 0) for key, row in matrix.items() if key != label)
        fn = sum(value for key, value in matrix[label].items() if key != label)
        support = sum(matrix[label].values())
        score = _f1(tp, fp, fn)
        # Absent authored classes are explicitly unmeasured, not perfect.
        if support and score is not None:
            scores.append(score)
        classes[label] = {"support": support, "tp": tp, "fp": fp, "fn": fn, "f1": score}
    return {
        "confusion_matrix": matrix,
        "classes": classes,
        "macro_f1_supported_classes": sum(scores) / len(scores) if scores else None,
    }


def evaluate_cases(
    gold_cases: tuple[GoldCase, ...], predictions: tuple[CasePrediction, ...]
) -> dict[str, object]:
    """Score every gold unit; duplicates never inflate extraction true positives.

    Alignment uses canonical opportunity/subject, independent of minimum/priority.
    The first submitted prediction owns a key; later duplicates are false positives.
    Missing units and inference failures remain in all accuracy denominators.
    """
    if not gold_cases or len({case.case_id for case in gold_cases}) != len(gold_cases):
        raise ValueError("Gold cases must be nonempty and unique")
    if len({case.case_id for case in predictions}) != len(predictions):
        raise ValueError("Prediction case identities must be unique")
    expected = {case.case_id for case in gold_cases}
    if {case.case_id for case in predictions} - expected:
        raise ValueError("Predictions contain a case outside the evaluation corpus")
    by_case = {case.case_id: case for case in predictions}
    total = sum(len(case.requirements) for case in gold_cases)
    subject_support = Counter(item.subject for case in gold_cases for item in case.requirements)
    kind_support = Counter(item.kind for case in gold_cases for item in case.requirements)
    statuses = (*FIT_STATUSES, "missing")
    fit_matrix: dict[str, dict[str, int]] = {
        label: dict.fromkeys(statuses, 0) for label in FIT_STATUSES
    }
    importance_matrix: dict[str, dict[str, int]] = {
        label: dict.fromkeys((*PRIORITIES, "missing"), 0) for label in PRIORITIES
    }
    tp = fp = fn = importance_correct = normalization_correct = fit_correct = 0
    declaration_correct = safety_failures = successful_cases = fit_case_vectors = 0
    subject_tp: Counter[str] = Counter()
    subject_fp: Counter[str] = Counter()
    subject_fn: Counter[str] = Counter()
    failures: list[dict[str, object]] = []
    case_results: list[dict[str, object]] = []

    def error(
        case_id: str,
        category: str,
        requirement_id: str | None = None,
        *,
        expected: object = None,
        observed: object = None,
    ) -> None:
        failures.append(
            {
                "case_id": case_id,
                "category": category,
                "requirement_id": requirement_id,
                "rationale": ERROR_RATIONALES[category],
                "expected": expected,
                "observed": observed,
            }
        )

    for case in gold_cases:
        result = by_case.get(case.case_id)
        if result is None:
            result = CasePrediction(case_id=case.case_id, failure_code="missing_case")
        start_errors = len(failures)
        if result.failure_code is not None:
            category = {
                "timeout": "model_timeout",
                "invalid_output": "schema_failure",
                "output_limit": "schema_failure",
            }.get(result.failure_code, "inference_failure")
            error(case.case_id, category)
        else:
            successful_cases += 1
        if not result.profile_unchanged:
            safety_failures += 1
            error(case.case_id, "profile_promotion")
        known_claims, known_evidence = set(result.known_claim_ids), set(result.known_evidence_ids)
        gold_by_key = {item.key: item for item in case.requirements}
        aligned: dict[tuple[str, str | None], Prediction] = {}
        for item in result.predictions:
            if (
                not set(item.claim_ids) <= known_claims
                or not set(item.evidence_ids) <= known_evidence
            ):
                safety_failures += 1
                error(case.case_id, "fabricated_reference", item.requirement_id)
            if item.status in ("supported", "partial") and (
                not item.claim_ids or not item.evidence_ids
            ):
                safety_failures += 1
                error(case.case_id, "missing_positive_evidence", item.requirement_id)
            if item.key in aligned:
                fp += 1
                subject_fp[item.subject or "unresolved"] += 1
                error(case.case_id, "duplicate_requirement", item.requirement_id)
                continue
            aligned[item.key] = item
            if item.key not in gold_by_key:
                fp += 1
                subject_fp[item.subject or "unresolved"] += 1
                error(case.case_id, "hallucinated_requirement", item.requirement_id)
            else:
                tp += 1
                subject_tp[cast(str, item.subject)] += 1
        for gold in case.requirements:
            prediction = aligned.get(gold.key)
            if prediction is None:
                fn += 1
                subject_fn[gold.subject] += 1
                error(case.case_id, "missed_requirement", gold.requirement_id)
                if gold.kind == "experience":
                    error(case.case_id, "numeric_experience_error", gold.requirement_id)
                elif gold.kind == "language":
                    error(case.case_id, "language_level_error", gold.requirement_id)
                if gold.priority == "ambiguous":
                    error(case.case_id, "ambiguity_lost", gold.requirement_id)
                if gold.status == "conflict":
                    error(case.case_id, "conflict_lost", gold.requirement_id)
                fit_matrix[gold.status]["missing"] += 1
                importance_matrix[gold.priority]["missing"] += 1
                continue
            importance_matrix[gold.priority][prediction.priority] += 1
            fit_matrix[gold.status][prediction.status] += 1
            if prediction.priority == gold.priority:
                importance_correct += 1
            else:
                error(
                    case.case_id,
                    "wrong_requirement_importance",
                    gold.requirement_id,
                    expected=gold.priority,
                    observed=prediction.priority,
                )
                if gold.priority == "ambiguous":
                    error(case.case_id, "ambiguity_lost", gold.requirement_id)
            scope_correct = (prediction.kind, prediction.unit, prediction.minimum) == (
                gold.kind,
                gold.unit,
                gold.minimum,
            )
            if scope_correct:
                normalization_correct += 1
            else:
                error(
                    case.case_id,
                    "wrong_normalization",
                    gold.requirement_id,
                    expected=[gold.kind, gold.unit, gold.minimum],
                    observed=[prediction.kind, prediction.unit, prediction.minimum],
                )
                if gold.kind == "experience":
                    error(case.case_id, "numeric_experience_error", gold.requirement_id)
                elif gold.kind == "language":
                    error(case.case_id, "language_level_error", gold.requirement_id)
            if prediction.status == gold.status:
                fit_correct += 1
            else:
                error(
                    case.case_id,
                    "wrong_support_decision",
                    gold.requirement_id,
                    expected=gold.status,
                    observed=prediction.status,
                )
                if prediction.status in ("supported", "partial") and gold.status not in (
                    "supported",
                    "partial",
                ):
                    safety_failures += 1
                    error(case.case_id, "unsupported_skill_match", gold.requirement_id)
                if gold.status == "conflict":
                    error(case.case_id, "conflict_lost", gold.requirement_id)
            if prediction.declared_shortfall == gold.declared_shortfall:
                declaration_correct += 1
            else:
                error(
                    case.case_id,
                    "wrong_declared_shortfall",
                    gold.requirement_id,
                    expected=gold.declared_shortfall,
                    observed=prediction.declared_shortfall,
                )
        if len(result.predictions) == len(case.requirements) and all(
            item.key in aligned
            and aligned[item.key].status == item.status
            and aligned[item.key].declared_shortfall == item.declared_shortfall
            for item in case.requirements
        ):
            fit_case_vectors += 1
        case_results.append(
            {
                "case_id": case.case_id,
                "gold_units": len(case.requirements),
                "predicted_units": len(result.predictions),
                "inference_failure": result.failure_code,
                "metadata": list(result.metadata),
                "predictions": [asdict(item) for item in result.predictions],
                "errors": failures[start_errors:],
            }
        )
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    return {
        "gold_cases": len(gold_cases),
        "gold_units": total,
        "successful_inference_cases": successful_cases,
        "support_by_subject": dict(sorted(subject_support.items())),
        "support_by_kind": dict(sorted(kind_support.items())),
        "extraction": {
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "precision": precision,
            "recall": recall,
            "f1": _f1(tp, fp, fn),
            "by_subject": {
                subject: {
                    "support": subject_support[subject],
                    "tp": subject_tp[subject],
                    "fp": subject_fp[subject],
                    "fn": subject_fn[subject],
                    "f1": _f1(subject_tp[subject], subject_fp[subject], subject_fn[subject]),
                }
                for subject in sorted(subject_support.keys() | subject_fp.keys())
            },
        },
        "importance": {
            **_rate(importance_correct, total),
            **_classification_summary(importance_matrix, PRIORITIES),
        },
        "normalization": _rate(normalization_correct, total),
        "fit": {**_rate(fit_correct, total), **_classification_summary(fit_matrix, FIT_STATUSES)},
        "declared_shortfall": _rate(declaration_correct, total),
        "fit_case_vector_agreement": _rate(fit_case_vectors, len(gold_cases)),
        "safety_violation_count": safety_failures,
        "failure_category_counts": dict(
            sorted(Counter(cast(str, item["category"]) for item in failures).items())
        ),
        "failures": failures,
        "cases": case_results,
    }


def evaluate_trial(
    *,
    trial: int,
    development: dict[str, object],
    adversarial: dict[str, object],
    component_correct: int,
    component_total: int,
) -> dict[str, object]:
    """Apply preregistered development gates without averaging trials into success."""
    if type(trial) is not int or not 1 <= trial <= 3:
        raise ValueError("The planned run has exactly three development trials")
    extraction = cast(dict[str, object], development["extraction"])
    failures = cast(list[dict[str, object]], development["failures"])
    gates = {
        "development_support_7_cases_24_units": (
            development["gold_cases"] == 7 and development["gold_units"] == 24
        ),
        "all_development_calls_valid": development["successful_inference_cases"] == 7,
        "extraction_precision_at_least_0_90": (
            isinstance(extraction["precision"], float) and extraction["precision"] >= 0.90
        ),
        "extraction_recall_at_least_0_90": (
            isinstance(extraction["recall"], float) and extraction["recall"] >= 0.90
        ),
        "importance_at_least_22_of_24": (
            cast(dict[str, object], development["importance"])["correct"] >= 22  # type: ignore[operator]
        ),
        "normalization_at_least_22_of_24": (
            cast(dict[str, object], development["normalization"])["correct"] >= 22  # type: ignore[operator]
        ),
        "fit_at_least_22_of_24": (
            cast(dict[str, object], development["fit"])["correct"] >= 22  # type: ignore[operator]
        ),
        "deterministic_component_exact_24_of_24": component_correct == component_total == 24,
        "zero_critical_truthfulness_errors": development["safety_violation_count"] == 0
        and not any(item["category"] in CRITICAL_CATEGORIES for item in failures),
        "adversarial_support_4_cases_4_units": (
            adversarial["gold_cases"] == 4 and adversarial["gold_units"] == 4
        ),
        "all_adversarial_calls_valid": adversarial["successful_inference_cases"] == 4,
        "all_adversarial_predictions_exact": not adversarial["failures"],
    }
    return {
        "trial": trial,
        "verdict": "GO" if all(gates.values()) else "NO_GO",
        "gates": gates,
        "development": development,
        "adversarial": adversarial,
        "component_matching": {"correct": component_correct, "total": component_total},
    }


def evaluation_summary(
    trials: tuple[dict[str, object], ...], *, dataset_identity: dict[str, object]
) -> dict[str, object]:
    if tuple(item["trial"] for item in trials) != (1, 2, 3):
        raise ValueError("All three planned trials must remain in the acceptance report")
    return {
        "schema_version": "actual-phase6-evaluation-v1",
        "synthetic": True,
        "evaluation_kind": "CareerLab public development performance",
        "dataset_identity": dataset_identity,
        "adversarial_identity": adversarial_identity(),
        "development_case_support": 7,
        "distinct_source_text_support": 6,
        "requirement_support_per_trial": 24,
        "trials_are_not_independent_samples": True,
        "validation": "unmaterialized",
        "locked_test": "unmaterialized",
        "overall_recommendation_accuracy": None,
        "verdict": "GO" if all(item["verdict"] == "GO" for item in trials) else "NO_GO",
        "trials": trials,
        "limitations": [
            "One shared-ancestry development component; no held-out generalization claim.",
            "Synthetic reviewed support does not authenticate evidence or certify proficiency.",
            "No partial authored labels; separate deterministic edge tests cover partial support.",
            "No overall hiring, recommendation, CV, real-world accuracy or calibration labels.",
            "Repeated generations do not enlarge the independent support count.",
        ],
    }
