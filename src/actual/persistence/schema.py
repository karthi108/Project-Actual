"""PostgreSQL relational boundaries for the current Career contracts.

This metadata describes storage, not a generic object repository. The initial
Alembic migration freezes its own DDL independently of this module.
"""

from typing import Any

import sqlalchemy as sa
from sqlalchemy.schema import SchemaItem

metadata = sa.MetaData()

_CLASSES = "('synthetic', 'personal', 'sensitive')"
_KINDS = (
    "('company', 'job', 'profile', 'claim', 'evidence', 'cv', 'draft', "
    "'application', 'requirement')"
)
_STATES = "('preparing', 'ready_for_review', 'reviewed', 'applied', 'interview', 'offer', 'closed')"
_ACTIVITIES = (
    "('job_added', 'requirements_reviewed', 'fit_assessment_recorded', "
    "'cv_recommended', 'draft_reviewed', 'application_status_recorded')"
)


def _id(name: str, nullable: bool = False) -> sa.Column[str]:
    return sa.Column(name, sa.Text(), nullable=nullable)


def _integer(name: str) -> sa.Column[int]:
    return sa.Column(name, sa.Integer(), nullable=False)


def _timestamp(name: str) -> sa.Column[Any]:
    return sa.Column(name, sa.DateTime(timezone=True), nullable=False)


def _check(table: str, label: str, expression: str) -> sa.CheckConstraint:
    # PostgreSQL CHECK accepts SQL NULL; required projections must fail instead.
    return sa.CheckConstraint(f"({expression}) IS TRUE", name=f"ck_{table}_{label}")


def _foreign(
    table: str, label: str, columns: list[str], targets: list[str]
) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        columns,
        targets,
        name=f"fk_{table}_{label}",
        ondelete="NO ACTION",
        onupdate="NO ACTION",
        deferrable=True,
        initially="DEFERRED",
    )


def _unique(table: str, label: str, *columns: str) -> sa.UniqueConstraint:
    # Collection swaps reconcile in one transaction; FK target keys stay immediate.
    return sa.UniqueConstraint(
        *columns,
        name=f"uq_{table}_{label}",
        deferrable=True if label == "position" else None,
        initially="DEFERRED" if label == "position" else None,
    )


def _scope_constraints(table: str) -> tuple[sa.CheckConstraint, sa.ForeignKeyConstraint]:
    return (
        _check(table, "workspace_id", "workspace_id ~ '^workspace_[0-9a-f]{32}$'"),
        _foreign(table, "workspace", ["workspace_id"], ["career_workspaces.workspace_id"]),
    )


def _payload_constraints(
    table: str, identity_field: str = "id", classification_field: str = "classification"
) -> tuple[sa.CheckConstraint, ...]:
    return (
        _check(table, "classification", f"classification IN {_CLASSES}"),
        _check(table, "payload_size", "octet_length(payload) BETWEEN 1 AND 2000000"),
        _check(table, "payload_digest", "payload_digest ~ '^[0-9a-f]{64}$'"),
        _check(
            table,
            "payload_hash",
            "payload_digest = encode(sha256(convert_to(payload, 'UTF8')), 'hex')",
        ),
        _check(
            table,
            "payload_metadata",
            "jsonb_typeof(payload::jsonb) = 'object' AND payload::jsonb @> "
            "jsonb_build_object('schema_version', 'actual-core-v1', "
            f"'{identity_field}', {identity_field}, 'workspace_id', workspace_id, "
            f"'{classification_field}', classification)",
        ),
    )


career_workspaces = sa.Table(
    "career_workspaces",
    metadata,
    _id("workspace_id"),
    _id("classification"),
    _timestamp("as_of"),
    sa.Column("generation", sa.BigInteger(), nullable=False),
    _id("snapshot_digest"),
    sa.PrimaryKeyConstraint("workspace_id", name="pk_career_workspaces"),
    _check("career_workspaces", "id", "workspace_id ~ '^workspace_[0-9a-f]{32}$'"),
    _check("career_workspaces", "classification", f"classification IN {_CLASSES}"),
    _check("career_workspaces", "generation", "generation > 0"),
    _check("career_workspaces", "digest", "snapshot_digest ~ '^[0-9a-f]{64}$'"),
)

