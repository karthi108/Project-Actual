"""Local destination, secret-free failures and migration-head boundary tests."""

import traceback
from unittest.mock import Mock

import pytest
from alembic.migration import MigrationContext
from sqlalchemy.engine import URL, Connection
from sqlalchemy.exc import OperationalError

from actual.persistence import database
from actual.persistence.errors import PersistenceError, SchemaMismatchError


def configured_url(**changes: object) -> URL:
    values = {
        "drivername": "postgresql+psycopg",
        "username": "synthetic_owner",
        "password": "synthetic-test-password",
        "host": "127.0.0.1",
        "database": "synthetic_database",
        **changes,
    }
    return URL.create(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize("host", ["localhost", "LOCALHOST", "127.0.0.1", "::1", "postgres"])
def test_local_engines_are_lazy_and_use_bounded_private_defaults(host: str) -> None:
    engine = database.create_database_engine(configured_url(host=host))
    try:
        assert engine.url.host == host
        assert engine.dialect.name == "postgresql"
        assert engine.dialect.driver == "psycopg"
        assert engine.echo is False
        assert engine.hide_parameters is True
        assert engine.pool._pre_ping is True
        assert engine.pool.checkedout() == 0  # type: ignore[attr-defined]
        connection_args = engine.dialect.create_connect_args(engine.url)
        assert connection_args[1]["host"] == host
    finally:
        engine.dispose()


def test_engine_creation_applies_fixed_connection_options(monkeypatch: pytest.MonkeyPatch) -> None:
    create = Mock()
    monkeypatch.setattr(database, "create_engine", create)
    url = configured_url()
    assert database.create_database_engine(url) is create.return_value
    create.assert_called_once_with(
        url,
        echo=False,
        echo_pool=False,
        hide_parameters=True,
        pool_pre_ping=True,
        connect_args={
            "options": (
                "-c search_path=public,pg_catalog,pg_temp "
                "-c timezone=UTC -c statement_timeout=10000"
            ),
            "connect_timeout": 5,
        },
    )


@pytest.mark.parametrize("setting", ["PGHOSTADDR", "PGSERVICE", "PGSERVICEFILE"])
def test_libpq_environment_cannot_redirect_an_explicit_local_destination(
    monkeypatch: pytest.MonkeyPatch, setting: str
) -> None:
    monkeypatch.setenv(setting, "private-redirect-configuration")
    create = Mock()
    monkeypatch.setattr(database, "create_engine", create)
    with pytest.raises(PersistenceError) as caught:
        database.create_database_engine(configured_url())
    assert "private-redirect-configuration" not in str(caught.value)
    create.assert_not_called()


def test_environment_credentials_are_used_only_when_no_explicit_url_is_given(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "ACTUAL_DATABASE_URL", configured_url().render_as_string(hide_password=False)
    )
    engine = database.create_database_engine()
    try:
        assert engine.url.password == "synthetic-test-password"
    finally:
        engine.dispose()
    monkeypatch.setenv("ACTUAL_DATABASE_URL", "malformed-private-value")
    explicit = database.create_database_engine(configured_url())
    explicit.dispose()


@pytest.mark.parametrize("value", [None, ""])
def test_missing_environment_configuration_fails_without_using_a_default_password(
    monkeypatch: pytest.MonkeyPatch, value: str | None
) -> None:
    if value is None:
        monkeypatch.delenv("ACTUAL_DATABASE_URL", raising=False)
    else:
        monkeypatch.setenv("ACTUAL_DATABASE_URL", value)
    with pytest.raises(PersistenceError):
        database.create_database_engine()


@pytest.mark.parametrize(
    "changes",
    [
        {"drivername": "postgresql"},
        {"drivername": "postgresql+psycopg2"},
        {"drivername": "sqlite"},
        {"host": "remote.example.invalid"},
        {"host": "192.168.1.10"},
        {"host": "127.0.0.2"},
        {"host": "localhost.remote.example.invalid"},
        {"host": "/tmp"},
        {"host": None},
        {"password": None},
        {"password": ""},
        {"password": " "},
        {"password": "nul\x00secret"},
        {"username": None},
        {"username": " "},
        {"database": None},
        {"database": " "},
        {"port": 0},
        {"port": 65536},
        {"query": {"host": "remote.example.invalid"}},
        {"query": {"hostaddr": "192.0.2.1"}},
        {"query": {"service": "private_remote_service"}},
        {"query": {"options": "-c timezone=Europe/Berlin"}},
    ],
)
def test_invalid_or_redirectable_configurations_fail_before_engine_creation(
    monkeypatch: pytest.MonkeyPatch, changes: dict[str, object]
) -> None:
    create = Mock()
    monkeypatch.setattr(database, "create_engine", create)
    with pytest.raises(PersistenceError):
        database.create_database_engine(configured_url(**changes))
    create.assert_not_called()


@pytest.mark.parametrize(
    "value",
    [
        "private-unparseable-password",
        "postgresql+psycopg://user:private-password@localhost:wrong-port/private-database",
        "x" * 4097,
        42,
    ],
)
def test_invalid_configuration_messages_never_include_supplied_input(value: object) -> None:
    with pytest.raises(PersistenceError) as caught:
        database.create_database_engine(value)  # type: ignore[arg-type]
    assert "private" not in str(caught.value)
    assert "password" not in str(caught.value)
    assert not caught.value.__cause__
    assert "private-password" not in "".join(traceback.format_exception(caught.value))


def test_engine_creation_failure_hides_original_driver_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create = Mock(side_effect=ValueError("private-password: private-driver-detail"))
    monkeypatch.setattr(database, "create_engine", create)
    with pytest.raises(PersistenceError) as caught:
        database.create_database_engine(configured_url())
    assert "private-password" not in "".join(traceback.format_exception(caught.value))


@pytest.mark.parametrize(
    "heads", [(), ("unknown_private_version",), (database.SCHEMA_HEAD, "other")]
)
def test_absent_unknown_or_multiple_schema_heads_are_rejected_without_echoing_versions(
    monkeypatch: pytest.MonkeyPatch, heads: tuple[str, ...]
) -> None:
    context = Mock(spec=MigrationContext)
    context.get_current_heads.return_value = heads
    configure = Mock(return_value=context)
    monkeypatch.setattr(database.MigrationContext, "configure", configure)
    connection = Mock(spec=Connection)
    with pytest.raises(SchemaMismatchError) as caught:
        database.verify_schema(connection)
    assert "unknown_private_version" not in str(caught.value)
    configure.assert_called_once_with(connection)


def test_exact_committed_schema_head_is_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    context = Mock(spec=MigrationContext)
    context.get_current_heads.return_value = (database.SCHEMA_HEAD,)
    monkeypatch.setattr(database.MigrationContext, "configure", Mock(return_value=context))
    database.verify_schema(Mock(spec=Connection))


def test_schema_driver_error_is_sanitized(monkeypatch: pytest.MonkeyPatch) -> None:
    context = Mock(spec=MigrationContext)
    context.get_current_heads.side_effect = OperationalError(
        "private SQL payload", {"password": "private-password"}, Exception("private driver error")
    )
    monkeypatch.setattr(database.MigrationContext, "configure", Mock(return_value=context))
    with pytest.raises(SchemaMismatchError) as caught:
        database.verify_schema(Mock(spec=Connection))
    assert "private" not in "".join(traceback.format_exception(caught.value))
