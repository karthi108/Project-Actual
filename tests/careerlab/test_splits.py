"""Public synthetic partition checks; these are not frozen validation/locked datasets."""

from dataclasses import replace

import pytest

from actual.careerlab.contracts import (
    Application,
    Candidate,
    Company,
    CVVariant,
    Evidence,
    HistoryEntry,
    JobPosting,
    ProfileClaim,
    ScenarioInput,
    Split,
    SplitMembership,
)
from actual.careerlab.splits import content_fingerprint, validate_split_isolation


def public_input(
    suffix: str,
    text: str,
    company_name: str = "Beacon Systems",
    candidate_name: str = "Jordan Example",
) -> ScenarioInput:
    company_id, job_id = f"company-{suffix}", f"job-{suffix}"
    candidate_id, claim_id = f"candidate-{suffix}", f"claim-{suffix}"
    evidence_id, application_id = f"evidence-{suffix}", f"application-{suffix}"
    return ScenarioInput(
        id=f"SCN-public-{suffix}",
        schema_version="careerlab-input-v1",
        as_of="2026-10-01T12:00:00Z",
        companies=(
            Company(
                id=company_id,
                name=company_name,
                context=f"{company_name} recruits engineers.",
            ),
        ),
        jobs=(
            JobPosting(
                id=job_id,
                company_id=company_id,
                canonical_opportunity=f"opportunity-{suffix}",
                source_reference=f"https://example.invalid/jobs/{suffix}",
                posted_at="2026-09-01T12:00:00Z",
                title="Backend engineer",
                text=text,
            ),
        ),
        candidate=Candidate(
            id=candidate_id,
            name=candidate_name,
            claims=(
                ProfileClaim(
                    id=claim_id,
                    subject="python",
                    value=2,
                    unit="skill_level",
                    text=f"{candidate_name} has Python experience.",
                    status="reviewed_supported",
                    evidence_ids=(evidence_id,),
                ),
            ),
            evidence=(
                Evidence(
                    id=evidence_id,
                    subject="python",
                    value=2,
                    unit="skill_level",
                    relation="supports",
                    source_kind="project_review",
                    excerpt=f"{candidate_name} implemented Python services for {company_name}.",
                    observed_at="2026-08-01T12:00:00Z",
                    reviewer="Synthetic reviewer",
                    review_method="Synthetic project review",
                    reviewed_at="2026-08-02T12:00:00Z",
                ),
            ),
        ),
        cvs=(
            CVVariant(
                id=f"cv-{suffix}",
                name="Backend CV",
                summary=f"{candidate_name}: Python project at {company_name}.",
                claim_ids=(claim_id,),
            ),
        ),
        draft_assertions=(),
        applications=(
            Application(
                id=application_id,
                job_id=job_id,
                candidate_id=candidate_id,
                state="preparing",
                history=(
                    HistoryEntry(
                        id=f"history-{suffix}",
                        state="preparing",
                        occurred_at="2026-09-02T12:00:00Z",
                        recorded_at="2026-09-02T12:00:00Z",
                    ),
                ),
            ),
        ),
        messages=(),
    )


def public_membership(inputs: ScenarioInput, split: Split) -> SplitMembership:
    suffix = inputs.id
    return SplitMembership(
        id=f"membership-{suffix}",
        scenario_id=inputs.id,
        split=split,
        coverage="explicit_gaps",
        company_lineages=(f"company-lineage-{suffix}",),
        candidate_lineages=(f"candidate-lineage-{suffix}",),
        evidence_lineages=(f"evidence-lineage-{suffix}",),
        cv_lineages=(f"cv-lineage-{suffix}",),
        application_lineages=(f"application-lineage-{suffix}",),
        template_lineages=(f"template-lineage-{suffix}",),
        normalized_content_hash=content_fingerprint(inputs),
    )


def error_codes(
    memberships: tuple[SplitMembership, ...], inputs: tuple[ScenarioInput, ...]
) -> set[str]:
    return {item.code for item in validate_split_isolation(memberships, inputs)}


def distinct_inputs() -> tuple[ScenarioInput, ...]:
    return (
        public_input("one", "Python API design is required."),
        public_input("two", "Azure infrastructure maintenance is required."),
        public_input("three", "French customer conversation is required."),
    )


def test_independent_public_memberships_in_all_three_partitions_pass() -> None:
    inputs = distinct_inputs()
    memberships = tuple(
        public_membership(record, split)
        for record, split in zip(inputs, ("development", "validation", "locked_test"), strict=True)
    )
    assert validate_split_isolation(memberships, inputs) == ()


@pytest.mark.parametrize(
    "lineage_field",
    [
        "company_lineages",
        "candidate_lineages",
        "evidence_lineages",
        "cv_lineages",
        "application_lineages",
        "template_lineages",
    ],
)
def test_each_shared_lineage_kind_is_rejected_across_splits(lineage_field: str) -> None:
    first, second, _ = distinct_inputs()
    one = public_membership(first, "development")
    two = public_membership(second, "validation")
    shared = ("shared-ancestry",)
    one = replace(one, **{lineage_field: shared})
    two = replace(two, **{lineage_field: shared})
    assert "shared_lineage" in error_codes((one, two), (first, second))