object_identities = sa.Table(
    "object_identities",
    metadata,
    _id("workspace_id"),
    _id("object_id"),
    _id("kind"),
    _integer("revision"),
    _id("classification"),
    _id("digest"),
    sa.PrimaryKeyConstraint("workspace_id", "object_id", name="pk_object_identities"),
    *_scope_constraints("object_identities"),
    _check("object_identities", "kind", f"kind IN {_KINDS}"),
    _check("object_identities", "id_kind", "object_id ~ ('^' || kind || '_[0-9a-f]{32}$')"),
    _check("object_identities", "revision", "revision BETWEEN 1 AND 2147483647"),
    _check("object_identities", "classification", f"classification IN {_CLASSES}"),
    _check("object_identities", "digest", "digest ~ '^[0-9a-f]{64}$'"),
    _unique("object_identities", "kind", "workspace_id", "object_id", "kind"),
    _unique(
        "object_identities",
        "snapshot",
        "workspace_id",
        "object_id",
        "revision",
        "classification",
        "digest",
    ),
)


def _record(table: str, kind: str, *extra: SchemaItem) -> sa.Table:
    return sa.Table(
        table,
        metadata,
        _id("workspace_id"),
        _id("id"),
        _integer("position"),
        _integer("revision"),
        _id("classification"),
        sa.Column("payload", sa.Text(), nullable=False),
        _id("payload_digest"),
        sa.PrimaryKeyConstraint("workspace_id", "id", name=f"pk_{table}"),
        *_scope_constraints(table),
        _foreign(
            table,
            "identity",
            ["workspace_id", "id"],
            ["object_identities.workspace_id", "object_identities.object_id"],
        ),
        _foreign(
            table,
            "identity_snapshot",
            ["workspace_id", "id", "revision", "classification", "payload_digest"],
            [
                "object_identities.workspace_id",
                "object_identities.object_id",
                "object_identities.revision",
                "object_identities.classification",
                "object_identities.digest",
            ],
        ),
        _check(table, "id", f"id ~ '^{kind}_[0-9a-f]{{32}}$'"),
        _check(table, "position", "position >= 0"),
        _check(table, "revision", "revision BETWEEN 1 AND 2147483647"),
        *_payload_constraints(table),
        _check(
            table, "payload_revision", "payload::jsonb @> jsonb_build_object('revision', revision)"
        ),
        *extra,
    )


companies = _record(
    "companies", "company", _unique("companies", "position", "workspace_id", "position")
)
profiles = _record(
    "profiles",
    "profile",
    _unique("profiles", "one_per_workspace", "workspace_id"),
    _unique("profiles", "position", "workspace_id", "position"),
)
jobs = _record(
    "jobs",
    "job",
    _id("company_id"),
    _id("opportunity_id"),
    _timestamp("posted_at"),
    _unique("jobs", "position", "workspace_id", "position"),
    _unique("jobs", "opportunity", "workspace_id", "id", "opportunity_id"),
    _unique("jobs", "source_revision", "workspace_id", "id", "revision", "payload_digest"),
    _foreign(
        "jobs",
        "company",
        ["workspace_id", "company_id"],
        ["companies.workspace_id", "companies.id"],
    ),
    _check("jobs", "opportunity_id", "opportunity_id ~ '^opportunity_[0-9a-f]{32}$'"),
    _check(
        "jobs",
        "source_metadata",
        "payload::jsonb @> jsonb_build_object('company_id', company_id, "
        "'opportunity_id', opportunity_id) AND (payload::jsonb->>'posted_at')::timestamptz "
        "IS NOT DISTINCT FROM posted_at AND payload::jsonb ? 'posted_at'",
    ),
)


def _profile_constraints(table: str) -> tuple[SchemaItem, ...]:
    return (
        _id("profile_id"),
        _foreign(
            table,
            "profile",
            ["workspace_id", "profile_id"],
            ["profiles.workspace_id", "profiles.id"],
        ),
        _unique(table, "position", "workspace_id", "profile_id", "position"),
        _unique(table, "profile_identity", "workspace_id", "profile_id", "id"),
        _check(
            table,
            "profile_metadata",
            "payload::jsonb @> jsonb_build_object('profile_id', profile_id)",
        ),
    )


