"""Read-only preservation gate for accepted and frozen evaluation artifacts."""

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def frozen_at(revision: str, prefixes: tuple[str, ...]) -> int:
    names = subprocess.check_output(
        ["git", "ls-tree", "-r", "--name-only", revision], cwd=ROOT, text=True
    ).splitlines()
    count = 0
    for name in names:
        if not name.startswith(prefixes):
            continue
        expected = subprocess.check_output(
            ["git", "rev-parse", f"{revision}:{name}"], cwd=ROOT, text=True
        ).strip()
        actual = subprocess.check_output(
            ["git", "hash-object", f"--path={name}", name], cwd=ROOT, text=True
        ).strip()
        if actual != expected:
            raise RuntimeError(f"Frozen artifact changed: {name}")
        count += 1
    return count


def main() -> None:
    accepted = frozen_at(
        "bdc988a", ("datasets/", "migrations/", "uv.lock", "docs/phase-6/", "docs/phase-6a/")
    )
    phase7 = frozen_at(
        "e23d24d", ("docs/phase-7/openapi-v1.json", "docs/phase-7/profile-replay-v1.json")
    )
    for split in ("validation", "locked_test"):
        if (ROOT / "datasets" / split).exists():
            raise RuntimeError("Reserved evaluation data was materialized")
    print(f"Preserved {accepted} accepted artifacts and {phase7} frozen Phase-7 artifacts.")


if __name__ == "__main__":
    main()
