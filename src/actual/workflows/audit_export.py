"""Bounded, read-only synthetic audit snapshot; never an authorization artifact."""

from typing import Annotated, Literal

from pydantic import Field, SecretStr
from sqlalchemy import select

from actual.core.primitives import Contract, Digest, Instant, WorkspaceId, content_digest

from .activation import audit as activation_audit
from .approval import audit as effect_audit
from .storage import Conflict
from .storage import audit as run_audit
from .teams import Teams
from .teams import audit as team_audit

type Action = Literal[
    "ready",
    "waiting",
    "human_wait",
    "succeeded",
    "failed",
    "cancelled",
    "approved",
    "reserved",
    "dispatching",
    "outcome_unknown",
    "revoked",
    "enabled",
    "disabled",
    "shadow",
    "publish",
    "workspace_policy",
    "organization_policy",
]


class AuditEntry(Contract):
    source: Literal["runtime", "effect", "activation", "team"]
    at: Instant
    action: Action
    event_digest: Digest
    actor_digest: Digest | None = None
    workflow_digest: Digest | None = None
    authority_digest: Digest | None = None


class AuditExport(Contract):
    export_version: Literal["actual-synthetic-audit-v1"] = "actual-synthetic-audit-v1"
    workspace_id: WorkspaceId
    classification: Literal["synthetic"] = "synthetic"
    generated_at: Instant
    complete_snapshot: Literal[True] = True
    grants_authority: Literal[False] = False
    entries: Annotated[tuple[AuditEntry, ...], Field(max_length=1000)]

    @property
    def digest(self) -> str:
        return content_digest(self.model_dump(mode="json"))


def export(teams: Teams, token: SecretStr, owner: WorkspaceId) -> AuditExport:
    teams.context(token, owner, ("admin",))
    entries: list[AuditEntry] = []
    # All four sources describe one MVCC snapshot; no silent truncation or raw payload table.
    with teams.engine.connect().execution_options(isolation_level="REPEATABLE READ") as connection:
        with connection.begin():
            for source, table, action_field in (
                ("runtime", run_audit, "status"),
                ("effect", effect_audit, "state"),
                ("activation", activation_audit, "state"),
                ("team", team_audit, "action"),
            ):
                rows = (
                    connection.execute(select(table).where(table.c.owner == owner.root).limit(1001))
                    .mappings()
                    .all()
                )
                if len(rows) + len(entries) > 1000:
                    raise Conflict("Audit export budget exceeded; no complete export produced")
                for row in rows:
                    safe_row = {
                        key: value.isoformat() if key == "at" else value
                        for key, value in row.items()
                    }
                    entries.append(
                        AuditEntry.model_validate(
                            {
                                "source": source,
                                "at": row["at"],
                                "action": row[action_field],
                                "event_digest": content_digest(safe_row),
                                "actor_digest": content_digest(row["actor"])
                                if "actor" in row
                                else None,
                                "workflow_digest": row.get(
                                    "workflow", row.get("definition_digest")
                                ),
                                "authority_digest": row.get("authority"),
                            }
                        )
                    )
    # Do not release a snapshot to an expired/revoked administrator session.
    teams.context(token, owner, ("admin",))
    return AuditExport(
        workspace_id=owner,
        generated_at=teams.clock(),
        entries=tuple(
            sorted(entries, key=lambda entry: (entry.at, entry.source, entry.event_digest))
        ),
    )
