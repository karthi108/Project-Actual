import pytest

from actual.workflows.runtime import Runtime
from actual.worklab.evaluator import answers, evaluate
from actual.worklab.fixtures import observations
from actual.worklab.replay import Case, Memory, replay


def test_replay_same_runtime_and_exact_development_answers():
    cases = observations()
    results = tuple(replay(c) for c in cases)
    report = evaluate(results, answers())
    assert report == {
        "cases": 5,
        "expected_status_matches": 5,
        "branch_matches": 5,
        "completed": 2,
        "human_escalations": 1,
        "workflow_failures": 2,
        "policy_denials": 1,
        "invalid_tool_calls": 0,
        "provider_calls": 0,
        "unsupported_ai_claims": None,
    }
    assert tuple(replay(c) for c in cases) == results
    assert all("expected" not in c.model_dump_json() for c in cases)
    assert all(Case.model_validate_json(c.model_dump_json()) == c for c in cases)


def test_provider_handles_are_rejected_and_dispatch_guard_remains_closed():
    class EffectSpy:
        def execute(self, *args):
            pytest.fail("Replay cannot dispatch")

    memory = Memory(observations()[-1])
    with pytest.raises(ValueError, match="provider handles"):
        Runtime(memory, mode="replay", effects=EffectSpy())
    runtime = Runtime(memory, mode="replay", clock=lambda: memory.run.started_at)
    runtime.effects = EffectSpy()
    memory.run = memory.run.model_copy(update={"current": "send"})
    assert runtime.tick(memory.run.id).failure_code == "mode_denied"


def test_evaluator_rejects_duplicate_membership():
    results = tuple(replay(c) for c in observations())
    with pytest.raises(ValueError, match="membership"):
        evaluate((*results[:-1], results[0]), answers())
