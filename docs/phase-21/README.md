# General personal workflow families

IMPLEMENTED synthetic families; canonical acceptance PENDING.

Two small families use the same typed graph, deterministic handler registry, runtime and replay: structured meeting notes to action records, and email-subject triage. The catalog extension is additive; existing capability semantics and definition bytes are preserved. No new provider, model, calendar, task API or mailbox is introduced.

Meeting processing accepts closed synthetic structured notes, preserves each explicit task/assignee/deadline and keeps missing fields unknown. It does not infer actions from free prose, invent dates or verify an assignment. Malformed notes route to explicit failure. Subject triage marks only an explicit `FYI:` prefix routine; other subjects go to a human-review disposition. That disposition completes classification, not the human's work. No email is sent, archived or fetched.

Tests exercise both families through the existing runtime, unknown-date preservation, malicious unstructured input, conservative branches and exact preservation of the original text workflow. Real mailbox/calendar interoperability, ambiguous prose interpretation, user validation and domain-specific accuracy remain pending; these are public development examples, not held-out evidence.
