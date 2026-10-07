from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from actual.core.primitives import ActorId, WorkspaceId
from actual.workflows.storage import Conflict
from actual.worklab.teach import Observation, Teach

NOW = datetime(2026, 10, 7, tzinfo=UTC)


class Visible:
    showing = True

    def show(self, session):
        return self.showing

    def visible(self, session):
        return self.showing


def observer():
    return Teach(WorkspaceId("workspace_" + "0" * 32), ActorId("actor_" + "0" * 32), Visible())


def event(**changes):
    return Observation(
        source_event="event_one",
        application="synthetic_career",
        activity="job_open",
        business_object="fabricated_job",
        occurred_at=NOW,
    ).model_copy(update=changes)


def test_visible_explicit_state_and_session_identity():
    teach = observer()
    with pytest.raises(Conflict):
        teach.ingest(event(), NOW)
    first = teach.start(("synthetic_career",))
    assert teach.ingest(event(), NOW).session == first.id
    teach.transition("paused")
    with pytest.raises(Conflict):
        teach.ingest(event(), NOW)
    teach.transition("active")
    teach.transition("stopped")
    teach.delete()
    assert teach.events == ()
    assert teach.start(("synthetic_career",)).id != first.id


@pytest.mark.parametrize(
    "changes",
    [
        {"field_kind": "password"},
        {"field_kind": "sensitive"},
        {"classification": "sensitive"},
        {"application": "private_app"},
    ],
)
def test_local_preprocessing_excludes_sensitive_and_unallowed(changes):
    teach = observer()
    teach.start(("synthetic_career",))
    assert teach.ingest(event(**changes), NOW) is None and teach.events == ()


def test_denylist_wins_and_raw_fields_are_not_admitted():
    teach = observer()
    teach.start(("synthetic_career",), ("synthetic_career",))
    assert teach.ingest(event(), NOW) is None
    with pytest.raises(ValidationError):
        Observation.model_validate(
            {**event().model_dump(mode="python"), "raw_password": "fabricated"}
        )


def test_lost_indicator_stops_intake_and_duplicates_conflict():
    display = Visible()
    teach = Teach(WorkspaceId("workspace_" + "0" * 32), ActorId("actor_" + "0" * 32), display)
    teach.start(("synthetic_career",))
    first = teach.ingest(event(), NOW)
    assert teach.ingest(event(), NOW) == first
    with pytest.raises(Conflict):
        teach.ingest(event(activity="cv_compare"), NOW)
    display.showing = False
    with pytest.raises(Conflict):
        teach.ingest(event(), NOW)
    with pytest.raises(Conflict):
        teach.transition("stopped")
    assert teach.session.state == "stopped"
