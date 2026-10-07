"""Visible synthetic semantic sessions; no device, screen or browser capture."""

from datetime import datetime
from typing import Annotated, Literal, Protocol
from uuid import uuid4

from pydantic import Field

from actual.core.primitives import ActorId, Contract, Instant, WorkspaceId, content_digest
from actual.workflows.ir import Name
from actual.workflows.storage import Conflict

type Activity = Literal[
    "job_open", "company_research", "cv_compare", "application_prepare", "tracker_update"
]
type SessionState = Literal["active", "paused", "stopped"]


class Observation(Contract):
    source_event: Name
    application: Name
    activity: Activity
    business_object: Name
    occurred_at: Instant
    classification: Literal["synthetic", "sensitive"] = "synthetic"
    field_kind: Literal["semantic", "password", "sensitive"] = "semantic"


class Event(Contract):
    teach_version: Literal["actual-teach-v1"] = "actual-teach-v1"
    workspace_id: WorkspaceId
    actor_id: ActorId
    session: Name
    source_event: Name
    application: Name
    activity: Activity
    business_object: Name
    occurred_at: Instant
    recorded_at: Instant
    classification: Literal["synthetic"] = "synthetic"


class Session(Contract):
    id: Name
    state: SessionState
    allowed: Annotated[tuple[Name, ...], Field(max_length=8)]
    denied: Annotated[tuple[Name, ...], Field(max_length=8)]
    visible_indicator: Literal[True] = True
    observed_examples: Literal[1] = 1


class Display(Protocol):
    def show(self, session: Session) -> bool: ...
    def visible(self, session: Session) -> bool: ...


class ConsoleDisplay:
    def __init__(self) -> None:
        self.session: Session | None = None

    def show(self, session: Session) -> bool:
        print(f"Simulated Teach session: {session.state}. Synthetic semantic events only.")
        self.session = session
        return True

    def visible(self, session: Session) -> bool:
        return self.session == session


class Teach:
    def __init__(self, owner: WorkspaceId, actor: ActorId, display: Display):
        self.owner, self.actor = WorkspaceId.model_validate(owner), ActorId.model_validate(actor)
        self.display = display
        self.session: Session | None = None
        self.events: tuple[Event, ...] = ()
        self.identities: dict[str, str] = {}

    def start(self, allowed: tuple[str, ...], denied: tuple[str, ...] = ()) -> Session:
        if self.session is not None and self.session.state != "stopped":
            raise Conflict("Stop the current session before starting another")
        session = Session(
            id="session_" + uuid4().hex, state="active", allowed=allowed, denied=denied
        )
        if (
            not session.allowed
            or len(set(session.allowed)) != len(session.allowed)
            or len(set(session.denied)) != len(session.denied)
        ):
            raise ValueError("Explicit unique application allowlist required")
        if not self.display.show(session):
            raise Conflict("Visible session indicator required")
        self.session, self.events, self.identities = session, (), {}
        return session

    def transition(self, state: SessionState) -> Session:
        if self.session is None or self.session.state == "stopped" or state == self.session.state:
            raise Conflict("Invalid session transition")
        changed = self.session.model_copy(update={"state": state})
        # Pause/stop always close capture, including when presentation fails.
        if state != "active":
            self.session = changed
        if not self.display.show(changed):
            raise Conflict("Visible session indicator unavailable")
        self.session = changed
        return changed

    def ingest(self, observation: Observation, recorded_at: datetime) -> Event | None:
        observation = Observation.model_validate(observation)
        session = self.session
        if session is None or session.state != "active" or not self.display.visible(session):
            raise Conflict("Explicit visible active session required")
        if (
            observation.application not in session.allowed
            or observation.application in session.denied
            or observation.classification != "synthetic"
            or observation.field_kind != "semantic"
        ):
            return None
        digest = content_digest(observation.model_dump(mode="json"))
        previous = self.identities.get(observation.source_event)
        if previous is not None:
            if previous != digest:
                raise Conflict("Source event identity conflict")
            return next(e for e in self.events if e.source_event == observation.source_event)
        if len(self.events) >= 2000:
            raise Conflict("Session event budget exhausted")
        event = Event(
            workspace_id=self.owner,
            actor_id=self.actor,
            session=session.id,
            source_event=observation.source_event,
            application=observation.application,
            activity=observation.activity,
            business_object=observation.business_object,
            occurred_at=observation.occurred_at,
            recorded_at=recorded_at,
        )
        self.events = (*self.events, event)
        self.identities[observation.source_event] = digest
        return event

    def delete(self) -> None:
        if self.session is not None and self.session.state != "stopped":
            raise Conflict("Stop the session before deleting observations")
        self.events, self.identities = (), {}
