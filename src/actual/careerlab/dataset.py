"""Development-only packaging with distinct observable/evaluator roots and hashes."""

import hashlib
import json
import re
import stat
from pathlib import Path

from .codec import canonical_bytes, load_record, observable_bytes, oracle_bytes, record_data
from .contracts import FixturePair, GroundTruth, ScenarioInput, SplitMembership
from .generator import GENERATOR_VERSION, generate_development
from .splits import validate_split_isolation
from .validation import validate_pair

DATASET_VERSION = "careerlab-development-v1"
DEFAULT_SEED = 20261004
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def source_hashes() -> dict[str, str]:
    """Identity of fixture/checker sources, methodology, rubric and project configuration."""
    paths = sorted(Path(__file__).parent.glob("*.py"))
    paths += [
        REPOSITORY_ROOT / "docs/phase-1/methodology.md",
        REPOSITORY_ROOT / "docs/phase-1/rubric.md",
        REPOSITORY_ROOT / "pyproject.toml",
        REPOSITORY_ROOT / "uv.lock",
    ]
    return {
        path.relative_to(REPOSITORY_ROOT).as_posix(): sha256(path.read_bytes()) for path in paths
    }


def validate_development(pairs: tuple[FixturePair, ...]) -> None:
    if len(pairs) != 8 or len({pair.oracle.coverage for pair in pairs}) != 8:
        raise ValueError("Development release requires eight distinct coverage cases")
    for pair in pairs:
        errors = validate_pair(pair)
        if errors:
            raise ValueError(
                f"Fixture failed integrity: {pair.inputs.id}: {[e.code for e in errors]}"
            )
        if (
            pair.membership.scenario_id != pair.inputs.id
            or pair.membership.coverage != pair.oracle.coverage
        ):
            raise ValueError("Membership does not match its fixture")
        if pair.membership.split != "development":
            raise ValueError("Phase 1 packages public development data only")
    errors = validate_split_isolation(
        tuple(pair.membership for pair in pairs), tuple(pair.inputs for pair in pairs)
    )
    if errors:
        raise ValueError(f"Split plan failed integrity: {[e.code for e in errors]}")


def build_manifest(pairs: tuple[FixturePair, ...], seed: int) -> dict[str, object]:
    validate_development(pairs)
    records: list[dict[str, object]] = []
    for pair in sorted(pairs, key=lambda item: item.inputs.id):
        records.append(
            {
                "synthetic": True,
                "scenario_id": pair.inputs.id,
                "input_sha256": sha256(observable_bytes(pair.inputs)),
                "oracle_sha256": sha256(oracle_bytes(pair.oracle)),
                "membership": record_data(pair.membership),
            }
        )
    body: dict[str, object] = {
        "synthetic": True,
        "dataset_version": DATASET_VERSION,
        "generator_version": GENERATOR_VERSION,
        "input_schema": "careerlab-input-v1",
        "oracle_schema": "careerlab-oracle-v1",
        "rubric_version": "careerlab-support-v1",
        "seed": seed,
        "serialization": "UTF-8, sorted keys, compact JSON, one LF",
        "source_sha256": source_hashes(),
        "split_status": {
            "development": "public",
            "validation": "unmaterialized",
            "locked_test": "unmaterialized",
        },
        "records": records,
    }
    return {**body, "dataset_sha256": sha256(canonical_bytes(body))}


def _distinct_roots(inputs: Path, evaluator: Path, manifest: Path) -> None:
    for path in (inputs, evaluator, manifest):
        _guard_path(path, path.parent)
    a, b, m = inputs.resolve(), evaluator.resolve(), manifest.resolve()
    if a == b or a.is_relative_to(b) or b.is_relative_to(a):
        raise ValueError("Observable and evaluator directories must be separate non-nested roots")
    if m.is_relative_to(a) or m.is_relative_to(b):
        raise ValueError("Manifest/lineage metadata must stay outside both record directories")
    if any(part.casefold() == "locked_test" for p in (a, b, m) for part in p.parts):
        raise ValueError("Development command cannot read or write a locked_test path")


