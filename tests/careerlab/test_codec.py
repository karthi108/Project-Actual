"""Handcrafted boundary tests, independent of the dataset generator and labels."""

import json
from dataclasses import replace

import pytest

from actual.careerlab.codec import (
    SchemaError,
    canonical_bytes,
    load_record,
    observable_bytes,
    oracle_bytes,
    record_data,
)
from actual.careerlab.contracts import (
    Candidate,
    Company,
    FixturePair,
    GroundTruth,
    JobPosting,
    ProfileClaim,
    ScenarioInput,
    SplitMembership,
)


def tiny_input() -> ScenarioInput:
    return ScenarioInput(
        id="SCN-codec",
        schema_version="careerlab-input-v1",
        as_of="2026-10-01T12:00:00Z",
        companies=(Company(id="company-codec", name="Société Exemple", context="Synthetic"),),
        jobs=(
            JobPosting(
                id="job-codec",
                company_id="company-codec",
                canonical_opportunity="opportunity-codec",
                source_reference="https://example.invalid/codec",
                posted_at="2026-09-01T12:00:00Z",
                title="Backend engineer",
                text="Python is required.",
            ),
        ),
        candidate=Candidate(
            id="candidate-codec",
            name="Synthetic Candidate",
            claims=(
                ProfileClaim(
                    id="claim-codec",
                    subject="python",
                    value=2,
                    unit="skill_level",
                    text="I report Python experience.",
                    status="self_reported",
                    evidence_ids=(),
                ),
            ),
            evidence=(),
        ),
        cvs=(),
        draft_assertions=(),
        applications=(),
        messages=(),
    )


def tiny_oracle() -> GroundTruth:
    return GroundTruth(
        id="oracle-codec",
        schema_version="careerlab-oracle-v1",
        scenario_id="SCN-codec",
        coverage="explicit_gaps",
        requirements=(),
        acceptable_cv_ids=(),
        cv_rationale="No CV in this schema-only fixture.",
        blocked_draft_ids=(),
        duplicate_job_groups=(),
        expected_error_codes=(),
        future_outcomes=(),
        secret_canary="SYNTHETIC_CODEC_SECRET_NOT_FOR_INPUT",
    )


def tiny_membership() -> SplitMembership:
    return SplitMembership(
        id="membership-codec",
        scenario_id="SCN-codec",
        split="development",
        coverage="explicit_gaps",
        company_lineages=("company-codec",),
        candidate_lineages=("candidate-codec",),
        evidence_lineages=(),
        cv_lineages=(),
        application_lineages=(),
        template_lineages=("template-codec",),
        normalized_content_hash="0" * 64,
    )


def test_observable_roundtrip_and_canonical_utf8_lf() -> None:
    inputs = tiny_input()
    payload = observable_bytes(inputs)

    assert load_record(ScenarioInput, payload) == inputs
    assert payload == observable_bytes(inputs)
    assert payload == canonical_bytes(json.loads(payload))
    assert "Société Exemple".encode() in payload
    assert b"\\u00e9" not in payload
    assert payload.endswith(b"\n")
    assert not payload.endswith(b"\n\n")
    assert b"\r" not in payload


def test_canonical_mapping_order_does_not_affect_bytes() -> None:
    first = {"z": {"beta": 2, "alpha": 1}, "a": "café"}
    second = {"a": "café", "z": {"alpha": 1, "beta": 2}}
    assert canonical_bytes(first) == canonical_bytes(second)


@pytest.mark.parametrize("field", ["oracle", "requirements", "secret_canary", "coverage"])
def test_observable_closed_outer_record_rejects_evaluator_fields(field: str) -> None:
    data = json.loads(observable_bytes(tiny_input()))
    data[field] = "oracle leakage"
    with pytest.raises(SchemaError):
        load_record(ScenarioInput, canonical_bytes(data))


@pytest.mark.parametrize("field", ["expected_result", "rationale", "secret_canary"])
def test_observable_closed_nested_record_rejects_evaluator_fields(field: str) -> None:
    data = json.loads(observable_bytes(tiny_input()))
    data["candidate"]["claims"][0][field] = "oracle leakage"
    with pytest.raises(SchemaError):
        load_record(ScenarioInput, canonical_bytes(data))


@pytest.mark.parametrize("value", [True, False, 2.0, "2", None])
def test_integer_is_not_coerced(value: object) -> None:
    data = json.loads(observable_bytes(tiny_input()))
    data["candidate"]["claims"][0]["value"] = value
    with pytest.raises(SchemaError):
        load_record(ScenarioInput, canonical_bytes(data))


