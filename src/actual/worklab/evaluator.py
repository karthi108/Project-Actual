"""Evaluator-only answers; never imported by the runtime or observable fixture generator."""

from typing import Literal

from actual.core.primitives import Contract
from actual.workflows.ir import Name

from .replay import Result


class Truth(Contract):
    case: Name
    status: Literal["succeeded", "failed", "human_wait"]
    branches: tuple[Literal["true", "false"], ...] = ()


def answers() -> tuple[Truth, ...]:
    return (
        Truth(case="work_dev_copy", status="succeeded"),
        Truth(case="work_dev_nonempty", status="succeeded", branches=("true",)),
        Truth(case="work_dev_empty", status="failed", branches=("false",)),
        Truth(case="work_dev_permission", status="failed"),
        Truth(case="work_dev_review", status="human_wait"),
    )


def evaluate(results: tuple[Result, ...], expected: tuple[Truth, ...]) -> dict[str, int | None]:
    truth = {t.case: t for t in expected}
    if (
        len(results) != len(truth)
        or len({r.case for r in results}) != len(results)
        or {r.case for r in results} != set(truth)
    ):
        raise ValueError("Exact unique evaluator membership required")
    return {
        "cases": len(results),
        "expected_status_matches": sum(r.status == truth[r.case].status for r in results),
        "branch_matches": sum(r.branches == truth[r.case].branches for r in results),
        "completed": sum(r.status == "succeeded" for r in results),
        "human_escalations": sum(r.human_escalation for r in results),
        "workflow_failures": sum(r.status == "failed" for r in results),
        "policy_denials": sum(r.policy_denials for r in results),
        "invalid_tool_calls": sum(r.failure_code in ("denied", "invalid_output") for r in results),
        "provider_calls": sum(r.provider_calls for r in results),
        "unsupported_ai_claims": None,  # AI inference is unavailable and unexercised.
    }