evidence = _record(
    "evidence",
    "evidence",
    *_profile_constraints("evidence"),
    _timestamp("collected_at"),
    _unique(
        "evidence",
        "source_snapshot",
        "workspace_id",
        "profile_id",
        "id",
        "revision",
        "payload_digest",
    ),
    _check(
        "evidence",
        "collected_metadata",
        "payload::jsonb ? 'collected_at' AND (payload::jsonb->>'collected_at')::timestamptz "
        "IS NOT DISTINCT FROM collected_at",
    ),
)
claims = _record(
    "claims",
    "claim",
    *_profile_constraints("claims"),
    _id("status"),
    _unique(
        "claims",
        "source_snapshot",
        "workspace_id",
        "profile_id",
        "id",
        "revision",
        "payload_digest",
    ),
    _check(
        "claims",
        "status",
        "status IN ('self_reported', 'candidate_support', 'reviewed_supported', "
        "'contradicted', 'withdrawn')",
    ),
    _check("claims", "status_metadata", "payload::jsonb @> jsonb_build_object('status', status)"),
)
cvs = _record("cvs", "cv", *_profile_constraints("cvs"))
drafts = _record("drafts", "draft", *_profile_constraints("drafts"))
applications = _record(
    "applications",
    "application",
    *_profile_constraints("applications"),
    _id("job_id"),
    _id("opportunity_id"),
    _id("state"),
    _unique("applications", "intent", "workspace_id", "profile_id", "opportunity_id"),
    _foreign(
        "applications",
        "job",
        ["workspace_id", "job_id", "opportunity_id"],
        ["jobs.workspace_id", "jobs.id", "jobs.opportunity_id"],
    ),
    _check("applications", "state", f"state IN {_STATES}"),
    _check(
        "applications",
        "application_metadata",
        "payload::jsonb @> jsonb_build_object('job_id', job_id, 'state', state)",
    ),
)
requirements = _record(
    "requirements",
    "requirement",
    _id("job_id"),
    _integer("job_revision"),
    _id("job_digest"),
    _id("opportunity_id"),
    _id("subject"),
    _unique("requirements", "position", "workspace_id", "position"),
    _unique("requirements", "subject", "workspace_id", "opportunity_id", "subject"),
    _foreign(
        "requirements",
        "job",
        ["workspace_id", "job_id", "opportunity_id"],
        ["jobs.workspace_id", "jobs.id", "jobs.opportunity_id"],
    ),
    _foreign(
        "requirements",
        "job_revision",
        ["workspace_id", "job_id", "job_revision", "job_digest"],
        ["jobs.workspace_id", "jobs.id", "jobs.revision", "jobs.payload_digest"],
    ),
    _check(
        "requirements",
        "source_metadata",
        "payload::jsonb @> jsonb_build_object('job_id', job_id, 'job_revision', "
        "job_revision, 'job_digest', job_digest) AND payload::jsonb->'assertion' "
        "@> jsonb_build_object('subject', subject)",
    ),
)


def _claim_links(table: str, owner: str, parent: str, draft: bool = False) -> sa.Table:
    columns: list[SchemaItem] = [
        _id("workspace_id"),
        _id(owner),
        _id("profile_id"),
        _integer("position"),
        _id("claim_id"),
        _integer("claim_revision"),
        _id("claim_digest"),
    ]
    key = ["workspace_id", owner]
    if draft:
        columns.append(_integer("assertion_position"))
        key.append("assertion_position")
    key.append("position")
    return sa.Table(
        table,
        metadata,
        *columns,
        sa.PrimaryKeyConstraint(*key, name=f"pk_{table}"),
        _check(table, "position", "position >= 0"),
        *([_check(table, "assertion_position", "assertion_position >= 0")] if draft else []),
        _unique(table, "source", *key[:-1], "claim_id"),
        _foreign(
            table,
            "owner",
            ["workspace_id", "profile_id", owner],
            [f"{parent}.workspace_id", f"{parent}.profile_id", f"{parent}.id"],
        ),
        _foreign(
            table,
            "claim_snapshot",
            ["workspace_id", "profile_id", "claim_id", "claim_revision", "claim_digest"],
            [
                "claims.workspace_id",
                "claims.profile_id",
                "claims.id",
                "claims.revision",
                "claims.payload_digest",
            ],
        ),
    )


claim_evidence_links = sa.Table(
    "claim_evidence_links",
    metadata,
    _id("workspace_id"),
    _id("claim_id"),
    _id("profile_id"),
    _integer("position"),
    _id("evidence_id"),
    _integer("evidence_revision"),
    _id("evidence_digest"),
    sa.PrimaryKeyConstraint("workspace_id", "claim_id", "position", name="pk_claim_evidence_links"),
    _check("claim_evidence_links", "position", "position >= 0"),
    _unique("claim_evidence_links", "source", "workspace_id", "claim_id", "evidence_id"),
    _foreign(
        "claim_evidence_links",
        "claim",
        ["workspace_id", "profile_id", "claim_id"],
        ["claims.workspace_id", "claims.profile_id", "claims.id"],
    ),
    _foreign(
        "claim_evidence_links",
        "evidence_snapshot",
        ["workspace_id", "profile_id", "evidence_id", "evidence_revision", "evidence_digest"],
        [
            "evidence.workspace_id",
            "evidence.profile_id",
            "evidence.id",
            "evidence.revision",
            "evidence.payload_digest",
        ],
    ),
)
cv_claim_links = _claim_links("cv_claim_links", "cv_id", "cvs")
draft_claim_links = _claim_links("draft_claim_links", "draft_id", "drafts", draft=True)

