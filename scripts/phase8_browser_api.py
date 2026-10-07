"""Owned disposable browser-test API; no startup migration in the product API.

The harness alone migrates an explicitly configured disposable database. Never
point this helper at runtime storage. It refuses non-loopback test configuration.
"""

import os
from pathlib import Path

import uvicorn
from alembic import command
from alembic.config import Config

from actual.api.app import create_app
from actual.api.config import ApiSettings
from actual.core.primitives import ActorId, WorkspaceId
from actual.persistence.database import create_database_engine


def main() -> None:
    if os.environ.get("ACTUAL_BROWSER_TEST_DISPOSABLE") != "phase8-owned-native-cluster":
        raise RuntimeError("Explicit owned disposable browser database required")
    engine = create_database_engine(os.environ["ACTUAL_TEST_DATABASE_URL"])
    if engine.url.host != "127.0.0.1":
        raise RuntimeError("Browser tests require an owned loopback database")
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
    settings = ApiSettings(
        workspace_id=WorkspaceId("workspace_" + "8" * 32),
        actor_id=ActorId("actor_" + "8" * 32),
    )
    try:
        uvicorn.run(
            create_app(settings, engine),
            host="127.0.0.1",
            port=8765,
            proxy_headers=False,
            access_log=False,
            log_level="warning",
        )
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
