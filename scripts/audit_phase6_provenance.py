"""Reconstruct bounded public synthetic provenance from the rejected UUID5 IDs.

Read-only: no inference, writes, held-out readers or active normalizer imports.
The archived, hash-checked v1 classes/rules run in this process only. This is
separate audit evidence; it never recalculates the frozen benchmark or its gates.
"""

import hashlib
import json
import re
import sys
import types
import zipfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, cast
from uuid import UUID, uuid5

from actual.career.jobs import Job
from actual.careerlab.codec import load_record
from actual.careerlab.contracts import ScenarioInput
from actual.careerlab_bridge import ImportContext, map_observable
from actual.core.primitives import ActorId, WorkspaceId

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "docs/phase-6/rejected-source-v1.zip"
MANIFEST = ROOT / "docs/phase-6/rejected-source-v1.manifest.json"
REPORT_PATH = "docs/phase-6/evaluation-results-v2.json"
NAMESPACE = UUID("4264c9a5-983f-4e3b-9bfa-295afc190a06")
CONTEXT = ImportContext(
    workspace_id=WorkspaceId("workspace_" + "6" * 32),
    actor_id=ActorId("actor_" + "6" * 32),
)


def _read_archive() -> tuple[dict[str, bytes], dict[str, Any]]:
    manifest = cast(dict[str, Any], json.loads(MANIFEST.read_bytes()))
    payload = SNAPSHOT.read_bytes()
    if hashlib.sha256(payload).hexdigest() != manifest["snapshot_sha256"]:
        raise ValueError("Rejected snapshot identity changed")
    with zipfile.ZipFile(SNAPSHOT) as archive:
        records = {name: archive.read(name) for name in manifest["files_sha256"]}
    for name, data in records.items():
        if hashlib.sha256(data).hexdigest() != manifest["files_sha256"][name]:
            raise ValueError("Rejected source identity changed")
    return records, manifest


@contextmanager
def archived_rules(records: dict[str, bytes]) -> Iterator[types.ModuleType]:
    """Install exactly three archived modules temporarily; restore module state."""
    names = (
        "actual.career.assessments",
        "actual.job_intelligence.errors",
        "actual.job_intelligence.normalize",
    )
    before = {name: sys.modules.get(name) for name in names}
    loaded: dict[str, types.ModuleType] = {}
    try:
        for name in names:
            source_path = "src/" + name.replace(".", "/") + ".py"
            module = types.ModuleType(name)
            module.__file__ = "rejected-source-v1.zip:" + source_path
            module.__package__ = name.rpartition(".")[0]
            sys.modules[name] = module
            exec(compile(records[source_path], module.__file__, "exec"), module.__dict__)
            loaded[name] = module
        yield loaded[names[-1]]
    finally:
        for name, original in before.items():
            if original is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original


def observable_jobs(records: dict[str, bytes]) -> dict[str, Job]:
    accepted = json.loads(records["datasets/manifests/careerlab-intelligence-env-v1.json"])
    expected = {row["scenario_id"]: row["input_sha256"] for row in accepted["records"]}
    jobs = {}
    for number in range(1, 8):
        case_id = f"CAREER-DEV-{number:03d}"
        data = (ROOT / f"datasets/development/inputs/{case_id}.json").read_bytes()
        if hashlib.sha256(data).hexdigest() != expected[case_id]:
            raise ValueError("Accepted observable identity changed")
        source = load_record(ScenarioInput, data)
        snapshot = map_observable(source, CONTEXT)
        jobs[case_id] = snapshot.jobs[0]
    return jobs


