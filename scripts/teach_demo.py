"""Visible fabricated session demo; no capture device is opened."""

from datetime import UTC, datetime

from actual.core.primitives import ActorId, WorkspaceId
from actual.worklab.teach import ConsoleDisplay, Observation, Teach

if __name__ == "__main__":
    demo = Teach(
        WorkspaceId("workspace_" + "0" * 32), ActorId("actor_" + "0" * 32), ConsoleDisplay()
    )
    demo.start(("synthetic_career",))
    demo.ingest(
        Observation(
            source_event="demo_one",
            application="synthetic_career",
            activity="job_open",
            business_object="fabricated_job",
            occurred_at=datetime(2026, 10, 7, tzinfo=UTC),
        ),
        datetime.now(UTC),
    )
    demo.transition("paused")
    demo.transition("active")
    demo.transition("stopped")
    print(f"Observed {len(demo.events)} fabricated event; this session is one example.")
