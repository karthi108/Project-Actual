"""Composition root adapts the accepted store to the application port."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import cast

from fastapi import Request
from sqlalchemy import Engine

from actual.application.ports import CareerState
from actual.application.service import CareerService
from actual.career.events import WorkEvent
from actual.career.snapshot import CareerSnapshot
from actual.persistence.errors import NotFoundError
from actual.persistence.repository import CareerStore

from .config import ApiSettings


class StoreAdapter:
    def __init__(self, store: CareerStore) -> None:
        self.store = store

    def load(self) -> CareerState | None:
        try:
            stored = self.store.load()
        except NotFoundError:
            return None
        return CareerState(stored.snapshot, stored.generation)

    def save(
        self,
        snapshot: CareerSnapshot,
        *,
        expected_generation: int,
        events: tuple[WorkEvent, ...] = (),
    ) -> CareerState:
        stored = self.store.save(snapshot, expected_generation=expected_generation, events=events)
        return CareerState(stored.snapshot, stored.generation)

    def load_events(self) -> tuple[WorkEvent, ...]:
        return self.store.load_events()


@dataclass(frozen=True)
class ApiRuntime:
    settings: ApiSettings
    engine: Engine
    clock: Callable[[], datetime]


def runtime(request: Request) -> ApiRuntime:
    return cast(ApiRuntime, request.app.state.runtime)


def career_service(request: Request) -> CareerService:
    configured = runtime(request)
    return CareerService(
        StoreAdapter(CareerStore(configured.engine, configured.settings.workspace_id)),
        configured.settings.workspace_id,
        configured.settings.actor_id,
        configured.clock,
    )
