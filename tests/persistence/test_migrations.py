"""Verify committed Alembic DDL against a disposable PostgreSQL schema."""

import re

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from conftest import migration_config
from sqlalchemy import Engine, inspect, text

from actual.persistence import schema

REVISION = "0001_career_persistence"


def test_upgrade_repeat_downgrade_and_reupgrade_are_real_migrations(
    unmigrated_engine: Engine,
) -> None:
    with unmigrated_engine.begin() as connection:
        assert inspect(connection).get_table_names() == []
        config = migration_config(connection)
        command.upgrade(config, "head")
        assert MigrationContext.configure(connection).get_current_heads() == (REVISION,)
        assert set(inspect(connection).get_table_names()) == {
            *schema.metadata.tables,
            "alembic_version",
        }
        command.upgrade(config, "head")
        assert MigrationContext.configure(connection).get_current_heads() == (REVISION,)
        # This unique test schema contains no domain records. No user database or
        # populated workspace is downgraded to exercise the destructive path.
        command.downgrade(config, "base")
        assert MigrationContext.configure(connection).get_current_heads() == ()
        assert set(inspect(connection).get_table_names()) <= {"alembic_version"}
        command.upgrade(config, "head")
        assert MigrationContext.configure(connection).get_current_heads() == (REVISION,)
        assert set(inspect(connection).get_table_names()) == {
            *schema.metadata.tables,
            "alembic_version",
        }


def test_frozen_migration_has_no_schema_drift_against_current_metadata(pg_engine: Engine) -> None:
    with pg_engine.connect() as connection:
        context = MigrationContext.configure(
            connection,
            opts={"compare_type": True, "compare_server_default": True, "include_schemas": False},
        )
        assert compare_metadata(context, schema.metadata) == []


def test_postgresql_inspection_confirms_ownership_and_business_constraints(
    pg_engine: Engine,
) -> None:
    with pg_engine.connect() as connection:
        inspector = inspect(connection)
        application_uniques = {
            tuple(item["column_names"]) for item in inspector.get_unique_constraints("applications")
        }
        event_uniques = {
            tuple(item["column_names"]) for item in inspector.get_unique_constraints("work_events")
        }
        assert ("workspace_id", "profile_id", "opportunity_id") in application_uniques
        assert ("workspace_id", "source", "source_event_id") in event_uniques
        company_fk = next(
            item
            for item in inspector.get_foreign_keys("jobs")
            if item["constrained_columns"] == ["workspace_id", "company_id"]
        )
        assert company_fk["referred_table"] == "companies"
        assert company_fk["referred_columns"] == ["workspace_id", "id"]
        assert company_fk["options"]["deferrable"] is True
        assert company_fk["options"]["initially"] == "DEFERRED"
        assert inspector.get_foreign_keys("deletion_ledger") == []
        assert {item["name"] for item in inspector.get_columns("deletion_ledger")} == {
            "workspace_id",
            "deleted_at",
        }
        timestamp = next(
            item for item in inspector.get_columns("work_events") if item["name"] == "occurred_at"
        )
        assert timestamp["type"].timezone is True


def test_committed_migration_installs_every_active_guard_trigger(pg_engine: Engine) -> None:
    expected = {
        **{
            f"tr_{table.name}_record_update": "actual_guard_record_update"
            for table in schema.CURRENT_TABLES.values()
        },
        "tr_object_identities_update": "actual_guard_identity_update",
        "tr_work_events_immutable": "actual_guard_event_update",
        "tr_event_object_refs_immutable": "actual_guard_event_update",
        "tr_event_evidence_refs_immutable": "actual_guard_event_update",
        "tr_career_workspaces_guard": "actual_guard_workspace_write",
        "tr_deletion_ledger_immutable": "actual_guard_ledger_mutation",
        **{
            f"tr_{table.name}_protected_delete": "actual_guard_protected_delete"
            for table in (
                *schema.CURRENT_TABLES.values(),
                schema.object_identities,
                schema.career_workspaces,
            )
        },
        **{
            f"tr_{table.name}_retention_delete": "actual_guard_event_delete"
            for table in (schema.work_events, schema.event_object_refs, schema.event_evidence_refs)
        },
    }
    with pg_engine.connect() as connection:
        guards = connection.execute(
            text("""
            SELECT trigger.tgname, function.proname, trigger.tgenabled
            FROM pg_trigger AS trigger
            JOIN pg_class AS relation ON relation.oid = trigger.tgrelid
            JOIN pg_namespace AS namespace ON namespace.oid = relation.relnamespace
            JOIN pg_proc AS function ON function.oid = trigger.tgfoid
            WHERE namespace.nspname = current_schema() AND NOT trigger.tgisinternal
        """)
        ).all()
    assert {name: function for name, function, _ in guards} == expected
    assert all(enabled == "O" for _, _, enabled in guards)


def test_live_guard_functions_match_frozen_migration_bodies_and_security_settings(
    pg_engine: Engine,
) -> None:
    with pg_engine.connect() as connection:
        revision = ScriptDirectory.from_config(migration_config(connection)).get_revision(REVISION)
        assert revision is not None
        frozen = {}
        for statement in revision.module.UPGRADE_STATEMENTS:
            match = re.search(
                r"CREATE FUNCTION (actual_guard_[a-z_]+)\(\) RETURNS trigger"
                r".*?\$actual\$(.*?)\$actual\$",
                statement,
                flags=re.DOTALL,
            )
            if match:
                frozen[match[1]] = " ".join(match[2].split())
        assert len(frozen) == 7
        functions = connection.execute(
            text("""
            SELECT function.proname, function.prosrc, language.lanname,
                   pg_catalog.format_type(function.prorettype, NULL),
                   function.prosecdef, function.proconfig
            FROM pg_proc AS function
            JOIN pg_namespace AS namespace ON namespace.oid = function.pronamespace
            JOIN pg_language AS language ON language.oid = function.prolang
            WHERE namespace.nspname = current_schema()
                  AND function.proname LIKE 'actual_guard_%'
        """)
        ).all()
    assert {name: " ".join(body.split()) for name, body, *_ in functions} == frozen
    assert all(
        (language, return_type, security_definer, options) == ("plpgsql", "trigger", False, None)
        for _, _, language, return_type, security_definer, options in functions
    )
