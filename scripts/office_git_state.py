"""Read-only phase/HEAD inventory; no remote URLs, private content or Git mutation."""

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = "bdc988ae7cc00379e6b90f1cf22e6c6de192be61"


def git(*arguments: str) -> str:
    return subprocess.check_output(["git", *arguments], cwd=ROOT, text=True).strip()


def main() -> None:
    records = git("log", "--format=%H %s", BASE + "..HEAD").splitlines()
    checkpoints = []
    for phase in range(7, 28):
        matches = [row for row in records if row[41:].startswith(f"wip(phase-{phase}):")]
        if len(matches) != 1:
            raise ValueError("Expected exactly one checkpoint per phase")
        row = matches[0]
        checkpoints.append({"phase": phase, "commit": row[:40], "subject": row[41:]})
    print(
        json.dumps(
            {
                "branch": git("branch", "--show-current"),
                "accepted_base": BASE,
                "head": git("rev-parse", "HEAD"),
                "working_tree_clean": not git("status", "--porcelain"),
                "remote_names": git("remote").splitlines(),
                "checkpoints": checkpoints,
                "canonical_acceptance": "PENDING",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
