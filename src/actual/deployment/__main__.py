"""Explicit migrate/check/serve commands; startup never changes a schema."""

import argparse
import logging
from pathlib import Path

import uvicorn
from alembic import command
from alembic.config import Config

from actual.api.app import create_app
from actual.api.config import ApiSettings
from actual.api.transport import REQUEST_LOG
from actual.persistence.database import create_database_engine, verify_schema
from actual.workflows.activation import migrate as migrate_activation
from actual.workflows.approval import migrate as migrate_approval
from actual.workflows.storage import migrate as migrate_workflow
from actual.workflows.teams import migrate as migrate_teams
from actual.worklab.shadow import migrate as migrate_shadow

from .secrets import database_url


def run(action: str) -> None:
    # This fixed file is mounted by the operator, outside the image and Git.
    engine = create_database_engine(database_url())
    try:
        if action == "migrate":
            config = Config(str(Path("alembic.ini")))
            with engine.begin() as connection:
                config.attributes["connection"] = connection
                command.upgrade(config, "head")
            for migration in (
                migrate_workflow,
                migrate_approval,
                migrate_activation,
                migrate_shadow,
                migrate_teams,
            ):
                migration(engine)
        elif action == "check":
            with engine.connect() as connection:
                verify_schema(connection)
        elif action == "serve":
            settings = ApiSettings.from_environment()
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter("%(message)s"))
            REQUEST_LOG.handlers = [handler]
            REQUEST_LOG.setLevel(logging.INFO)
            REQUEST_LOG.propagate = False
            uvicorn.run(
                create_app(settings, engine=engine),
                host="127.0.0.1",
                port=settings.port,
                proxy_headers=False,
                server_header=False,
                access_log=False,
                log_config=None,
                log_level="critical",
                timeout_keep_alive=5,
            )
        else:
            raise ValueError("Unknown deployment action")
    finally:
        engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Private synthetic ACTUAL deployment")
    parser.add_argument("action", choices=("migrate", "check", "serve"))
    action = parser.parse_args().action
    try:
        run(action)
    except Exception:
        raise SystemExit("ACTUAL deployment command failed; check private configuration.") from None


if __name__ == "__main__":
    main()
