"""Public development artifact integrity, reproducibility and packaging boundaries."""

import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from actual.careerlab.codec import observable_bytes, oracle_bytes
from actual.careerlab.dataset import (
    DEFAULT_SEED,
    build_manifest,
    validate_development,
    verify_development,
    write_development,
)
from actual.careerlab.generator import generate_development, generate_inputs
from actual.careerlab.validation import validate_input


def locations(base: Path) -> tuple[Path, Path, Path]:
    return base / "observable", base / "evaluator", base / "metadata/manifest.json"


def tree_bytes(base: Path) -> dict[str, bytes]:
    return {path.relative_to(base).as_posix(): path.read_bytes() for path in base.rglob("*.json")}


def test_saved_development_regenerates_identically_in_other_directory(tmp_path: Path) -> None:
    first, second = tmp_path / "first", tmp_path / "second"
    a = write_development(*locations(first))
    b = write_development(*locations(second))
    assert a == b
    assert tree_bytes(first) == tree_bytes(second)
    assert verify_development(*locations(first)) == a
    assert verify_development(*locations(second)) == b
    assert len(tree_bytes(first)) == 17  # 8 observable, 8 evaluator, 1 manifest.


def test_source_only_generation_and_semantic_seed_variation() -> None:
    first = generate_development(DEFAULT_SEED)
    assert generate_inputs(DEFAULT_SEED) == tuple(pair.inputs for pair in first)
    repeated = generate_development(DEFAULT_SEED)
    assert [observable_bytes(p.inputs) for p in first] == [
        observable_bytes(p.inputs) for p in repeated
    ]
    assert [oracle_bytes(p.oracle) for p in first] == [oracle_bytes(p.oracle) for p in repeated]
    assert build_manifest(first, DEFAULT_SEED) == build_manifest(repeated, DEFAULT_SEED)
    changed = generate_development(DEFAULT_SEED + 1)
    validate_development(changed)

    # Inspect actual context/dates/prose, rather than counting changes to IDs/seed metadata.
    def meaning(pairs: object) -> object:
        assert isinstance(pairs, tuple)
        return [
            (p.inputs.companies[0].context, p.inputs.jobs[0].posted_at, p.inputs.jobs[0].text)
            for p in pairs
        ]

    assert meaning(first) != meaning(changed)


@pytest.mark.parametrize("seed", [0, 1, 17, 2147483647, DEFAULT_SEED])
def test_generated_records_validate_for_multiple_seeds(seed: int) -> None:
    pairs = generate_development(seed)
    validate_development(pairs)
    rejected = [p.inputs.id for p in pairs if validate_input(p.inputs)]
    assert rejected == ["CAREER-DEV-008"]


@pytest.mark.parametrize("seed", [-1, 2**63, True, 1.5, "42"])
def test_invalid_generation_seed_is_rejected(seed: object) -> None:
    with pytest.raises(ValueError):
        generate_development(seed)  # type: ignore[arg-type]


def test_manifest_records_versions_lineages_hashes_and_unmaterialized_splits() -> None:
    manifest = build_manifest(generate_development(), DEFAULT_SEED)
    assert manifest["synthetic"] is True
    assert manifest["split_status"] == {
        "development": "public",
        "validation": "unmaterialized",
        "locked_test": "unmaterialized",
    }
    assert manifest["input_schema"] == "careerlab-input-v1"
    assert manifest["oracle_schema"] == "careerlab-oracle-v1"
    assert manifest["rubric_version"] == "careerlab-support-v1"
    sources = manifest["source_sha256"]
    assert isinstance(sources, dict)
    assert {
        "docs/phase-1/methodology.md",
        "docs/phase-1/rubric.md",
        "pyproject.toml",
        "uv.lock",
    } <= sources.keys()
    assert all(len(value) == 64 for value in sources.values())
    assert len(str(manifest["dataset_sha256"])) == 64


