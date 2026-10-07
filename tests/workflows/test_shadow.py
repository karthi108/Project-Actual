import pytest

from actual.worklab.fixtures import observations
from actual.worklab.shadow import Transition, compare


def test_matching_trace_is_candidate_evidence_without_activation():
    case = observations()[0]
    result = compare(
        case,
        (Transition(step="start", outcome="success"), Transition(step="copy", outcome="success")),
    )
    assert result.disagreements == () and result.produced.provider_calls == 0
    assert next(r for r in result.readiness if r.step == "copy").state == "candidate"
    assert "activation" not in result.model_dump_json()


def test_variant_disagreement_is_recorded_per_step():
    result = compare(
        observations()[1],
        (
            Transition(step="start", outcome="success"),
            Transition(step="predicate", outcome="success"),
            Transition(step="branch", outcome="false"),
        ),
    )
    assert result.disagreements == ("branch",)
    assert next(r for r in result.readiness if r.step == "branch").state == "shadow"


def test_human_and_effect_steps_remain_human():
    result = compare(
        observations()[-1],
        (Transition(step="start", outcome="success"), Transition(step="policy", outcome="allow")),
    )
    assert result.produced.human_escalation
    assert {r.step for r in result.readiness if r.state == "human"} == {"review", "send"}


def test_invalid_human_path_rejected():
    with pytest.raises(ValueError, match="registered path"):
        compare(observations()[0], (Transition(step="send", outcome="success"),))
