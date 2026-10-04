"""The exact aggregate port used by Career commands; commits belong to save."""

from dataclasses import dataclass
from typing import Protocol

from actual.career.events import WorkEvent
from actual.career.snapshot import CareerSnapshot


@dataclass(frozen=True)
class CareerState:
    snapshot: CareerSnapshot
    generation: int


class CareerRepository(Protocol):
    def load(self) -> CareerState | None: ...

    def save(
        self,
        snapshot: CareerSnapshot,
        *,
        expected_generation: int,
        events: tuple[WorkEvent, ...] = (),
    ) -> CareerState: ...

    def load_events(self) -> tuple[WorkEvent, ...]: ...