def test_no_evaluator_answers_or_canary_in_saved_inputs(tmp_path: Path) -> None:
    paths = locations(tmp_path)
    write_development(*paths)
    forbidden = {
        "coverage",
        "assessment",
        "requirements",
        "blocked_draft_ids",
        "acceptable_cv_ids",
        "expected_error_codes",
        "future_outcomes",
        "secret_canary",
    }

    def inspect(value: object) -> None:
        if isinstance(value, dict):
            assert not forbidden & set(value)
            for child in value.values():
                inspect(child)
        elif isinstance(value, list):
            for child in value:
                inspect(child)

    for pair in generate_development():
        payload = (paths[0] / f"{pair.inputs.id}.json").read_bytes()
        inspect(json.loads(payload))
        if pair.oracle.secret_canary:
            assert pair.oracle.secret_canary.encode() not in payload
        for outcome in pair.oracle.future_outcomes:
            assert outcome.explanation.encode() not in payload


@pytest.mark.parametrize(
    "root_kind", ["same", "evaluator_inside", "inputs_inside", "manifest_inside", "locked"]
)
def test_packaging_rejects_overlapping_or_locked_destinations(
    tmp_path: Path, root_kind: str
) -> None:
    a, b, m = locations(tmp_path)
    if root_kind == "same":
        b = a
    elif root_kind == "evaluator_inside":
        b = a / "answers"
    elif root_kind == "inputs_inside":
        a = b / "observable"
    elif root_kind == "manifest_inside":
        m = a / "manifest.json"
    else:
        b = tmp_path / "locked_test"
    with pytest.raises(ValueError):
        write_development(a, b, m)
    assert not a.exists() and not b.exists()  # Rejection happens before writing/reading cases.


@pytest.mark.parametrize("kind", ["input", "oracle", "manifest", "extra", "missing"])
def test_verification_rejects_tampering_or_missing_membership(tmp_path: Path, kind: str) -> None:
    a, b, m = locations(tmp_path)
    write_development(a, b, m)
    if kind == "input":
        (a / "CAREER-DEV-001.json").write_bytes(b"{}\n")
    elif kind == "oracle":
        (b / "CAREER-DEV-001.json").write_bytes(b"{}\n")
    elif kind == "manifest":
        data = json.loads(m.read_bytes())
        data["seed"] += 1
        m.write_text(json.dumps(data), encoding="utf-8")
    elif kind == "extra":
        (a / "unexpected.json").write_bytes(b"{}\n")
    else:
        (b / "CAREER-DEV-001.json").unlink()
    with pytest.raises(ValueError):
        verify_development(a, b, m)


def test_generator_does_not_overwrite_unrelated_output(tmp_path: Path) -> None:
    a, b, m = locations(tmp_path)
    a.mkdir()
    unrelated = a / "owner-notes.txt"
    unrelated.write_text("preserve", encoding="utf-8")
    with pytest.raises(ValueError):
        write_development(a, b, m)
    assert unrelated.read_text() == "preserve"
    assert not b.exists() and not m.exists()


@pytest.mark.parametrize("operation", ["write", "verify"])
def test_artifact_alias_is_rejected_before_payload_io(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, operation: str
) -> None:
    a, b, m = locations(tmp_path)
    write_development(a, b, m)
    protected = a / "CAREER-DEV-001.json"
    original = Path.is_symlink
    monkeypatch.setattr(Path, "is_symlink", lambda path: path == protected or original(path))
    with pytest.raises(ValueError, match="symlinks"):
        if operation == "write":
            write_development(a, b, m)
        else:
            verify_development(a, b, m)


def test_development_gate_rejects_missing_categories_and_foreign_split() -> None:
    pairs = generate_development()
    with pytest.raises(ValueError):
        validate_development(pairs[:-1])
    foreign = replace(pairs[0], membership=replace(pairs[0].membership, split="validation"))
    with pytest.raises(ValueError):
        validate_development((foreign, *pairs[1:]))


def test_cli_generate_and_verify_in_fresh_processes(tmp_path: Path) -> None:
    a, b, m = locations(tmp_path)
    paths = ["--inputs", str(a), "--evaluator", str(b), "--manifest", str(m)]
    generated = subprocess.run(
        [sys.executable, "-m", "actual.careerlab", "generate", *paths],
        capture_output=True,
        text=True,
        check=True,
    )
    verified = subprocess.run(
        [sys.executable, "-m", "actual.careerlab", "verify", *paths],
        capture_output=True,
        text=True,
        check=True,
    )
    assert generated.stdout == verified.stdout
    assert "8 public cases" in verified.stdout
    assert "unmaterialized" in verified.stdout


def test_cli_has_no_automatic_heldout_generation(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "actual.careerlab", "generate", "--split", "locked_test"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert not list(tmp_path.iterdir())
