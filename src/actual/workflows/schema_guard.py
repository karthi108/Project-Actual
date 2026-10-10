"""Refuse drift in provisional workflow tables instead of silently blessing it."""

from sqlalchemy import Connection, MetaData, UniqueConstraint, inspect


def verify(connection: Connection, metadata: MetaData) -> None:
    inspector = inspect(connection)
    for table in metadata.tables.values():
        found = {column["name"]: column for column in inspector.get_columns(table.name)}
        if set(found) != set(table.columns.keys()):
            raise ValueError("Unsupported workflow table shape")
        for column in table.columns:
            actual = found[column.name]
            if (
                actual["type"].compile(dialect=connection.dialect)
                != column.type.compile(dialect=connection.dialect)
                or actual["nullable"] != column.nullable
            ):
                raise ValueError("Unsupported workflow column shape")
        primary = inspector.get_pk_constraint(table.name)["constrained_columns"]
        if set(primary) != set(table.primary_key.columns.keys()):
            raise ValueError("Unsupported workflow primary key")
        expected = {
            frozenset(constraint.columns.keys())
            for constraint in table.constraints
            if isinstance(constraint, UniqueConstraint)
        }
        actual_unique = {
            frozenset(constraint["column_names"])
            for constraint in inspector.get_unique_constraints(table.name)
        }
        if actual_unique != expected:
            raise ValueError("Unsupported workflow unique constraints")
