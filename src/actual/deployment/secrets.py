"""Fixed operator-mounted secret input, never model/request configuration."""

import stat
from pathlib import Path


def database_url(path: Path = Path("/run/secrets/database_url")) -> str:
    try:
        if not stat.S_ISREG(path.lstat().st_mode):
            raise ValueError
        with path.open("rb") as stream:
            raw = stream.read(4097)
        if len(raw) > 4096:
            raise ValueError
        value = raw.decode("utf-8").removesuffix("\n").removesuffix("\r")
        if not value or any(character in value for character in ("\n", "\r", "\x00")):
            raise ValueError
        return value
    except (OSError, UnicodeError, ValueError):
        raise ValueError("A bounded mounted database secret is required") from None
