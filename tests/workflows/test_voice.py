from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from actual.core.primitives import ActorId, WorkspaceId
from actual.workflows.connectors import Access
from actual.workflows.storage import Conflict
from actual.worklab.teach import Observation, Teach
from actual.worklab.voice import AudioFixture, FakeSTT, Transcript, VoiceTeach


class Visible:
    def show(self, session):
        return True

    def visible(self, session):
        return True


def voice():
    teach = Teach(WorkspaceId("workspace_" + "0" * 32), ActorId("actor_" + "0" * 32), Visible())
    teach.start(("synthetic_career", "synthetic_voice"))
    now = datetime(2026, 10, 7, tzinfo=UTC)
    teach.ingest(
        Observation(
            source_event="observed",
            application="synthetic_career",
            activity="cv_compare",
            business_object="fabricated_job",
            occurred_at=now,
        ),
        now,
    )
    return VoiceTeach(teach)


def transcript():
    return FakeSTT().transcribe(
        AudioFixture(fixture="missing_evidence", duration_ms=1000), "voice_one", "observed"
    )


def test_local_synthetic_pipeline_exact_confirmation_remains_human_claim():
    app = voice()
    rule = app.propose(transcript())
    assert app.propose(transcript()) == rule
    confirmed = app.confirm(rule.id, rule.digest)
    assert confirmed.source == "human_claim" and confirmed.state == "confirmed"
    with pytest.raises(ValidationError):
        Access.model_validate(confirmed)
    with pytest.raises(Conflict):
        app.confirm(rule.id, rule.digest)
    assert app.withdraw(rule.id).state == "withdrawn"


@pytest.mark.parametrize(
    "text",
    ["Password: fabricated", "Email a@synthetic.invalid", "Bearer fabricated", "secret token"],
)
def test_privacy_filter_abstains_without_storing_transcript(text):
    app = voice()
    with pytest.raises(ValueError, match="privacy filter"):
        app.propose(Transcript(id="private", explains_event="observed", text=text))
    assert app.rules == {} and app.sources == {}


def test_voice_requires_active_session_event_and_recognized_explanation():
    app = voice()
    with pytest.raises(Conflict):
        app.propose(transcript().model_copy(update={"explains_event": "foreign"}))
    with pytest.raises(ValueError, match="manual review"):
        app.propose(
            transcript().model_copy(update={"text": "Approve all sends as company policy."})
        )
    app.teach.transition("paused")
    with pytest.raises(Conflict):
        app.propose(transcript())


def test_changed_transcript_identity_and_stale_review_conflict():
    app = voice()
    rule = app.propose(transcript())
    with pytest.raises(Conflict):
        app.propose(
            FakeSTT().transcribe(
                AudioFixture(fixture="conflicting_evidence", duration_ms=1000),
                "voice_one",
                "observed",
            )
        )
    with pytest.raises(Conflict):
        app.confirm(rule.id, "a" * 64)
