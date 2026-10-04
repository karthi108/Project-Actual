"""Public input compatibility and related-record invariant properties."""

import ast
import json
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from actual.career.jobs import Requirement
from actual.career.snapshot import CareerSnapshot
from actual.careerlab.codec import observable_bytes
from actual.careerlab.generator import generate_inputs
from actual.careerlab_bridge import ImportContext, load_observable, map_observable
from actual.core.primitives import (
    ActorId,
    CompanyId,
    EvidenceId,
    RequirementId,
    WorkspaceId,
    canonical_bytes,
    load_contract,
)
from actual.core.workflow import ContentReview
from actual.profile.contracts import EvidenceRecord, supports_assertion


def context(number: int = 1) -> ImportContext:
    return ImportContext(
        workspace_id=WorkspaceId(f"workspace_{number:032x}"), actor_id=ActorId("actor_" + "2" * 32)
    )


def snapshot(case: int = 0) -> CareerSnapshot:
    return map_observable(generate_inputs()[case], context())


def test_valid_worlds_preserve_facts_and_canonical_roundtrips() -> None:
    for source in generate_inputs()[:7]:
        result = map_observable(source, context())
        assert load_observable(observable_bytes(source), context()) == result
        assert load_contract(CareerSnapshot, canonical_bytes(result)) == result
        assert [claim.status for claim in result.profile.claims] == [
            claim.status for claim in source.candidate.claims
        ]
        for claim, observed in zip(result.profile.claims, source.candidate.claims, strict=True):
            assert (claim.assertion.subject, claim.assertion.value, claim.assertion.unit) == (
                observed.subject,
                observed.value,
                observed.unit,
            )
            assert claim.classification == "synthetic" and claim.origin == "synthetic_fixture"
            assert claim.asserted_at is None and claim.asserted_by is None
        for record, observed in zip(
            result.profile.evidence, source.candidate.evidence, strict=True
        ):
            assert record.excerpt == observed.excerpt
            assert record.relation == observed.relation
            if record.review:
                assert record.review.kind == "synthetic_review"
                assert record.review.method == observed.review_method
        assert result.requirements == ()
        assert all(draft.review is None for draft in result.drafts)
        assert [job.text for job in result.jobs] == [job.text for job in source.jobs]
        for app, observed in zip(result.applications, source.applications, strict=True):
            assert [h.state for h in app.history] == [h.state for h in observed.history]
            assert all(
                h.basis == "synthetic_observation" and not h.external_manual for h in app.history
            )


def test_invalid_world_is_not_repaired_or_approved_by_import() -> None:
    with pytest.raises(ValueError, match="application_transition"):
        map_observable(generate_inputs()[7], context())
    with pytest.raises(TypeError):
        map_observable(object(), context())
    source = generate_inputs()[0]
    raw = json.loads(observable_bytes(source))
    raw["secret_canary"] = "must not become context"
    with pytest.raises(ValueError):
        load_observable(json.dumps(raw).encode(), context())
    for malformed in ("{}", b" " * 2_000_001, 2_000_001):
        with pytest.raises(ValueError, match="Bounded"):
            load_observable(malformed, context())


def test_import_identity_prevents_cross_world_and_owner_collisions() -> None:
    first, second = snapshot(0), snapshot(1)
    assert first.jobs[0].opportunity_id != second.jobs[0].opportunity_id
    changed = map_observable(generate_inputs()[0], context(3))
    assert first.jobs[0].id != changed.jobs[0].id
    assert first.profile.id != changed.profile.id
    # Fix only the public malformed history to test alias identity independently.
    source = generate_inputs()[7]
    valid_alias = replace(source, applications=(source.applications[0],))
    result = map_observable(valid_alias, context())
    assert result.jobs[0].id != result.jobs[1].id
    assert result.jobs[0].opportunity_id == result.jobs[1].opportunity_id
    other_app = result.applications[0].model_copy(
        update={"id": snapshot(1).applications[0].id, "job_id": result.jobs[1].id}
    )
    with pytest.raises(ValidationError, match="Duplicate application"):
        result.model_copy(update={"applications": (*result.applications, other_app)})


def test_seed_boundary_repeatability_and_source_variation() -> None:
    payloads = []
    for seed in (0, 20261004, 2**63 - 1):
        source = generate_inputs(seed)[0]
        first = canonical_bytes(map_observable(source, context()))
        assert first == canonical_bytes(map_observable(source, context()))
        payloads.append(first)
    assert len(set(payloads)) == 3


def test_snapshot_rejects_foreign_missing_stale_and_duplicate_objects() -> None:
    value = snapshot()
    foreign = value.jobs[0].model_copy(update={"workspace_id": context(3).workspace_id})
    missing = value.jobs[0].model_copy(update={"company_id": CompanyId("company_" + "f" * 32)})
    for jobs in ((foreign,), (missing,), (value.jobs[0], value.jobs[0])):
        with pytest.raises(ValidationError):
            value.model_copy(update={"jobs": jobs})
    stale = value.cvs[0].claim_refs[0].model_copy(update={"revision": 2})
    cv = value.cvs[0].model_copy(update={"claim_refs": (stale,)})
    with pytest.raises(ValidationError):
        value.model_copy(update={"cvs": (cv,)})
    forged = value.jobs[0]
    object.__setattr__(forged, "revision", 0)
    with pytest.raises(ValidationError):
        CareerSnapshot.model_validate(value)


