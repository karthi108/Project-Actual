import json

import pytest
from pydantic import ValidationError

from actual.workflows.examples import effect_workflow, text_workflow
from actual.workflows.ir import Workflow


def raw() -> dict:
    return effect_workflow().model_dump(mode="json")


def test_examples_are_closed_immutable_and_roundtrip():
    for workflow in (effect_workflow(), text_workflow()):
        assert Workflow.model_validate_json(workflow.model_dump_json()) == workflow
        assert len(workflow.digest) == 64
        with pytest.raises(ValidationError):
            workflow.version = 2


@pytest.mark.parametrize(
    "change",
    [
        "cycle",
        "missing",
        "duplicate",
        "unknown",
        "weak_effect",
        "weak_permission",
        "bypass_policy",
        "denial_write",
        "budget",
        "wrong_type",
        "arbitrary_code",
        "classification",
    ],
)
def test_invalid_workflows_fail_closed(change):
    value = raw()
    if change == "cycle":
        value["edges"][0]["target"] = "start"
    elif change == "missing":
        value["edges"].pop()
    elif change == "duplicate":
        value["steps"].append(value["steps"][0])
    elif change == "unknown":
        value["steps"][3]["capability"] = "shell"
    elif change == "weak_effect":
        value["steps"][3]["effect"] = "READ_ONLY"
    elif change == "weak_permission":
        value["steps"][3]["permissions"] = []
    elif change == "bypass_policy":
        value["edges"][0]["target"] = "review"
    elif change == "denial_write":
        value["edges"][2]["target"] = "send"
    elif change == "budget":
        value["max_steps"] = 2
    elif change == "wrong_type":
        value["steps"][3]["inputs"][0]["value"] = True
    elif change == "arbitrary_code":
        value["steps"][3]["python"] = "print('not executed')"
    else:
        value["classification"] = "personal"
    with pytest.raises(ValueError):
        Workflow.model_validate_json(json.dumps(value))


def test_absent_error_output_cannot_feed_consumer():
    value = text_workflow().model_dump(mode="json")
    value["steps"].insert(
        2,
        {
            "schema_version": "actual-core-v1",
            "id": "other",
            "kind": "deterministic",
            "capability": "copy_text",
            "inputs": [
                {
                    "schema_version": "actual-core-v1",
                    "name": "text",
                    "source": "output",
                    "step": "copy",
                    "field": "text",
                }
            ],
        },
    )
    value["edges"][1]["target"] = "other"
    value["edges"][2]["target"] = "other"
    value["edges"].extend(
        [
            {
                "schema_version": "actual-core-v1",
                "source": "other",
                "outcome": "success",
                "target": "done",
            },
            {
                "schema_version": "actual-core-v1",
                "source": "other",
                "outcome": "error",
                "target": "failed",
            },
        ]
    )
    with pytest.raises(ValueError, match="absent"):
        Workflow.model_validate_json(json.dumps(value))


def test_duplicate_trigger_fields_and_duration_budget_fail():
    workflow = text_workflow()
    with pytest.raises(ValueError, match="Duplicate trigger"):
        workflow.model_copy(update={"trigger_schema": workflow.trigger_schema * 2})
    with pytest.raises(ValueError, match="Duration budget"):
        workflow.model_copy(update={"max_duration_seconds": 1})
