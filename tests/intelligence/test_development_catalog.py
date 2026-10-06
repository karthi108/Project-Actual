"""The supported development intake stays pinned, observable and non-arbitrary."""

import hashlib
from pathlib import Path

import pytest

from actual.job_intelligence import development
from actual.job_intelligence.errors import IntelligenceFailure


def test_catalog_preserves_eight_public_observable_identities() -> None:
    values = development.load_development()
    assert tuple(value.id for value in values) == tuple(development.INPUT_HASHES)
    assert all(value.synthetic is True for value in values)
    assert not any(hasattr(value, "oracle") for value in values)


def test_changed_fixture_cannot_enter_supported_development_intake(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    inputs = tmp_path / "datasets" / "development" / "inputs"
    inputs.mkdir(parents=True)
    source = development._ROOT / "datasets" / "development" / "inputs" / "CAREER-DEV-001.json"
    payload = source.read_bytes().replace(b"Python", b"PERSONAL-CANARY", 1)
    (inputs / "CAREER-DEV-001.json").write_bytes(payload)
    assert hashlib.sha256(payload).hexdigest() != development.INPUT_HASHES["CAREER-DEV-001"]
    monkeypatch.setattr(development, "_ROOT", tmp_path)
    with pytest.raises(IntelligenceFailure, match="^input_rejected$"):
        development.load_development()


def test_catalog_has_no_arbitrary_path_or_text_argument() -> None:
    with pytest.raises(TypeError):
        development.load_development("private-file.json")  # type: ignore[call-arg]
