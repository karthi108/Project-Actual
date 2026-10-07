from pathlib import Path

import pytest

from actual.deployment.secrets import database_url


@pytest.mark.parametrize("content", [b"", b"x" * 4097, b"one\ntwo", b"one\x00two", b"\xff"])
def test_secret_files_are_bounded_single_values_with_safe_errors(tmp_path, content):
    path = tmp_path / "secret"
    path.write_bytes(content)
    with pytest.raises(ValueError, match="bounded mounted") as error:
        database_url(path)
    assert str(error.value) == "A bounded mounted database secret is required"


def test_secret_file_reader_does_not_echo_missing_paths_or_create_anything(tmp_path):
    missing = tmp_path / "fabricated_private_path"
    with pytest.raises(ValueError) as error:
        database_url(missing)
    assert str(missing) not in str(error.value) and not missing.exists()
    path = tmp_path / "secret"
    path.write_text("Fabricated test secret\n", encoding="utf-8")
    assert database_url(path) == "Fabricated test secret"
    with pytest.raises(ValueError):
        database_url(Path(tmp_path))
