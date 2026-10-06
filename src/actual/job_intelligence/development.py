"""Closed development input catalog; no oracle/manifest or arbitrary intake."""

import hashlib
from pathlib import Path

from actual.careerlab.codec import load_record
from actual.careerlab.contracts import ScenarioInput
from actual.job_intelligence.errors import IntelligenceFailure

_ROOT = Path(__file__).resolve().parents[3]
# Public observable identities from accepted Phase 5, deliberately separated
# from manifests (which carry evaluator lineage/categories/answer hashes).
INPUT_HASHES = {
    "CAREER-DEV-001": "04e9d748eb8967f8548c3f3f5e98b3e02388b40e86dc4858426f3c5933e88c42",
    "CAREER-DEV-002": "3beae9a4cc4562a3b20aad38cb15966e656c056c2b0184da8517bbc5eefc6091",
    "CAREER-DEV-003": "228dc0d5ea6beadc732b4cb86b805cddd83a34a773b34e843b2e9c6ea0b9740a",
    "CAREER-DEV-004": "ca9a2ee1065b84c0995d80212408dbe131e92ea3e698fe9a26ef05d283d50971",
    "CAREER-DEV-005": "f3ffaf5fae879195a9ef1793ea2eea4110d9a58767706b2505d08d67414da475",
    "CAREER-DEV-006": "ef960a87174f0d0d7e21187110d9a0b480c6be0662a88a7f6795e6eec672d7d9",
    "CAREER-DEV-007": "f3312df81ca6029ecaeb38bb7dd457fb72d59859868ea54f4e48c87f358f8312",
    "CAREER-DEV-008": "7248c075a39630d6cf80ea99f23b6d8d033a3750685b20f2dba87fbcdcf683bb",
}


def load_development() -> tuple[ScenarioInput, ...]:
    """Read eight fixed, unchanged public inputs, without evaluator artifacts."""
    result = []
    for scenario_id, digest in INPUT_HASHES.items():
        payload = (
            _ROOT / "datasets" / "development" / "inputs" / f"{scenario_id}.json"
        ).read_bytes()
        if hashlib.sha256(payload).hexdigest() != digest:
            raise IntelligenceFailure("input_rejected")
        value = load_record(ScenarioInput, payload)
        if value.id != scenario_id:
            raise IntelligenceFailure("input_rejected")
        result.append(value)
    return tuple(result)
