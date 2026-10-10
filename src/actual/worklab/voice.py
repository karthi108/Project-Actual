"""Synthetic text/STT harness; explanations are human claims, never policy."""

import re
from typing import Annotated, Literal, Protocol
from uuid import uuid4

from pydantic import Field

from actual.core.primitives import ActorId, Contract, Digest, WorkspaceId, content_digest
from actual.workflows.ir import Name
from actual.workflows.storage import Conflict

from .teach import Teach


class Transcript(Contract):
    id: Name
    explains_event: Name
    text: Annotated[str, Field(min_length=1, max_length=4096)]
    classification: Literal["synthetic"] = "synthetic"


class AudioFixture(Contract):
    fixture: Literal["missing_evidence", "conflicting_evidence"]
    duration_ms: Annotated[int, Field(ge=1, le=30_000)]
    classification: Literal["synthetic"] = "synthetic"


class LocalSTTPort(Protocol):
    def transcribe(self, sample: AudioFixture, identifier: str, event: str) -> Transcript: ...


class FakeSTT:
    def transcribe(self, sample: AudioFixture, identifier: str, event: str) -> Transcript:
        sample = AudioFixture.model_validate(sample)
        return Transcript(
            id=identifier,
            explains_event=event,
            text=(
                "When evidence is missing, ask a human because support is absent."
                if sample.fixture == "missing_evidence"
                else "When evidence conflicts, ask a human because verification is needed."
            ),
        )


class CandidateRule(Contract):
    id: Name
    workspace_id: WorkspaceId
    speaker: ActorId
    session: Name
    explains_event: Name
    transcript_digest: Digest
    condition: Literal["missing_evidence", "conflicting_evidence", "ambiguous_input"]
    action: Literal["ask_human"] = "ask_human"
    rationale: Literal["missing_support", "verification_needed", "unclear_request"]
    source: Literal["human_claim"] = "human_claim"
    state: Literal["candidate", "confirmed", "withdrawn"] = "candidate"
    confirmed_by: ActorId | None = None

    @property
    def digest(self) -> str:
        return content_digest(self.model_dump(mode="json"))


PHRASES: dict[
    str,
    tuple[
        Literal["missing_evidence", "conflicting_evidence", "ambiguous_input"],
        Literal["missing_support", "verification_needed", "unclear_request"],
    ],
] = {
    "when evidence is missing, ask a human because support is absent.": (
        "missing_evidence",
        "missing_support",
    ),
    "when evidence conflicts, ask a human because verification is needed.": (
        "conflicting_evidence",
        "verification_needed",
    ),
    "when input is ambiguous, ask a human because the request is unclear.": (
        "ambiguous_input",
        "unclear_request",
    ),
}
PRIVATE = re.compile(
    r"password|secret|token|authorization|bearer|@[a-z0-9]|\b\d{6,}\b", re.IGNORECASE
)


class VoiceTeach:
    def __init__(self, teach: Teach):
        self.teach = teach
        self.rules: dict[str, CandidateRule] = {}
        self.sources: dict[str, str] = {}

    def propose(self, transcript: Transcript) -> CandidateRule:
        transcript = Transcript.model_validate(transcript)
        session = self.teach.session
        if (
            session is None
            or session.state != "active"
            or not self.teach.display.visible(session)
            or "synthetic_voice" not in session.allowed
            or "synthetic_voice" in session.denied
        ):
            raise Conflict("Explicit visible allowed voice session required")
        if not any(
            e.source_event == transcript.explains_event and e.session == session.id
            for e in self.teach.events
        ):
            raise Conflict("Explanation must reference this session's observed event")
        if PRIVATE.search(transcript.text):
            raise ValueError("Transcript excluded by local privacy filter")
        phrase = PHRASES.get(transcript.text.strip().casefold())
        if phrase is None:
            raise ValueError("Unrecognized explanation requires manual review")
        digest = content_digest(transcript.model_dump(mode="json"))
        key = session.id + ":" + transcript.id
        previous = self.sources.get(key)
        if previous is not None:
            if self.rules[previous].transcript_digest != digest:
                raise Conflict("Transcript identity conflict")
            return self.rules[previous]
        if len(self.rules) >= 128:
            raise Conflict("Candidate explanation budget exhausted")
        rule = CandidateRule(
            id="rule_" + uuid4().hex,
            workspace_id=self.teach.owner,
            speaker=self.teach.actor,
            session=session.id,
            explains_event=transcript.explains_event,
            transcript_digest=digest,
            condition=phrase[0],
            rationale=phrase[1],
        )
        self.rules[rule.id], self.sources[key] = rule, rule.id
        return rule

    def confirm(self, identifier: str, reviewed_digest: str) -> CandidateRule:
        rule = self.rules[identifier]
        if rule.state != "candidate" or rule.digest != reviewed_digest:
            raise Conflict("Stale candidate explanation review")
        confirmed = rule.model_copy(update={"state": "confirmed", "confirmed_by": self.teach.actor})
        self.rules[identifier] = confirmed
        return confirmed

    def withdraw(self, identifier: str) -> CandidateRule:
        rule = self.rules[identifier].model_copy(update={"state": "withdrawn"})
        self.rules[identifier] = rule
        return rule
