"""Pinned synthetic review intents; callers cannot assign verification authority."""

from actual.core.primitives import Digest, Revision

from .commands import Command, ExpectedGeneration


class ProfileRevisionCommand(Command):
    expected_generation: ExpectedGeneration
    expected_revision: Revision
    expected_digest: Digest


class ReviewSyntheticEvidence(ProfileRevisionCommand):
    """Review one existing synthetic fixture, never certify an imported source."""


class ReviewSyntheticClaim(ProfileRevisionCommand):
    """Explicitly accept a claim against its current reviewed synthetic sources."""


class WithdrawEvidence(ProfileRevisionCommand):
    """Withdraw one current source and reconcile its exact dependent claim refs."""
