"""Bounded deterministic summaries of observed sessions, never executable policy."""

from collections import Counter, defaultdict
from statistics import mean, median
from typing import Annotated

from pydantic import Field

from actual.core.primitives import Contract, WorkspaceId, content_digest

from .teach import Activity, Event


class Sequence(Contract):
    activities: tuple[Activity, ...]
    occurrences: Annotated[int, Field(ge=1)]


class Transition(Contract):
    source: Activity
    target: Activity
    occurrences: Annotated[int, Field(ge=1)]


class Timing(Contract):
    activity: Activity
    observations: Annotated[int, Field(ge=1)]
    mean_elapsed_seconds: Annotated[float, Field(ge=0)]
    median_elapsed_seconds: Annotated[float, Field(ge=0)]


class Discovery(Contract):
    sessions: Annotated[int, Field(ge=0)]
    events: Annotated[int, Field(ge=0)]
    variants: tuple[Sequence, ...]
    repeated_sequences: tuple[Sequence, ...]
    transitions: tuple[Transition, ...]
    branch_points: tuple[Activity, ...]
    observed_loops: Annotated[int, Field(ge=0)]
    rework_events: Annotated[int, Field(ge=0)]
    session_elapsed_seconds: tuple[float, ...]
    bottlenecks: tuple[Timing, ...]


def discover(events: tuple[Event, ...], owner: WorkspaceId) -> Discovery:
    owner = WorkspaceId.model_validate(owner)
    if len(events) > 20_000:
        raise ValueError("Discovery input budget exceeded")
    groups: dict[str, list[Event]] = defaultdict(list)
    identities: dict[tuple[str, str], str] = {}
    actors: dict[str, str] = {}
    for event in events:
        event = Event.model_validate(event)
        if event.workspace_id != owner:
            raise ValueError("Discovery owner mismatch")
        if event.session in actors and actors[event.session] != event.actor_id.root:
            raise ValueError("Session actor mismatch")
        actors[event.session] = event.actor_id.root
        key = event.session, event.source_event
        digest = content_digest(event.model_dump(mode="json", exclude={"recorded_at"}))
        if key in identities:
            if identities[key] != digest:
                raise ValueError("Conflicting observation identity")
            continue
        identities[key] = digest
        groups[event.session].append(event)
    if len(groups) > 128:
        raise ValueError("Discovery session budget exceeded")
    variants: Counter[tuple[Activity, ...]] = Counter()
    repeated: Counter[tuple[Activity, ...]] = Counter()
    transitions: Counter[tuple[Activity, Activity]] = Counter()
    times: dict[Activity, list[float]] = defaultdict(list)
    elapsed: list[float] = []
    rework = loops = 0
    for session in sorted(groups):
        ordered = sorted(groups[session], key=lambda e: e.occurred_at)
        if len({e.occurred_at for e in ordered}) != len(ordered):
            raise ValueError("Ambiguous same-time observation order")
        sequence = tuple(e.activity for e in ordered)
        variants[sequence] += 1
        rework += len(sequence) - len(set(sequence))
        loops += len(sequence) - len(set(sequence))
        elapsed.append((ordered[-1].occurred_at - ordered[0].occurred_at).total_seconds())
        for length in (2, 3, 4):
            for index in range(len(sequence) - length + 1):
                repeated[sequence[index : index + length]] += 1
        for before, after in zip(ordered, ordered[1:], strict=False):
            transitions[before.activity, after.activity] += 1
            times[before.activity].append((after.occurred_at - before.occurred_at).total_seconds())
    successors: dict[Activity, set[Activity]] = defaultdict(set)
    for source, target in transitions:
        successors[source].add(target)
    return Discovery(
        sessions=len(groups),
        events=len(identities),
        variants=tuple(
            Sequence(activities=seq, occurrences=n) for seq, n in sorted(variants.items())
        ),
        repeated_sequences=tuple(
            Sequence(activities=seq, occurrences=n) for seq, n in sorted(repeated.items()) if n >= 2
        ),
        transitions=tuple(
            Transition(source=a, target=b, occurrences=n)
            for (a, b), n in sorted(transitions.items())
        ),
        branch_points=tuple(sorted(a for a, following in successors.items() if len(following) > 1)),
        observed_loops=loops,
        rework_events=rework,
        session_elapsed_seconds=tuple(elapsed),
        bottlenecks=tuple(
            sorted(
                (
                    Timing(
                        activity=a,
                        observations=len(values),
                        mean_elapsed_seconds=float(mean(values)),
                        median_elapsed_seconds=float(median(values)),
                    )
                    for a, values in times.items()
                ),
                key=lambda t: (-t.mean_elapsed_seconds, t.activity),
            )
        ),
    )
