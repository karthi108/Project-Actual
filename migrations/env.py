"""Run reviewed migrations against an explicit PostgreSQL connection only."""

from alembic import context
from sqlalchemy.engine import Connection

from actual.persistence.database import create_database_engine
from actual.persistence.schema import metadata

config = context.config


def _run(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=metadata,
        compare_type=True,
        transactional_ddl=True,
    )
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    context.configure(
        dialect_name="postgresql",
        target_metadata=metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        transactional_ddl=True,
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    supplied = config.attributes.get("connection")
    if supplied is not None:
        if not isinstance(supplied, Connection):
            raise TypeError("Migration connection must be a SQLAlchemy Connection")
        _run(supplied)
    else:
        engine = create_database_engine()
        try:
            with engine.connect() as active:
                _run(active)
        finally:
            engine.dispose()