def candidates(job: Job) -> Iterator[tuple[int, str, str]]:
    """Finite sentence boundaries, terminal punctuation variants, token terms."""
    for sentence in re.finditer(r"[^.!?]+(?:[.!?]|$)", job.text):
        raw = sentence.group()
        stripped = raw.strip()
        start = sentence.start() + len(raw) - len(raw.lstrip())
        for quote in (stripped, stripped.rstrip(".!?")):
            if not 1 <= len(quote) <= 512 or job.text.count(quote) != 1:
                continue
            words = list(re.finditer(r"\S+", quote))
            for left in range(len(words)):
                for right in range(left, len(words)):
                    term = quote[words[left].start() : words[right].end()]
                    if len(term) > 64:
                        break
                    yield start, quote, term


def reconstruct() -> dict[str, Any]:
    records, manifest = _read_archive()
    report = cast(dict[str, Any], json.loads(records[REPORT_PATH]))
    jobs = observable_jobs(records)
    reconstructed: list[dict[str, Any]] = []
    searched = 0
    with archived_rules(records) as normalizer:
        for case in report["trials"][0]["development"]["cases"]:
            expected = {item["requirement_id"]: item for item in case["predictions"]}
            if not expected:
                continue
            job = jobs[case["case_id"]]
            prefix = f"{job.workspace_id.root}/{job.id.root}/{job.revision}/{job.content_digest}/"
            found: dict[str, tuple[int, str, str]] = {}
            for start, quote, term in candidates(job):
                searched += 1
                identity = "requirement_" + uuid5(NAMESPACE, f"{prefix}{start}/{quote}/{term}").hex
                if identity in expected:
                    if identity in found and found[identity] != (start, quote, term):
                        raise ValueError("Ambiguous reconstructed identity")
                    found[identity] = (start, quote, term)
            for identity, prediction in expected.items():
                if identity not in found:
                    reconstructed.append(
                        {"case_id": case["case_id"], "requirement_id": identity, "found": False}
                    )
                    continue
                start, quote, term = found[identity]
                requirement = normalizer.normalize_requirement(
                    job, quote=quote, term=term, priority=prediction["priority"]
                )
                for trial in report["trials"]:
                    trial_case = next(
                        row
                        for row in trial["development"]["cases"]
                        if row["case_id"] == case["case_id"]
                    )
                    actual = next(
                        row
                        for row in trial_case["predictions"]
                        if row["requirement_id"] == identity
                    )
                    if actual != prediction:
                        raise ValueError("Trial reconstruction is not common to all three trials")
                reconstructed.append(
                    {
                        "case_id": case["case_id"],
                        "requirement_id": identity,
                        "found": True,
                        "job_digest": job.content_digest,
                        "source_start": start,
                        "source_end": start + len(quote),
                        "source_quote": quote,
                        "term": term,
                        "priority": prediction["priority"],
                        "recorded_fit_status": prediction["status"],
                        "recorded_declared_shortfall": prediction["declared_shortfall"],
                        "v1_normalization_type": type(requirement).__name__,
                        "v1_normalization_reason": getattr(requirement, "reason", None),
                        "v1_subject": getattr(
                            getattr(requirement, "assertion", None), "subject", None
                        ),
                        "all_three_trial_records_identical": True,
                    }
                )
    result: dict[str, Any] = {
        "schema_version": "actual-phase6a-provenance-audit-v1",
        "synthetic": True,
        "evidence_kind": "source-derived reconstruction, not retained raw model output",
        "snapshot_sha256": manifest["snapshot_sha256"],
        "source_report_sha256": manifest["files_sha256"][REPORT_PATH],
        "archived_normalizer_sha256": manifest["files_sha256"][
            "src/actual/job_intelligence/normalize.py"
        ],
        "candidate_count": searched,
        "reconstructed_count": sum(row["found"] for row in reconstructed),
        "unknown_term_count": sum(
            row.get("v1_normalization_reason") == "unknown_term" for row in reconstructed
        ),
        "reconstruction": reconstructed,
        "historical_metrics_and_verdict_unchanged": True,
        "limitations": [
            "Only the 20 retained requirement IDs can be reconstructed.",
            "Rejected DEV006 units and empty outputs have no retained IDs to reconstruct.",
            "This finite search never reconstructs the complete prompt or wire response.",
            "UUID identity verifies the candidate provenance, not factual model truth.",
        ],
    }
    result["canonical_decision_decomposition"] = decomposition(records, reconstructed)
    result["adversarial_decomposition"] = [
        {
            "case_id": f"P6-ADV-{number:03d}",
            "expected_subject": "python",
            "primary_stage": "EXTRACTION",
            "related_stage": "PROMPT_INJECTION_ADVERSARIAL_HANDLING",
            "observed": "schema-valid empty requirement array",
            "limitation": "Omission is observed; model intent or instruction obedience is unknown.",
        }
        for number in range(1, 5)
    ]
    return result


