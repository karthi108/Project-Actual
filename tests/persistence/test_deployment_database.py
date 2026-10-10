"""Real database deployment/role checks, distinct from the accepted API test module."""

from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from actual.deployment import __main__ as deployment
from actual.persistence.database import verify_schema
from actual.workflows.approval import audit


def test_deployment_commands_are_explicit_and_runtime_role_cannot_modify_audit(
    pg_engine, monkeypatch
):
    monkeypatch.setattr(deployment, "database_url", lambda: "Synthetic stub")
    monkeypatch.setattr(deployment, "create_database_engine", lambda _: pg_engine)
    deployment.run("check")
    deployment.run("migrate")
    deployment.run("migrate")
    role = "actual_test_role_" + uuid4().hex
    script = (
        Path("deploy/runtime-role.sql").read_text(encoding="utf-8").replace("actual_runtime", role)
    )
    with pg_engine.begin() as connection:
        schema = connection.execute(text("SELECT current_schema()")).scalar_one()
    # The template targets public on a real isolated deployment, this fixture owns a fresh schema.
    script = script.replace("SCHEMA public", 'SCHEMA "' + schema + '"')
    try:
        with pg_engine.begin() as connection:
            for statement in script.split(";"):
                if statement.strip():
                    connection.execute(text(statement))
        with pg_engine.begin() as connection:
            connection.execute(text('SET LOCAL ROLE "' + role + '"'))
            verify_schema(connection)
            assert connection.execute(audit.select()).all() == []
            with pytest.raises(DBAPIError):
                connection.execute(audit.update().values(state="approved"))
        with pg_engine.begin() as connection:
            connection.execute(text('SET LOCAL ROLE "' + role + '"'))
            with pytest.raises(DBAPIError):
                connection.execute(text("CREATE TABLE fabricated_ddl (id integer)"))
    finally:
        with pg_engine.begin() as connection:
            connection.execute(text('DROP OWNED BY "' + role + '"'))
            connection.execute(text('DROP ROLE "' + role + '"'))