work_events = sa.Table(
    "work_events",
    metadata,
    _id("workspace_id"),
    _id("event_id"),
    _id("source"),
    _id("source_event_id", nullable=True),
    _timestamp("occurred_at"),
    _timestamp("recorded_at"),
    _id("classification"),
    _id("activity"),
    sa.Column("payload", sa.Text(), nullable=False),
    _id("payload_digest"),
    sa.PrimaryKeyConstraint("workspace_id", "event_id", name="pk_work_events"),
    *_scope_constraints("work_events"),
    *_payload_constraints("work_events", "event_id", "privacy_classification"),
    _unique("work_events", "source_identity", "workspace_id", "source", "source_event_id"),
    _check("work_events", "event_id", "event_id ~ '^event_[0-9a-f]{32}$'"),
    _check(
        "work_events",
        "source_event_id",
        "source_event_id IS NULL OR source_event_id ~ '^source_event_[0-9a-f]{32}$'",
    ),
    _check("work_events", "source", "source IN ('manual','careerlab','local_domain')"),
    _check("work_events", "activity", f"activity IN {_ACTIVITIES}"),
    _check("work_events", "chronology", "recorded_at >= occurred_at"),
    _check(
        "work_events",
        "event_metadata",
        "payload::jsonb @> jsonb_build_object('source', source, 'source_event_id', "
        "source_event_id, 'activity', activity) AND payload::jsonb "
        "?& ARRAY['occurred_at','recorded_at'] AND "
        "(payload::jsonb->>'occurred_at')::timestamptz IS NOT DISTINCT FROM occurred_at AND "
        "(payload::jsonb->>'recorded_at')::timestamptz IS NOT DISTINCT FROM recorded_at",
    ),
)

event_object_refs = sa.Table(
    "event_object_refs",
    metadata,
    _id("workspace_id"),
    _id("event_id"),
    _integer("position"),
    _id("kind"),
    _id("object_id"),
    _integer("revision"),
    _id("digest"),
    _id("classification"),
    sa.PrimaryKeyConstraint("workspace_id", "event_id", "position", name="pk_event_object_refs"),
    _check("event_object_refs", "position", "position >= 0"),
    _check("event_object_refs", "revision", "revision BETWEEN 1 AND 2147483647"),
    _check("event_object_refs", "digest", "digest ~ '^[0-9a-f]{64}$'"),
    _check("event_object_refs", "classification", f"classification IN {_CLASSES}"),
    _unique("event_object_refs", "object", "workspace_id", "event_id", "kind", "object_id"),
    _foreign(
        "event_object_refs",
        "event",
        ["workspace_id", "event_id"],
        ["work_events.workspace_id", "work_events.event_id"],
    ),
    _foreign(
        "event_object_refs",
        "historical_object",
        ["workspace_id", "object_id", "kind"],
        ["object_identities.workspace_id", "object_identities.object_id", "object_identities.kind"],
    ),
)
event_evidence_refs = sa.Table(
    "event_evidence_refs",
    metadata,
    _id("workspace_id"),
    _id("event_id"),
    _integer("position"),
    _id("profile_id"),
    _id("evidence_id"),
    _integer("revision"),
    _id("digest"),
    _id("classification"),
    sa.PrimaryKeyConstraint("workspace_id", "event_id", "position", name="pk_event_evidence_refs"),
    _check("event_evidence_refs", "position", "position >= 0"),
    _check("event_evidence_refs", "revision", "revision BETWEEN 1 AND 2147483647"),
    _check("event_evidence_refs", "digest", "digest ~ '^[0-9a-f]{64}$'"),
    _check("event_evidence_refs", "classification", f"classification IN {_CLASSES}"),
    _unique(
        "event_evidence_refs", "evidence", "workspace_id", "event_id", "profile_id", "evidence_id"
    ),
    _foreign(
        "event_evidence_refs",
        "event",
        ["workspace_id", "event_id"],
        ["work_events.workspace_id", "work_events.event_id"],
    ),
    _foreign(
        "event_evidence_refs",
        "historical_evidence",
        ["workspace_id", "profile_id", "evidence_id"],
        ["evidence.workspace_id", "evidence.profile_id", "evidence.id"],
    ),
)

deletion_ledger = sa.Table(
    "deletion_ledger",
    metadata,
    _id("workspace_id"),
    _timestamp("deleted_at"),
    sa.PrimaryKeyConstraint("workspace_id", name="pk_deletion_ledger"),
    _check("deletion_ledger", "workspace_id", "workspace_id ~ '^workspace_[0-9a-f]{32}$'"),
)

CURRENT_TABLES: dict[str, sa.Table] = {
    "company": companies,
    "job": jobs,
    "profile": profiles,
    "evidence": evidence,
    "claim": claims,
    "cv": cvs,
    "draft": drafts,
    "application": applications,
    "requirement": requirements,
}
