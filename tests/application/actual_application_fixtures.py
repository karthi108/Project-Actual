"""Isolated command fixtures; this port fake makes no database-integrity claim."""

from datetime import UTC, datetime, timedelta

from actual.application import CareerState
from actual.application.commands import CompanyInput, InitializeCareer, InitialProfile, ManualJob
from actual.career.events import WorkEvent
from actual.career.snapshot import CareerSnapshot
from actual.core.primitives import (
    ActorId,
    CompanyId,
    JobId,
    OpportunityId,
    ProfileId,
    WorkspaceId,
)
from actual.profile.contracts import Assertion

NOW = datetime(2026, 10, 4, 12, tzinfo=UTC)
POSTED = NOW - timedelta(days=1)
WORKSPACE = WorkspaceId("workspace_" + "1" * 32)
ACTOR = ActorId("actor_" + "2" * 32)
PROFILE = ProfileId("profile_" + "3" * 32)


class RepositoryFailure(Exception):
    pass


class MemoryRepository:
    def __init__(self) -> None:
        self.state: CareerState | None = None
        self.observations: tuple[WorkEvent, ...] = ()
        self.calls: list[tuple[CareerSnapshot, int, tuple[WorkEvent, ...]]] = []
        self.fail_save = False

    def load(self) -> CareerState | None:
        return self.state

    def save(
        self,
        snapshot: CareerSnapshot,
        *,
        expected_generation: int,
        events: tuple[WorkEvent, ...] = (),
    ) -> CareerState:
        self.calls.append((snapshot, expected_generation, events))
        if self.fail_save:
            raise RepositoryFailure("Simulated port failure")
        generation = self.state.generation if self.state is not None else 0
        assert expected_generation == generation
        self.state = CareerState(snapshot, generation + 1)
        self.observations = (*self.observations, *events)
        return self.state

    def load_events(self) -> tuple[WorkEvent, ...]:
        return self.observations


def manual_job(number: int = 1, **updates: object) -> ManualJob:
    return ManualJob(
        id=JobId(f"job_{number:032x}"),
        opportunity_id=OpportunityId(f"opportunity_{number:032x}"),
        company=CompanyInput(
            id=CompanyId("company_" + "4" * 32),
            name="Synthetic Company",
            context="Fabricated context for use-case tests.",
        ),
        title="Synthetic engineer",
        text="Fabricated manual job posting. Python is essential.",
        source_reference="synthetic:manual-job",
        posted_at=POSTED,
    ).model_copy(update=updates)


def initialization(**updates: object) -> InitializeCareer:
    return InitializeCareer(
        expected_generation=0,
        profile=InitialProfile(id=PROFILE, name="Synthetic candidate"),
        job=manual_job(),
    ).model_copy(update=updates)


def python_assertion(value: int = 2) -> Assertion:
    return Assertion(kind="skill", subject="python", unit="skill_level", value=value)
