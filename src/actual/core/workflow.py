"""Content review/effect values only. No workflow graph, permission or executor."""

from typing import Literal

from .primitives import ActorId, Contract, Digest, Instant, Label, Revision

type EffectKind = Literal["READ_ONLY", "LOCAL_WRITE", "EXTERNAL_WRITE"]


class ContentReview(Contract):
    revision: Revision
    content_digest: Digest
    reviewer_id: ActorId
    reviewed_at: Instant
    method: Label
    decision: Literal["accepted", "rejected"]
