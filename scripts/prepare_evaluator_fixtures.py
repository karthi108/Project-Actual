"""Restore only missing ignored synthetic evaluator fixtures on a fresh clone."""

import argparse
import hashlib
import json
from pathlib import Path

from actual.careerlab.codec import canonical_bytes, oracle_bytes
from actual.careerlab.dataset import (
    _distinct_roots,
    _guard_path,
    build_manifest,
    verify_development,
)
from actual.careerlab.generator import generate_development


def prepare(root: Path, materialize: bool) -> None:
    inputs = root / "datasets/development/inputs"
    evaluator = root / "datasets/ground_truth/development"
    manifest = root / "docs/office-build/careerlab-environment.json"
    _distinct_roots(inputs, evaluator, manifest)
    stored = json.loads(manifest.read_bytes())
    pairs = generate_development(stored["seed"])
    if manifest.read_bytes() != canonical_bytes(build_manifest(pairs, stored["seed"])):
        raise ValueError("Current configuration/manifest identity differs")
    expected = {row["scenario_id"]: row for row in stored["records"]}
    names = {pair.inputs.id + ".json" for pair in pairs}
    if {path.name for path in inputs.iterdir()} != names:
        raise ValueError("Frozen observable membership differs")
    if evaluator.exists() and {path.name for path in evaluator.iterdir()} - names:
        raise ValueError("Evaluator directory contains unexpected files")
    missing: list[tuple[Path, bytes]] = []
    for pair in pairs:
        name = pair.inputs.id + ".json"
        _guard_path(inputs / name, inputs)
        _guard_path(evaluator / name, evaluator)
        payload = oracle_bytes(pair.oracle)
        row = expected[pair.inputs.id]
        if (
            hashlib.sha256((inputs / name).read_bytes()).hexdigest() != row["input_sha256"]
            or hashlib.sha256(payload).hexdigest() != row["oracle_sha256"]
        ):
            raise ValueError("Frozen fixture identity differs")
        destination = evaluator / name
        if destination.exists():
            if destination.read_bytes() != payload:
                raise ValueError("Existing evaluator differs; never overwrite it")
        else:
            missing.append((destination, payload))
    if missing and not materialize:
        raise ValueError("Missing ignored evaluator fixtures; explicit materialization required")
    if missing:
        evaluator.mkdir(parents=True, exist_ok=True)
        for path, payload in missing:
            with path.open("xb") as stream:
                stream.write(payload)
    verify_development(inputs, evaluator, manifest)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--materialize", action="store_true")
    options = parser.parse_args()
    prepare(Path(__file__).resolve().parents[1], options.materialize)
    print("Eight frozen development identities verified; evaluator remains separate and ignored.")


if __name__ == "__main__":
    main()
