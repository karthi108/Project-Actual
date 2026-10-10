import pytest

from actual.core.primitives import ActorId, WorkspaceId
from actual.worklab.fixtures import process_observations
from actual.worklab.improvement import (
    Judgment,
    Measurements,
    Reference,
    compare_measurements,
    recommend,
)

OWNER = WorkspaceId("workspace_" + "0" * 32)


def judgment(mechanism="DETERMINISTIC", basis="structured_copy", consequence="none"):
    return Judgment(
        activity="cv_compare",
        mechanism=mechanism,
        basis=basis,
        consequence=consequence,
        references=(Reference(session="session_a", event="event_2"),),
        reviewer=ActorId("actor_" + "0" * 32),
        provenance="synthetic_design_review",
    )


def test_linked_proposals_choose_ordinary_software_and_preserve_risk():
    events = process_observations()
    proposals = recommend(events, (judgment(), judgment("ELIMINATE", "redundant_output")), OWNER)
    assert [p.mechanism for p in proposals] == ["ELIMINATE", "DETERMINISTIC"]
    assert all(p.requires_review and not p.executes and p.evidence_digest for p in proposals)
    assert (
        recommend(events, (judgment(consequence="communication"),), OWNER)[0].mechanism == "HUMAN"
    )
    assert "repetition alone" in proposals[0].reasoning
    assert all(
        p.mechanism == "HUMAN"
        for p in recommend(
            events,
            (judgment(consequence="communication"), judgment("ELIMINATE", "redundant_output")),
            OWNER,
        )
    )


def test_unlinked_evidence_cannot_support_recommendation():
    with pytest.raises(ValueError, match="matching observation"):
        recommend(
            process_observations(),
            (
                judgment().model_copy(
                    update={"references": (Reference(session="foreign", event="event_2"),)}
                ),
            ),
            OWNER,
        )
    assert recommend(process_observations(), (), OWNER) == ()


def test_only_matched_measurements_produce_time_changes():
    measured = Measurements(
        workload_digest="a" * 64, runs=2, failures=0, human_interventions=2, model_calls=0
    )
    assert compare_measurements(measured, measured)["human_active_seconds_change"] is None
    before = measured.model_copy(update={"human_active_seconds": 10.0})
    after = measured.model_copy(update={"human_active_seconds": 8.0})
    assert compare_measurements(before, after)["human_active_seconds_change"] == -2.0
    with pytest.raises(ValueError, match="Matched"):
        compare_measurements(before, after.model_copy(update={"workload_digest": "b" * 64}))
