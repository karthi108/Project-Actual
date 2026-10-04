"""Required real-PostgreSQL fixtures, each confined to a fresh disposable schema."""

import os
import re
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Connection, Engine, create_engine, event
from sqlalchemy.engine import URL

from actual.persistence import schema
from actual.persistence.database import create_database_engine
from actual.persistence.errors import PersistenceError

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATTERN = re.compile(r"actual_test_[0-9a-f]{32}")
ROLE_PATTERN = re.compile(r"actual_test_role_[0-9a-f]{32}")


def migration_config(connection: Connection) -> Config:
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    location = Path(config.get_main_option("script_location"))
    if not location.is_absolute():
        location = PROJECT_ROOT / location
    config.set_main_option("script_location", str(location))
    config.attributes["connection"] = connection
    return config


@pytest.fixture(scope="session")
def database_url() -> URL:
    value = os.environ.get("ACTUAL_TEST_DATABASE_URL")
    if not value:
        raise pytest.UsageError(
            "ACTUAL_TEST_DATABASE_URL is required: persistence acceptance uses real PostgreSQL"
        )
    try:
        configured = create_database_engine(value)
    except PersistenceError:
        raise pytest.UsageError("Malformed PostgreSQL test configuration") from None
    try:
        url = configured.url
    finally:
        configured.dispose()
    if url.host not in ("localhost", "127.0.0.1", "::1"):
        raise pytest.UsageError("Disposable persistence tests require the local PostgreSQL service")
    return url


@contextmanager
def isolated_engine(database_url: URL) -> Iterator[Engine]:
    schema_name = f"actual_test_{uuid4().hex}"
    if SCHEMA_PATTERN.fullmatch(schema_name) is None:
        raise RuntimeError("Unsafe disposable schema identity")
    admin = create_engine(database_url, echo=False, hide_parameters=True, pool_pre_ping=True)
    engine = create_engine(
        database_url,
        echo=False,
        hide_parameters=True,
        pool_pre_ping=True,
        connect_args={
            "options": f"-c search_path={schema_name},pg_catalog,public,pg_temp -c timezone=UTC"
        },
    )
    created = False
    try:
        with admin.begin() as connection:
            connection.exec_driver_sql(f'CREATE SCHEMA "{schema_name}"')
        created = True
        with engine.connect() as connection:
            assert connection.exec_driver_sql("SELECT current_schema()").scalar_one() == schema_name
            assert connection.exec_driver_sql("SHOW TimeZone").scalar_one() == "UTC"
        yield engine
    finally:
        engine.dispose()
        if created:
            if SCHEMA_PATTERN.fullmatch(schema_name) is None:
                raise RuntimeError("Refusing to remove an unsafe schema identity")
            with admin.begin() as connection:
                connection.exec_driver_sql(f'DROP SCHEMA "{schema_name}" CASCADE')
        admin.dispose()


@pytest.fixture
def unmigrated_engine(database_url: URL) -> Iterator[Engine]:
    with isolated_engine(database_url) as engine:
        yield engine


@pytest.fixture
def pg_engine(unmigrated_engine: Engine) -> Engine:
    with unmigrated_engine.begin() as connection:
        command.upgrade(migration_config(connection), "head")
    return unmigrated_engine


@pytest.fixture
def restored_pg_engine(database_url: URL) -> Iterator[Engine]:
    """A separately migrated destination, with no shared tables or tombstones."""
    with isolated_engine(database_url) as engine:
        with engine.begin() as connection:
            command.upgrade(migration_config(connection), "head")
        yield engine


@pytest.fixture
def runtime_engine(pg_engine: Engine) -> Iterator[Engine]:
    """Exercise DML through a fresh role that cannot own or alter the schema."""
    role_name = f"actual_test_role_{uuid4().hex}"
    if ROLE_PATTERN.fullmatch(role_name) is None:
        raise RuntimeError("Unsafe disposable role identity")
    with pg_engine.connect() as connection:
        schema_name = connection.exec_driver_sql("SELECT current_schema()").scalar_one()
    if SCHEMA_PATTERN.fullmatch(schema_name) is None:
        raise RuntimeError("Unsafe role grant destination")
    tables = ", ".join(
        f'"{schema_name}"."{table.name}"'
        for table in schema.metadata.tables.values()
        if table is not schema.deletion_ledger
    )
    created = False
    engine = create_engine(
        pg_engine.url,
        echo=False,
        hide_parameters=True,
        connect_args={
            "options": f"-c search_path={schema_name},pg_catalog,public,pg_temp -c timezone=UTC"
        },
    )

    @event.listens_for(engine, "begin")
    def assume_runtime_role(connection: Connection) -> None:
        connection.exec_driver_sql(f'SET LOCAL ROLE "{role_name}"')

    try:
        with pg_engine.begin() as connection:
            connection.exec_driver_sql(f'CREATE ROLE "{role_name}" NOLOGIN')
            connection.exec_driver_sql(f'GRANT USAGE ON SCHEMA "{schema_name}" TO "{role_name}"')
            connection.exec_driver_sql(
                f'GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE {tables} TO "{role_name}"'
            )
            connection.exec_driver_sql(
                f'GRANT SELECT, INSERT ON TABLE "{schema_name}".deletion_ledger TO "{role_name}"'
            )
            connection.exec_driver_sql(
                f'GRANT SELECT ON TABLE "{schema_name}".alembic_version TO "{role_name}"'
            )
        created = True
        yield engine
    finally:
        engine.dispose()
        if created:
            if ROLE_PATTERN.fullmatch(role_name) is None:
                raise RuntimeError("Refusing to remove an unsafe role identity")
            with pg_engine.begin() as connection:
                connection.exec_driver_sql(
                    f'REVOKE ALL ON ALL TABLES IN SCHEMA "{schema_name}" FROM "{role_name}"'
                )
                connection.exec_driver_sql(
                    f'REVOKE ALL ON SCHEMA "{schema_name}" FROM "{role_name}"'
                )
                connection.exec_driver_sql(f'DROP ROLE "{role_name}"')