def _guard_path(path: Path, root: Path) -> None:
    """Inspect path metadata only; never follow an artifact alias into another boundary."""
    for part in (path.absolute(), *path.absolute().parents):
        if part.is_symlink() or part.is_junction():
            raise ValueError("Dataset paths cannot contain symlinks or junctions")
        try:
            attributes = getattr(part.stat(follow_symlinks=False), "st_file_attributes", 0)
        except FileNotFoundError:
            continue
        if attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT:
            raise ValueError("Dataset paths cannot contain reparse points")
    resolved = path.resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise ValueError("Artifact escaped its declared root")
    if any(part.casefold() == "locked_test" for part in resolved.parts):
        raise ValueError("Development artifact cannot refer to a locked_test path")


def write_development(
    inputs: Path, evaluator: Path, manifest: Path, seed: int = DEFAULT_SEED
) -> str:
    """Validate everything before writing. Never deletes data or creates other splits."""
    _distinct_roots(inputs, evaluator, manifest)
    pairs = generate_development(seed)
    data = build_manifest(pairs, seed)
    payloads: list[tuple[Path, bytes]] = []
    for pair in pairs:
        if not re.fullmatch(r"CAREER-DEV-\d{3}", pair.inputs.id):
            raise ValueError("Unexpected development filename identity")
        name = f"{pair.inputs.id}.json"
        _guard_path(inputs / name, inputs)
        _guard_path(evaluator / name, evaluator)
        payloads.extend(
            [
                (inputs / name, observable_bytes(pair.inputs)),
                (evaluator / name, oracle_bytes(pair.oracle)),
            ]
        )
    for directory in (inputs, evaluator):
        expected = {f"{pair.inputs.id}.json" for pair in pairs}
        if directory.exists() and any(
            p.name not in expected or not p.is_file() for p in directory.iterdir()
        ):
            raise ValueError(
                "Output directory contains unexpected files; choose a clean destination"
            )
    inputs.mkdir(parents=True, exist_ok=True)
    evaluator.mkdir(parents=True, exist_ok=True)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    for path, payload in payloads:
        path.write_bytes(payload)
    manifest.write_bytes(canonical_bytes(data))
    return str(data["dataset_sha256"])


def verify_development(inputs: Path, evaluator: Path, manifest: Path) -> str:
    """Verify public development files against regeneration; no frozen-split reader."""
    _distinct_roots(inputs, evaluator, manifest)
    stored = json.loads(manifest.read_bytes())
    if not isinstance(stored, dict) or type(stored.get("seed")) is not int:
        raise ValueError("Invalid development manifest")
    seed = stored["seed"]
    if stored.get("dataset_version") != DATASET_VERSION:
        raise ValueError("Unsupported development version")
    expected = build_manifest(generate_development(seed), seed)
    if manifest.read_bytes() != canonical_bytes(expected):
        raise ValueError("Manifest differs from current source/configuration identity")
    pairs: list[FixturePair] = []
    expected_names = {f"{row['scenario_id']}.json" for row in stored["records"]}
    for directory in (inputs, evaluator):
        if {p.name for p in directory.iterdir()} != expected_names:
            raise ValueError("Directory membership differs from manifest")
    for row in stored["records"]:
        name = f"{row['scenario_id']}.json"
        _guard_path(inputs / name, inputs)
        _guard_path(evaluator / name, evaluator)
        input_payload, oracle_payload = (
            (inputs / name).read_bytes(),
            (evaluator / name).read_bytes(),
        )
        if (
            sha256(input_payload) != row["input_sha256"]
            or sha256(oracle_payload) != row["oracle_sha256"]
        ):
            raise ValueError("Record hash mismatch")
        scenario = load_record(ScenarioInput, input_payload)
        oracle = load_record(GroundTruth, oracle_payload)
        membership = load_record(SplitMembership, canonical_bytes(row["membership"]))
        pairs.append(FixturePair(inputs=scenario, oracle=oracle, membership=membership))
    validate_development(tuple(pairs))
    return str(expected["dataset_sha256"])