@pytest.mark.parametrize("value", [1, 0, False, "true", None])
def test_synthetic_literal_requires_exact_true(value: object) -> None:
    data = json.loads(observable_bytes(tiny_input()))
    data["synthetic"] = value
    with pytest.raises(SchemaError):
        load_record(ScenarioInput, canonical_bytes(data))


def test_nested_synthetic_marker_is_also_strict() -> None:
    data = json.loads(observable_bytes(tiny_input()))
    data["candidate"]["claims"][0]["synthetic"] = 1
    with pytest.raises(SchemaError):
        load_record(ScenarioInput, canonical_bytes(data))


@pytest.mark.parametrize(
    ("field", "value"),
    [("subject", "unregistered_skill"), ("unit", "stars"), ("status", "verified")],
)
def test_nested_enum_values_are_closed(field: str, value: str) -> None:
    data = json.loads(observable_bytes(tiny_input()))
    data["candidate"]["claims"][0][field] = value
    with pytest.raises(SchemaError):
        load_record(ScenarioInput, canonical_bytes(data))


@pytest.mark.parametrize("version", ["careerlab-input-v2", "careerlab-oracle-v1", 1])
def test_input_schema_version_is_closed(version: object) -> None:
    data = json.loads(observable_bytes(tiny_input()))
    data["schema_version"] = version
    with pytest.raises(SchemaError):
        load_record(ScenarioInput, canonical_bytes(data))


@pytest.mark.parametrize("value", [{}, "job-codec", None, 1])
def test_tuple_contract_requires_json_array(value: object) -> None:
    data = json.loads(observable_bytes(tiny_input()))
    data["jobs"] = value
    with pytest.raises(SchemaError):
        load_record(ScenarioInput, canonical_bytes(data))


@pytest.mark.parametrize("nested", [False, True])
def test_missing_explicit_field_is_rejected(nested: bool) -> None:
    data = json.loads(observable_bytes(tiny_input()))
    target = data["candidate"] if nested else data
    del target["synthetic"]
    with pytest.raises(SchemaError):
        load_record(ScenarioInput, canonical_bytes(data))


def test_duplicate_json_outer_keys_are_rejected() -> None:
    payload = observable_bytes(tiny_input())
    duplicate = b'{"id":"replacement",' + payload[1:]
    with pytest.raises(SchemaError):
        load_record(ScenarioInput, duplicate)


def test_duplicate_json_nested_keys_are_rejected() -> None:
    payload = observable_bytes(tiny_input())
    duplicate = payload.replace(b'"name":"Synthetic Candidate"', b'"name":"x","name":"y"')
    with pytest.raises(SchemaError):
        load_record(ScenarioInput, duplicate)


@pytest.mark.parametrize("payload", [b"not JSON", b"{} trailing", b"\xff", b"null"])
def test_malformed_json_is_rejected(payload: bytes) -> None:
    with pytest.raises(SchemaError):
        load_record(ScenarioInput, payload)


def test_python_created_record_uses_same_strict_validation() -> None:
    inputs = tiny_input()
    invalid = replace(
        inputs,
        candidate=replace(
            inputs.candidate,
            claims=(replace(inputs.candidate.claims[0], value=True),),
        ),
    )
    with pytest.raises(SchemaError):
        observable_bytes(invalid)


def test_observable_entrypoint_rejects_oracle_and_authoring_bundle() -> None:
    inputs, oracle = tiny_input(), tiny_oracle()
    pair = FixturePair(inputs=inputs, oracle=oracle, membership=tiny_membership())
    for value in (oracle, pair):
        with pytest.raises(SchemaError):
            observable_bytes(value)  # type: ignore[arg-type]


def test_oracle_canary_and_answers_do_not_enter_observable_payload() -> None:
    inputs, oracle = tiny_input(), tiny_oracle()
    input_payload = observable_bytes(inputs)
    assert oracle.secret_canary is not None
    assert oracle.secret_canary.encode() in oracle_bytes(oracle)
    assert oracle.secret_canary.encode() not in input_payload
    assert set(record_data(inputs)).isdisjoint(
        {"requirements", "coverage", "future_outcomes", "secret_canary", "expected_error_codes"}
    )
    assert load_record(GroundTruth, oracle_bytes(oracle)) == oracle
