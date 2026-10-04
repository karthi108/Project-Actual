"""Lossless canonical contracts with explicitly derived relational projections."""

import hashlib
from typing import Any, Literal

from sqlalchemy import Connection, Table, select

from actual.career.applications import Application
from actual.career.jobs import Company, Job, Requirement
from actual.career.materials import CVVariant, Draft
from actual.career.snapshot import CareerSnapshot
from actual.core.primitives import Contract, canonical_bytes, load_contract
from actual.core.references import BusinessObjectRef
from actual.profile.contracts import Claim, EvidenceRecord, Profile

from . import schema
from .errors import CorruptStorageError

type Record = (
    Company | Job | Profile | EvidenceRecord | Claim | CVVariant | Draft | Application | Requirement
)
type Kind = Literal[
    "company", "job", "profile", "evidence", "claim", "cv", "draft", "application", "requirement"
]
type Row = dict[str, Any]

KINDS: tuple[Kind, ...] = (
    "company",
    "job",
    "profile",
    "evidence",
    "claim",
    "cv",
    "draft",
    "application",
    "requirement",
)
CONTRACTS: dict[Kind, type[Record]] = {
    "company": Company,
    "job": Job,
    "profile": Profile,
    "evidence": EvidenceRecord,
    "claim": Claim,
    "cv": CVVariant,
    "draft": Draft,
    "application": Application,
    "requirement": Requirement,
}


def checksum(record: Contract) -> str:
    return hashlib.sha256(canonical_bytes(record)).hexdigest()


def collections(snapshot: CareerSnapshot) -> dict[Kind, tuple[Record, ...]]:
    return {
        "company": snapshot.companies,
        "job": snapshot.jobs,
        "profile": (snapshot.profile,),
        "evidence": snapshot.profile.evidence,
        "claim": snapshot.profile.claims,
        "cv": snapshot.cvs,
        "draft": snapshot.drafts,
        "application": snapshot.applications,
        "requirement": snapshot.requirements,
    }


def catalog(snapshot: CareerSnapshot) -> tuple[BusinessObjectRef, ...]:
    return tuple(
        BusinessObjectRef(
            workspace_id=record.workspace_id,
            classification=record.classification,
            kind=kind,
            object_id=record.id,
            revision=record.revision,
            content_digest=checksum(record),
        )
        for kind, records in collections(snapshot).items()
        for record in records
    )


def entity_row(record: Record, position: int, jobs: dict[str, Job]) -> Row:
    row: Row = {
        "workspace_id": record.workspace_id.root,
        "id": record.id.root,
        "position": position,
        "revision": record.revision,
        "classification": record.classification,
        "payload": canonical_bytes(record).decode("utf-8"),
        "payload_digest": checksum(record),
    }
    if isinstance(record, Job):
        row.update(
            company_id=record.company_id.root,
            opportunity_id=record.opportunity_id.root,
            posted_at=record.posted_at,
        )
    if isinstance(record, (EvidenceRecord, Claim, CVVariant, Draft, Application)):
        row["profile_id"] = record.profile_id.root
    if isinstance(record, EvidenceRecord):
        row["collected_at"] = record.collected_at
    if isinstance(record, Claim):
        row["status"] = record.status
    if isinstance(record, Application):
        row.update(
            job_id=record.job_id.root,
            state=record.state,
            opportunity_id=jobs[record.job_id.root].opportunity_id.root,
        )
    if isinstance(record, Requirement):
        row.update(
            job_id=record.job_id.root,
            job_revision=record.job_revision,
            job_digest=record.job_digest,
            opportunity_id=jobs[record.job_id.root].opportunity_id.root,
            subject=record.assertion.subject,
        )
    return row


