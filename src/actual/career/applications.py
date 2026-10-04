"""Historical reported application states; no delivery proof or artifact approval."""

from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from actual.core.primitives import (
    ActorId,
    ApplicationId,
    Classification,
    Contract,
    Instant,
    JobId,
    ProfileId,
    Revision,
    WorkspaceId,
    content_digest,
)

type ApplicationState = Literal[
    "preparing", "ready_for_review", "reviewed", "applied", "interview", "offer", "closed"
]
type ObservationBasis = Literal["user_reported", "synthetic_observation"]

_TRANSITIONS: dict[ApplicationState, frozenset[ApplicationState]] = {
    "preparing": frozenset({"ready_for_review", "closed"}),
    "ready_for_review": frozenset({"preparing", "reviewed", "closed"}),
    "reviewed": frozenset({"preparing", "applied", "closed"}),
    "applied": frozenset({"interview", "closed"}),
    "interview": frozenset({"offer", "closed"}),
    "offer": frozenset({"closed"}),
    "closed": frozenset(),
}


def allowed_transition(
    previous: ApplicationState,
    target: ApplicationState,
    basis: ObservationBasis,
    external_manual: bool,
) -> bool:
    """Tracking an external manual submission does not invent an internal review."""
    if basis not in ("user_reported", "synthetic_observation") or type(external_manual) is not bool:
        return False
    if external_manual:
        return (
            basis == "user_reported"
            and previous in ("preparing", "ready_for_review")
            and target == "applied"
        )
    return target in _TRANSITIONS.get(previous, frozenset())


class StatusObservation(Contract):
    actor_id: ActorId
    occurred_at: Instant
    recorded_at: Instant
    state: ApplicationState
    basis: ObservationBasis
    external_manual: Annotated[bool, Field(strict=True)] = False

    @model_validator(mode="after")
    def valid_observation(self) -> Self:
        if self.recorded_at < self.occurred_at:
            raise ValueError("Status cannot be recorded before occurrence")
        if self.external_manual and (self.state != "applied" or self.basis != "user_reported"):
            raise ValueError(
                "External manual tracking requires a user-reported applied observation"
            )
        return self


class Application(Contract):
    id: ApplicationId
    workspace_id: WorkspaceId
    revision: Revision
    classification: Classification
    job_id: JobId
    profile_id: ProfileId
    state: ApplicationState
    history: Annotated[tuple[StatusObservation, ...], Field(min_length=1, max_length=500)]

    @property
    def content_digest(self) -> str:
        return content_digest(self.model_dump(mode="json"))

    @model_validator(mode="after")
    def valid_history(self) -> Self:
        if self.history[0].state != "preparing" or self.history[0].external_manual:
            raise ValueError("Application history must begin with preparing")
        if self.state != self.history[-1].state:
            raise ValueError("Application current state differs from its last observation")
        for previous, target in zip(self.history, self.history[1:], strict=False):
            if target.occurred_at <= previous.occurred_at:
                raise ValueError("Application occurrences must be strictly increasing")
            if not allowed_transition(
                previous.state, target.state, target.basis, target.external_manual
            ):
                raise ValueError("Application transition is not permitted")
        return self
