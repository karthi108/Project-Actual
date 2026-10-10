"""Record current configuration identity without rewriting any frozen fixture."""

import json
from pathlib import Path

from actual.careerlab.codec import canonical_bytes
from actual.careerlab.dataset import build_manifest
from actual.careerlab.generator import generate_development


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    old = json.loads((root / "datasets/manifests/careerlab-profile-env-v1.json").read_bytes())
    current = build_manifest(generate_development(old["seed"]), old["seed"])
    if current["records"] != old["records"]:
        raise ValueError("Office manifest cannot change accepted input/oracle identities")
    (root / "docs/office-build/careerlab-environment.json").write_bytes(canonical_bytes(current))
    print("Office environment identity updated; all eight frozen record identities preserved.")


if __name__ == "__main__":
    main()
