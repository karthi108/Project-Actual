"""The rejected experiment remains reconstructible independently of active rules."""

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[2]


def audit_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "phase6_provenance_audit", ROOT / "scripts/audit_phase6_provenance.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_reconstruction_is_bounded_exact_and_independent_of_active_rules(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from actual.job_intelligence import normalize

    def reject_active_rule(*args: object, **kwargs: object) -> None:
        raise AssertionError("The audit must never invoke the active normalizer")

    monkeypatch.setattr(normalize, "normalize_requirement", reject_active_rule)
    before = sys.modules["actual.job_intelligence.normalize"]
    historical = ROOT / "docs/phase-6/evaluation-results-v2.json"
    digest = hashlib.sha256(historical.read_bytes()).hexdigest()
    result = audit_module().reconstruct()
    assert result["candidate_count"] == 1124
    assert result["reconstructed_count"] == 20
    assert result["unknown_term_count"] == 13
    assert len(result["canonical_decision_decomposition"]) == 24
    assert (
        sum(row["exact_canonical_decision"] for row in result["canonical_decision_decomposition"])
        == 7
    )
    assert sys.modules["actual.job_intelligence.normalize"] is before
    assert hashlib.sha256(historical.read_bytes()).hexdigest() == digest
    recorded = json.loads((ROOT / "docs/phase-6a/failure-decomposition-v1.json").read_bytes())
    assert result == recorded


def test_archive_module_restoration_on_failure() -> None:
    module = audit_module()
    records, _ = module._read_archive()
    before = {
        name: sys.modules.get(name)
        for name in (
            "actual.career.assessments",
            "actual.job_intelligence.errors",
            "actual.job_intelligence.normalize",
        )
    }
    records["src/actual/job_intelligence/normalize.py"] = b"raise ValueError('audit failure')"
    with pytest.raises(ValueError, match="audit failure"), module.archived_rules(records):
        pass
    assert all(sys.modules.get(name) is previous for name, previous in before.items())
