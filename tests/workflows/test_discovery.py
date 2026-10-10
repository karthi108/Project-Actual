import pytest

from actual.core.primitives import WorkspaceId
from actual.worklab.discovery import discover
from actual.worklab.fixtures import process_observations

OWNER = WorkspaceId("workspace_" + "0" * 32)


def test_synthetic_process_ground_truth_and_arrival_order():
    events = process_observations()
    result = discover(tuple(reversed(events)), OWNER)
    assert result == discover(events, OWNER)
    assert result.sessions == 3 and result.events == 15
    assert len(result.variants) == 2 and sorted(v.occurrences for v in result.variants) == [1, 2]
    assert result.branch_points == ("cv_compare", "job_open")
    assert result.observed_loops == 1 and result.rework_events == 1
    assert result.session_elapsed_seconds == (40.0, 40.0, 50.0)
    assert result.bottlenecks[0].activity == "cv_compare"
    assert result.bottlenecks[0].mean_elapsed_seconds == 12.5
    assert (
        next(
            s
            for s in result.repeated_sequences
            if s.activities == ("cv_compare", "application_prepare", "tracker_update")
        ).occurrences
        == 3
    )
    assert sum(t.occurrences for t in result.transitions) == 12


def test_duplicates_are_not_rework_and_changed_identity_conflicts():
    events = process_observations()
    assert discover((*events, events[0]), OWNER) == discover(events, OWNER)
    with pytest.raises(ValueError, match="Conflicting observation"):
        discover((*events, events[0].model_copy(update={"activity": "cv_compare"})), OWNER)


def test_ambiguous_time_and_owner_are_rejected():
    events = process_observations()
    with pytest.raises(ValueError, match="Ambiguous"):
        discover(
            (events[0], events[1].model_copy(update={"occurred_at": events[0].occurred_at})), OWNER
        )
    with pytest.raises(ValueError, match="owner mismatch"):
        discover(events, WorkspaceId("workspace_" + "1" * 32))


def test_empty_input_is_an_empty_observation_report():
    assert discover((), OWNER).sessions == 0