def requirement(value: CareerSnapshot) -> Requirement:
    job = value.jobs[0]
    quote = "Python"
    start = job.text.index(quote)
    return Requirement(
        id=RequirementId("requirement_" + "a" * 32),
        workspace_id=value.workspace_id,
        revision=1,
        classification=value.classification,
        job_id=job.id,
        job_revision=job.revision,
        job_digest=job.content_digest,
        assertion=value.profile.claims[0].assertion,
        priority="essential",
        source_start=start,
        source_end=start + len(quote),
        source_quote=quote,
        origin="ai_proposal",
    )


def test_normalization_is_source_bound_and_remains_a_proposal() -> None:
    value = snapshot()
    proposed = requirement(value)
    result = value.model_copy(update={"requirements": (proposed,)})
    assert result.requirements[0].review is None
    assert result.requirements[0].origin == "ai_proposal"
    for changes in (
        {"job_revision": 2},
        {"job_digest": "0" * 64},
        {"source_quote": "Java"},
        {"source_start": proposed.source_start + 1},
    ):
        with pytest.raises(ValidationError):
            value.model_copy(update={"requirements": (proposed.model_copy(update=changes),)})
    with pytest.raises(ValidationError):
        value.model_copy(update={"requirements": (proposed, proposed)})
    review = ContentReview(
        revision=1,
        content_digest=proposed.content_digest,
        reviewer_id=context().actor_id,
        reviewed_at=datetime(2026, 1, 1, tzinfo=UTC),
        method="manual source review",
        decision="accepted",
    )
    with pytest.raises(ValidationError, match="precedes posting"):
        value.model_copy(update={"requirements": (proposed.model_copy(update={"review": review}),)})


def test_unsupported_proposals_are_visible_but_cannot_receive_accepted_unit_review() -> None:
    value = snapshot(1)
    assert value.drafts
    additions = [
        draft
        for draft in value.drafts
        if draft.assertions[0].assertion.subject in {"french", "experience"}
    ]
    assert len(additions) == 2
    for draft in additions:
        for unit in draft.assertions:
            assert not supports_assertion(value.profile, unit.assertion, unit.source_claim_refs)
        review = ContentReview(
            revision=draft.revision,
            content_digest=draft.content_digest,
            reviewer_id=context().actor_id,
            reviewed_at=value.as_of,
            method="manual review",
            decision="accepted",
        )
        with pytest.raises(ValidationError, match="unsupported"):
            value.model_copy(update={"drafts": (draft.model_copy(update={"review": review}),)})


def test_accepted_unit_review_requires_support_available_at_review_time() -> None:
    value = snapshot()
    draft = value.drafts[0]
    assert supports_assertion(
        value.profile, draft.assertions[0].assertion, draft.assertions[0].source_claim_refs
    )
    review = ContentReview(
        revision=draft.revision,
        content_digest=draft.content_digest,
        reviewer_id=context().actor_id,
        reviewed_at=value.as_of,
        method="manual structured review",
        decision="accepted",
    )
    accepted = draft.model_copy(update={"review": review})
    value.model_copy(update={"drafts": (accepted,)})
    early = review.model_copy(update={"reviewed_at": datetime(2025, 1, 1, tzinfo=UTC)})
    with pytest.raises(ValidationError, match="precedes"):
        value.model_copy(update={"drafts": (draft.model_copy(update={"review": early}),)})
    claim = value.profile.claims[0].model_copy(update={"status": "withdrawn", "review": None})
    profile = value.profile.model_copy(update={"claims": (claim, *value.profile.claims[1:])})
    with pytest.raises(ValidationError, match="stale"):
        value.model_copy(update={"profile": profile, "drafts": (accepted,)})


def test_wire_rejects_missing_nested_version_and_unreadable_large_aggregate() -> None:
    value = snapshot()
    data = json.loads(canonical_bytes(value))
    del data["profile"]["schema_version"]
    with pytest.raises(ValueError):
        load_contract(CareerSnapshot, json.dumps(data).encode())
    # A large trusted in-memory collection must not emit an unreadable wire record.
    basis = value.profile.evidence[0]
    records = tuple(
        EvidenceRecord(
            id=EvidenceId(f"evidence_{i:032x}"),
            workspace_id=value.workspace_id,
            profile_id=value.profile.id,
            revision=1,
            classification="synthetic",
            assertion=basis.assertion,
            relation="supports",
            excerpt="x" * 12000,
            source_kind="project_artifact",
            source_reference="synthetic retained artifact",
            collected_at=basis.collected_at,
        )
        for i in range(200)
    )
    profile = value.profile.model_copy(update={"claims": (), "evidence": records})
    with pytest.raises(ValueError, match="wire size"):
        canonical_bytes(profile)


def test_runtime_contracts_and_wire_exclude_evaluator_answers() -> None:
    root = Path(__file__).resolve().parents[2] / "src/actual"
    prohibited = {
        "GroundTruth",
        "FixturePair",
        "RequirementOracle",
        "FutureOutcome",
        "generate_development",
    }
    paths = [
        root / "careerlab_bridge.py",
        *root.glob("core/*.py"),
        *root.glob("career/*.py"),
        *root.glob("profile/*.py"),
    ]
    for path in paths:
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ImportFrom):
                assert "annotations" not in (node.module or "")
                assert not prohibited.intersection(alias.name for alias in node.names)
    forbidden = {
        "coverage",
        "acceptable_cv_ids",
        "blocked_draft_ids",
        "expected_error_codes",
        "future_outcomes",
        "secret_canary",
        "split",
        "membership",
    }

    def inspect(data: object) -> None:
        if isinstance(data, dict):
            assert not forbidden.intersection(data)
            for item in data.values():
                inspect(item)
        elif isinstance(data, list):
            for item in data:
                inspect(item)

    for case in range(7):
        inspect(json.loads(canonical_bytes(snapshot(case))))