def decomposition(
    records: dict[str, bytes], reconstructed: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    accepted = json.loads(records["datasets/manifests/careerlab-intelligence-env-v1.json"])
    hashes = {row["scenario_id"]: row["oracle_sha256"] for row in accepted["records"]}
    result = []
    for number in range(1, 8):
        case_id = f"CAREER-DEV-{number:03d}"
        payload = (ROOT / f"datasets/ground_truth/development/{case_id}.json").read_bytes()
        if hashlib.sha256(payload).hexdigest() != hashes[case_id]:
            raise ValueError("Accepted oracle identity changed")
        gold = json.loads(payload)
        for unit in gold["requirements"]:
            matched = [
                row
                for row in reconstructed
                if row["case_id"] == case_id
                and row.get("source_quote") == unit["source_quote"].rstrip(".!?")
            ]
            row: dict[str, Any] = {
                "case_id": case_id,
                "authored_requirement_id": unit["id"],
                "subject": unit["subject"],
                "expected_priority": unit["priority"],
                "expected_fit": unit["assessment"],
                "expected_declared_shortfall": unit["declared_shortfall"],
            }
            if len(matched) == 1:
                item = matched[0]
                row.update(
                    {
                        "reconstructed_requirement_id": item["requirement_id"],
                        "source_discovery": "verified exact clause, terminal period omitted",
                        "observed_priority": item["priority"],
                        "observed_fit": item["recorded_fit_status"],
                        "normalization_reason": item["v1_normalization_reason"],
                        "primary_stage": (
                            "NORMALIZATION_INTERFACE"
                            if item["v1_normalization_reason"] == "unknown_term"
                            else "NONE"
                        ),
                        "exact_canonical_decision": item["v1_subject"] == unit["subject"],
                    }
                )
            elif case_id == "CAREER-DEV-006":
                row.update(
                    {
                        "exact_canonical_decision": False,
                        "observed_fit": "no assessment",
                        "primary_stage": (
                            "IMPORTANCE_CLASSIFICATION" if unit["subject"] == "azure" else "OTHER"
                        ),
                        "root_cause": (
                            "Proposed/clipped preferred wording contradicts full ambiguous context."
                            if unit["subject"] == "azure"
                            else (
                                "Case-wide rejection cascades from Azure's "
                                "context/priority failure."
                            )
                        ),
                        "limitation": (
                            "Rejected source spans/terms were not retained or reconstructed."
                        ),
                    }
                )
            elif case_id == "CAREER-DEV-007":
                row.update(
                    {
                        "exact_canonical_decision": False,
                        "observed_fit": "omitted requirement",
                        "primary_stage": "EXTRACTION",
                        "related_stage": "PROMPT_INJECTION_ADVERSARIAL_HANDLING",
                        "limitation": (
                            "Model intent and causal reason for the empty array are unknown."
                        ),
                    }
                )
            else:
                raise ValueError("Unexpected unmatched authored audit unit")
            result.append(row)
    if len(result) != 24:
        raise ValueError("Canonical audit denominator changed")
    return result


def main() -> int:
    if len(sys.argv) != 1:
        return 2
    print(json.dumps(reconstruct(), ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
