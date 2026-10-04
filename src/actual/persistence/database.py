"""Local PostgreSQL engine configuration and fail-closed migration-head checks.

Creating an engine is lazy: no database connection or schema mutation happens
here. The trusted local operator configures credentials outside version control.
URL query parameters are excluded because driver settings can override a host.
"""

import os

from alembic.migration import MigrationContext
from sqlalchemy import create_engine
from sqlalchemy.engine import URL, Connection, Engine, make_url
from sqlalchemy.exc import ArgumentError, SQLAlchemyError

from .errors import PersistenceError, SchemaMismatchError

SCHEMA_HEAD = "0001_career_persistence"
STATEMENT_TIMEOUT_MS = 10_000
CONNECT_TIMEOUT_SECONDS = 5
_LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1", "postgres"})
_DESTINATION_ENVIRONMENT = ("PGHOSTADDR", "PGSERVICE", "PGSERVICEFILE")
_CONFIGURATION_ERROR = "A local PostgreSQL psycopg URL with configured credentials is required"


def _configured_url(value: str | URL | None) -> URL:
    if any(os.environ.get(name) for name in _DESTINATION_ENVIRONMENT):
        raise PersistenceError("Libpq address and service overrides are not allowed")
    configured = os.environ.get("ACTUAL_DATABASE_URL") if value is None else value
    if not isinstance(configured, (str, URL)):
        raise PersistenceError(_CONFIGURATION_ERROR)
    if isinstance(configured, str) and len(configured) > 4096:
        raise PersistenceError(_CONFIGURATION_ERROR)
    try:
        parsed = make_url(configured)
    except (ArgumentError, TypeError, ValueError):
        raise PersistenceError(_CONFIGURATION_ERROR) from None
    if (
        parsed.drivername != "postgresql+psycopg"
        or parsed.host is None
        or parsed.host.lower() not in _LOCAL_HOSTS
        or parsed.query
        or not isinstance(parsed.password, str)
        or not parsed.password.strip()
        or "\x00" in parsed.password
        or parsed.username is None
        or not parsed.username.strip()
        or "\x00" in parsed.username
        or parsed.database is None
        or not parsed.database.strip()
        or "\x00" in parsed.database
        or parsed.port is not None
        and not 1 <= parsed.port <= 65535
    ):
        raise PersistenceError(_CONFIGURATION_ERROR)
    return parsed


def create_database_engine(url: str | URL | None = None) -> Engine:
    """Configure one local engine without connecting, logging data or migrating."""
    configured = _configured_url(url)
    try:
        return create_engine(
            configured,
            echo=False,
            echo_pool=False,
            hide_parameters=True,
            pool_pre_ping=True,
            connect_args={
                "options": (
                    "-c search_path=public,pg_catalog,pg_temp "
                    f"-c timezone=UTC -c statement_timeout={STATEMENT_TIMEOUT_MS}"
                ),
                "connect_timeout": CONNECT_TIMEOUT_SECONDS,
            },
        )
    except (SQLAlchemyError, ImportError, TypeError, ValueError):
        raise PersistenceError(
            "The configured local database engine could not be created"
        ) from None


def verify_schema(connection: Connection) -> None:
    """Require exactly the committed migration head before persistence operations."""
    try:
        heads = MigrationContext.configure(connection).get_current_heads()
    except (SQLAlchemyError, ValueError):
        raise SchemaMismatchError("Database migration state could not be verified") from None
    if heads != (SCHEMA_HEAD,):
        raise SchemaMismatchError("Database migration state does not match the committed schema")
