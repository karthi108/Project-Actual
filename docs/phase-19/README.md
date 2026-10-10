# Voice Teach Mode harness

IMPLEMENTED synthetic transcript/local-STT-port pipeline; canonical acceptance PENDING. Real microphone, audio decoding and recognizer interoperability are not implemented or verified.

Voice explanations require an explicit visible Teach session, allowed synthetic voice application and an exact observed event in that session. Bounded synthetic transcripts pass a local privacy abstention filter before parsing. A small deterministic phrase catalog produces structured condition/action/rationale candidates. Unknown explanations require manual review; no arbitrary expression or code is inferred. Candidate records retain a transcript digest and provenance, without raw transcript/audio.

Exact confirmation records the trusted speaker's review and preserves `human_claim` provenance. Confirmation never turns an explanation into company policy, permission, evidence verification or effect approval. Changed transcript identities and stale reviews conflict; withdrawal remains explicit. No runtime authorizer consumes these candidates.

`LocalSTTPort` and `FakeSTT` exercise the boundary using two synthetic fixture tokens, with no claim of audio recognition accuracy. No microphone or always-on recorder is opened. A real local recognizer such as faster-whisper needs dependency/version/license, model/device, permission, privacy and synthetic-audio evaluation before adoption; none was installed merely to document it.

Tests cover active-session/event binding, privacy exclusion, unknown instructions, duplicate/conflicting transcripts, exact confirmation and authority-type separation. The filter is limited defense in depth and cannot guarantee removal of private speech. Personal-device recording/UI and real STT are pending canonical integration.
