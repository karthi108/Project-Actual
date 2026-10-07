import importlib.util
from pathlib import Path
from shutil import copytree

import pytest


def test_fresh_clone_restores_only_missing_private_evaluators_and_refuses_overwrites(tmp_path):
    root = Path(__file__).resolve().parents[2]
    spec = importlib.util.spec_from_file_location(
        "evaluator_bootstrap", root / "scripts/prepare_evaluator_fixtures.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    inputs = tmp_path / "datasets/development/inputs"
    copytree(root / "datasets/development/inputs", inputs)
    manifest = tmp_path / "docs/office-build/careerlab-environment.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_bytes((root / "docs/office-build/careerlab-environment.json").read_bytes())
    original = {path.name: path.read_bytes() for path in inputs.iterdir()}
    with pytest.raises(ValueError, match="explicit materialization"):
        module.prepare(tmp_path, False)
    module.prepare(tmp_path, True)
    module.prepare(tmp_path, False)
    assert {path.name: path.read_bytes() for path in inputs.iterdir()} == original
    evaluator = tmp_path / "datasets/ground_truth/development"
    damaged = next(evaluator.iterdir())
    damaged.write_bytes(b"Fabricated corruption")
    with pytest.raises(ValueError, match="never overwrite"):
        module.prepare(tmp_path, True)
    assert damaged.read_bytes() == b"Fabricated corruption"