def test_transitive_lineage_chain_is_rejected_across_splits() -> None:
    inputs = distinct_inputs()
    one = replace(public_membership(inputs[0], "development"), company_lineages=("shared-company",))
    two = replace(
        public_membership(inputs[1], "development"),
        company_lineages=("shared-company",),
        template_lineages=("shared-template",),
    )
    three = replace(
        public_membership(inputs[2], "locked_test"), template_lineages=("shared-template",)
    )
    assert set(one.company_lineages).isdisjoint(three.company_lineages)
    assert set(one.template_lineages).isdisjoint(three.template_lineages)
    violations = validate_split_isolation((one, two, three), inputs)
    # The first record is connected to the locked-labelled test record only through the bridge.
    assert any(
        item.code == "shared_lineage" and item.path == one.scenario_id for item in violations
    )


def test_shared_template_within_one_partition_is_allowed() -> None:
    first, second, _ = distinct_inputs()
    memberships = (
        replace(public_membership(first, "development"), template_lineages=("same-template",)),
        replace(public_membership(second, "development"), template_lineages=("same-template",)),
    )
    assert validate_split_isolation(memberships, (first, second)) == ()


def test_identical_source_with_renamed_lineages_is_rejected() -> None:
    first = public_input("original", "Python API design is required.")
    second = public_input("renamed", "Python API design is required.")
    assert content_fingerprint(first) == content_fingerprint(second)
    memberships = (
        public_membership(first, "development"),
        public_membership(second, "validation"),
    )
    assert "duplicate_source" in error_codes(memberships, (first, second))


def test_shared_individual_job_is_rejected_even_when_whole_scenario_hash_differs() -> None:
    first = public_input("multiple", "Python API design is required.")
    additional = replace(
        first.jobs[0],
        id="job-additional",
        canonical_opportunity="opportunity-additional",
        text="Azure infrastructure maintenance is required.",
    )
    first = replace(first, jobs=(first.jobs[0], additional))
    second = public_input("single", "Python API design is required.")
    assert content_fingerprint(first) != content_fingerprint(second)
    memberships = (
        public_membership(first, "development"),
        public_membership(second, "validation"),
    )
    assert "duplicate_source" in error_codes(memberships, (first, second))


def test_content_fingerprint_is_independent_of_job_order() -> None:
    first = public_input("ordered", "Python API design is required.")
    additional = replace(
        first.jobs[0],
        id="job-second",
        canonical_opportunity="opportunity-second",
        text="Azure infrastructure maintenance is required.",
    )
    forward = replace(first, jobs=(first.jobs[0], additional))
    backward = replace(first, jobs=(additional, first.jobs[0]))
    assert content_fingerprint(forward) == content_fingerprint(backward)


def test_normalized_name_number_url_case_and_whitespace_do_not_create_new_source() -> None:
    first = public_input(
        "original",
        "Beacon Systems asks Jordan Example for Python work on 12 services. "
        "See https://one.invalid/jobs/41.",
    )
    second = public_input(
        "masked",
        "  CEDAR LABS asks  MORGAN SAMPLE for PYTHON work on 99 services.\n"
        "See https://two.invalid/vacancy/812.  ",
        company_name="Cedar Labs",
        candidate_name="Morgan Sample",
    )
    assert content_fingerprint(first) == content_fingerprint(second)
    memberships = (
        public_membership(first, "development"),
        public_membership(second, "locked_test"),
    )
    assert "duplicate_source" in error_codes(memberships, (first, second))


def test_semantic_source_change_remains_distinct() -> None:
    first = public_input("python", "Python API design is required.")
    second = public_input("azure", "Azure infrastructure maintenance is required.")
    assert content_fingerprint(first) != content_fingerprint(second)


def test_declared_content_hash_must_match_computed_fingerprint() -> None:
    inputs = distinct_inputs()[0]
    membership = replace(public_membership(inputs, "development"), normalized_content_hash="0" * 64)
    assert "fingerprint_mismatch" in error_codes((membership,), (inputs,))


def test_missing_membership_is_rejected() -> None:
    inputs = distinct_inputs()[0]
    assert "split_membership" in error_codes((), (inputs,))


def test_duplicate_membership_is_rejected() -> None:
    inputs = distinct_inputs()[0]
    one = public_membership(inputs, "development")
    two = replace(one, id="duplicate-membership", split="validation")
    assert "split_membership" in error_codes((one, two), (inputs,))


def test_membership_for_unknown_scenario_is_rejected() -> None:
    inputs = distinct_inputs()[0]
    membership = replace(public_membership(inputs, "development"), scenario_id="unknown-scenario")
    assert "split_membership" in error_codes((membership,), (inputs,))
