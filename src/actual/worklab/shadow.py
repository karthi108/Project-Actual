"""Synthetic human-path comparison; evidence of readiness never activates authority."""

import json
from datetime import datetime
from typing import Literal

from sqlalchemy import Column, DateTime, Engine, Integer, MetaData, String, Table, select, text
from sqlalchemy.dialects.postgresql import JSONB, insert

from actual.core.primitives import Contract, Digest, WorkspaceId, content_digest
from actual.workflows.ir import Name, Workflow, outcomes
from actual.workflows.schema_guard import verify
from actual.workflows.storage import Conflict

from .replay import Case, Result, replay


class Transition(Contract):
    step: Name
    outcome: Name


class Readiness(Contract):
    step: Name
    state: Literal["unobserved", "shadow", "candidate", "human"]
    matches: bool


class Comparison(Contract):
    workflow_digest: Digest
    input_digest: Digest
    human: tuple[Transition, ...]
    produced: Result
    disagreements: tuple[Name, ...]
    readiness: tuple[Readiness, ...]


def validate_path(workflow: Workflow, human: tuple[Transition, ...]) -> None:
    if len(human) > workflow.max_steps:
        raise ValueError("Human trace budget exceeded")
    current = next(s.id for s in workflow.steps if s.kind == "trigger")
    for observed in human:
        step = next(s for s in workflow.steps if s.id == current)
        if observed.step != current or observed.outcome not in outcomes(step):
            raise ValueError("Human trace is not a registered path")
        current = next(
            e.target
            for e in workflow.edges
            if e.source == current and e.outcome == observed.outcome
        )


def compare(case: Case, human: tuple[Transition, ...]) -> Comparison:
    case = Case.model_validate(case)
    human = tuple(Transition.model_validate(item) for item in human)
    validate_path(case.workflow, human)
    produced = replay(case, mode="shadow")
    observed = dict(zip(produced.steps, produced.outcomes, strict=True))
    expected = {t.step: t.outcome for t in human}
    disagreements = tuple(
        sorted(
            step
            for step in set(observed) | set(expected)
            if observed.get(step) != expected.get(step)
        )
    )
    readiness = []
    for step in case.workflow.steps:
        matches = step.id in observed and observed.get(step.id) == expected.get(step.id)
        state: Literal["unobserved", "shadow", "candidate", "human"]
        if step.effect != "READ_ONLY" or step.kind == "human_approval":
            state = "human"
        elif step.id not in observed:
            state = "unobserved"
        elif step.kind == "ai" or not matches:
            state = "shadow"
        else:
            state = "candidate"
        readiness.append(Readiness(step=step.id, state=state, matches=matches))
    return Comparison(
        workflow_digest=case.workflow.digest,
        input_digest=content_digest(case.model_dump(mode="json")),
        human=human,
        produced=produced,
        disagreements=disagreements,
        readiness=tuple(readiness),
    )


metadata = MetaData()
schema = Table("actual_shadow_schema", metadata, Column("version", Integer, primary_key=True))
records = Table(
    "actual_shadow_observations",
    metadata,
    Column("owner", String(64), primary_key=True),
    Column("event", String(48), primary_key=True),
    Column("digest", String(64), nullable=False),
    Column("payload", JSONB, nullable=False),
    Column("recorded_at", DateTime(timezone=True), nullable=False),
)


def migrate(engine: Engine) -> None:
    if engine.dialect.name != "postgresql":
        raise ValueError("PostgreSQL required")
    with engine.begin() as connection:
        connection.execute(text("SELECT pg_advisory_xact_lock(734015001)"))
        metadata.create_all(connection)
        verify(connection, metadata)
        found = connection.execute(select(schema.c.version)).scalars().all()
        if found and found != [1]:
            raise Conflict("Unsupported shadow migration version")
        if not found:
            connection.execute(schema.insert().values(version=1))


class ShadowStore:
    def __init__(self, engine: Engine, owner: WorkspaceId):
        self.engine, self.owner = engine, WorkspaceId.model_validate(owner).root

    def record(self, event: str, comparison: Comparison, now: datetime) -> Comparison:
        comparison = Comparison.model_validate(comparison)
        # Validate the opaque event token without introducing an unrestricted dictionary.
        Transition(step=event, outcome="observed")
        digest = content_digest(comparison.model_dump(mode="json"))
        with self.engine.begin() as connection:
            connection.execute(
                insert(records)
                .values(
                    owner=self.owner,
                    event=event,
                    digest=digest,
                    payload=comparison.model_dump(mode="json"),
                    recorded_at=now,
                )
                .on_conflict_do_nothing()
            )
            row = (
                connection.execute(
                    select(records)
                    .where(records.c.owner == self.owner, records.c.event == event)
                    .with_for_update()
                )
                .mappings()
                .one()
            )
            if row["digest"] != digest:
                raise Conflict("Shadow observation identity conflict")
            return Comparison.model_validate_json(json.dumps(row["payload"]))
