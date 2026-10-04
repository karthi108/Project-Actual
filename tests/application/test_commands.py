"""Intent models cannot accept domain authority or invalid primitive values."""

import pytest
from actual_application_fixtures import NOW, initialization, manual_job, python_assertion
from pydantic import ValidationError

from actual.application.commands import (
    AddJob,
    AttachEvidence,
    CreateApplication,
    CreateClaim,
    InitializeCareer,
    TransitionApplication,
)
from actual.core.primitives import ApplicationId, ClaimId, EvidenceId


def command_examples() -> tuple[object, ...]:
    claim_id = ClaimId("claim_" + "5" * 32)
    return (
        initialization(),
        AddJob(expected_generation=1, job=manual_job()),
        CreateClaim(
            expected_generation=1, id=claim_id, assertion=python_assertion(), text="Synthetic claim"
        ),
        AttachEvidence(
            expected_generation=1,
            id=EvidenceId("evidence_" + "6" * 32),
            claim_id=claim_id,
            assertion=python_assertion(),
            relation="supports",
            source_kind="user_report",
            source_reference="synthetic:declared-evidence",
            excerpt="Synthetic evidence excerpt",
            collected_at=NOW,
        ),
        CreateApplication(
            expected_generation=1,
            id=ApplicationId("application_" + "7" * 32),
            job_id=manual_job().id,
            occurred_at=NOW,
        ),
        TransitionApplication(expected_generation=1, state="closed", occurred_at=NOW),
    )


@pytest.mark.parametrize("command", command_examples())
def test_intents_have_their_own_version_and_round_trip(command: object) -> None:
    assert command.schema_version == "actual-api-v1"
    assert type(command).model_validate_json(command.model_dump_json()) == command
    with pytest.raises(ValidationError):
        command.expected_generation = 4


@pytest.mark.parametrize(
    "field", ["workspace_id", "actor_id", "classification", "status", "review", "history"]
)
def test_request_cannot_supply_domain_authority(field: str) -> None:
    command = command_examples()[2]
    with pytest.raises(ValidationError):
        type(command).model_validate({**command.model_dump(), field: "unsafe-client-value"})


@pytest.mark.parametrize("value", [True, "1", 1.0, -1, 0, 9223372036854775807])
def test_mutation_generation_is_a_strict_bounded_positive_integer(value: object) -> None:
    with pytest.raises(ValidationError):
        AddJob(expected_generation=value, job=manual_job())


@pytest.mark.parametrize("value", [False, "0", 0.0, -1, 1])
def test_initialization_generation_is_exactly_integer_zero(value: object) -> None:
    with pytest.raises(ValidationError):
        InitializeCareer.model_validate(
            {**initialization().model_dump(), "expected_generation": value}
        )


def test_unknown_version_naive_time_and_string_boolean_fail_closed() -> None:
    command = TransitionApplication(expected_generation=1, state="closed", occurred_at=NOW)
    for updates in (
        {"schema_version": "actual-api-v2"},
        {"occurred_at": NOW.replace(tzinfo=None)},
        {"external_manual": "false"},
    ):
        with pytest.raises(ValidationError):
            TransitionApplication.model_validate({**command.model_dump(), **updates})


def test_validation_error_text_hides_sensitive_inputs() -> None:
    marker = "private-profile-content-marker"
    with pytest.raises(ValidationError) as captured:
        CreateClaim.model_validate({"id": marker, "expected_generation": marker})
    assert marker not in str(captured.value)