def state_rows(snapshot: CareerSnapshot) -> dict[str, list[Row]]:
    jobs = {job.id.root: job for job in snapshot.jobs}
    rows: dict[str, list[Row]] = {}
    identities: list[Row] = []
    for kind, records in collections(snapshot).items():
        table = schema.CURRENT_TABLES[kind]
        rows[table.name] = [entity_row(record, index, jobs) for index, record in enumerate(records)]
        identities.extend(
            {
                "workspace_id": record.workspace_id.root,
                "object_id": record.id.root,
                "kind": kind,
                "revision": record.revision,
                "classification": record.classification,
                "digest": checksum(record),
            }
            for record in records
        )
    rows[schema.object_identities.name] = identities
    rows[schema.claim_evidence_links.name] = [
        {
            "workspace_id": snapshot.workspace_id.root,
            "claim_id": claim.id.root,
            "profile_id": claim.profile_id.root,
            "position": index,
            "evidence_id": ref.evidence_id.root,
            "evidence_revision": ref.revision,
            "evidence_digest": ref.content_digest,
        }
        for claim in snapshot.profile.claims
        for index, ref in enumerate(claim.evidence_refs)
    ]
    rows[schema.cv_claim_links.name] = [
        {
            "workspace_id": snapshot.workspace_id.root,
            "cv_id": cv.id.root,
            "profile_id": cv.profile_id.root,
            "position": index,
            "claim_id": ref.claim_id.root,
            "claim_revision": ref.revision,
            "claim_digest": ref.content_digest,
        }
        for cv in snapshot.cvs
        for index, ref in enumerate(cv.claim_refs)
    ]
    rows[schema.draft_claim_links.name] = [
        {
            "workspace_id": snapshot.workspace_id.root,
            "draft_id": draft.id.root,
            "profile_id": draft.profile_id.root,
            "assertion_position": assertion_index,
            "position": index,
            "claim_id": ref.claim_id.root,
            "claim_revision": ref.revision,
            "claim_digest": ref.content_digest,
        }
        for draft in snapshot.drafts
        for assertion_index, assertion in enumerate(draft.assertions)
        for index, ref in enumerate(assertion.source_claim_refs)
    ]
    return rows


def selected_rows(connection: Connection, table: Table, workspace: str) -> list[Row]:
    return [
        dict(row)
        for row in connection.execute(
            select(table).where(table.c.workspace_id == workspace)
        ).mappings()
    ]


def _row_key(row: Row) -> tuple[str, ...]:
    return tuple(str(row[key]) for key in sorted(row))


def load_snapshot(connection: Connection, workspace_row: Row) -> CareerSnapshot:
    """Reject corrupt projections instead of returning a partly trusted record."""
    workspace = workspace_row["workspace_id"]
    try:
        found: dict[Kind, tuple[Record, ...]] = {}
        for kind in KINDS:
            rows = selected_rows(connection, schema.CURRENT_TABLES[kind], workspace)
            rows.sort(key=lambda row: row["position"])
            if [row["position"] for row in rows] != list(range(len(rows))):
                raise ValueError("Noncontiguous collection order")
            records = tuple(
                load_contract(CONTRACTS[kind], row["payload"].encode("utf-8")) for row in rows
            )
            found[kind] = records
        if len(found["profile"]) != 1 or not isinstance(found["profile"][0], Profile):
            raise ValueError("Missing unique profile")
        profile = found["profile"][0]
        if profile.claims != found["claim"] or profile.evidence != found["evidence"]:
            raise ValueError("Profile child projection mismatch")
        snapshot = CareerSnapshot.model_validate(
            {
                "workspace_id": profile.workspace_id,
                "classification": workspace_row["classification"],
                "as_of": workspace_row["as_of"],
                "companies": found["company"],
                "jobs": found["job"],
                "profile": profile,
                "cvs": found["cv"],
                "drafts": found["draft"],
                "applications": found["application"],
                "requirements": found["requirement"],
            }
        )
        if (
            snapshot.workspace_id.root != workspace
            or checksum(snapshot) != workspace_row["snapshot_digest"]
        ):
            raise ValueError("Snapshot identity mismatch")
        for table_name, expected in state_rows(snapshot).items():
            actual = selected_rows(connection, schema.metadata.tables[table_name], workspace)
            if sorted(actual, key=_row_key) != sorted(expected, key=_row_key):
                raise ValueError("Relational projection mismatch")
        return snapshot
    except (ValueError, TypeError, KeyError, UnicodeError):
        raise CorruptStorageError("Stored career state failed integrity validation") from None
