"""Offline development-data authoring CLI; no ACTUAL application entry point."""

import argparse
from pathlib import Path

from .dataset import DEFAULT_SEED, verify_development, write_development


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("generate", "verify"))
    parser.add_argument("--inputs", type=Path, default=Path("datasets/development/inputs"))
    parser.add_argument("--evaluator", type=Path, default=Path("datasets/ground_truth/development"))
    parser.add_argument(
        "--manifest", type=Path, default=Path("datasets/manifests/careerlab-dev-v1.json")
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args()
    try:
        if args.command == "generate":
            identity = write_development(args.inputs, args.evaluator, args.manifest, args.seed)
        else:
            identity = verify_development(args.inputs, args.evaluator, args.manifest)
    except (ValueError, OSError) as error:
        parser.exit(1, f"CareerLab rejected dataset: {error}\n")
    print(f"development: 8 public cases; validation/locked_test: unmaterialized; sha256={identity}")


if __name__ == "__main__":
    main()
