"""Adversarial public-fixture integrity tests, independent of authored labels.

These tests perturb observable facts and evaluator annotations separately. They
never load a locked-test case or use a future recruiter narrative as fit evidence.
"""

from dataclasses import replace

import pytest

from actual.careerlab.contracts import FixturePair, ScenarioInput
from actual.careerlab.generator import generate_development
from actual.careerlab.validation import validate_input, validate_oracle, validate_pair


@pytest.fixture(scope="module")
def public_cases() -> tuple[FixturePair, ...]:
    return generate_development()


@pytest.fixture
def base(public_cases: tuple[FixturePair, ...]) -> FixturePair:
    return public_cases[0]


def input_codes(value: ScenarioInput) -> set[str]:
    return {violation.code for violation in validate_input(value)}


def oracle_codes(pair: FixturePair) -> set[str]:
    return {violation.code for violation in validate_oracle(pair.inputs, pair.oracle)}


def replace_claim(value: ScenarioInput, subject: str, /, **changes: object) -> ScenarioInput:
    claims = tuple(
        replace(claim, **changes) if claim.subject == subject else claim
        for claim in value.candidate.claims
    )
    return replace(value, candidate=replace(value.candidate, claims=claims))


def replace_evidence(value: ScenarioInput, subject: str, /, **changes: object) -> ScenarioInput:
    evidence = tuple(
        replace(item, **changes) if item.subject == subject else item
        for item in value.candidate.evidence
    )
    return replace(value, candidate=replace(value.candidate, evidence=evidence))


def replace_requirement(pair: FixturePair, subject: str, **changes: object) -> FixturePair:
    requirements = tuple(
        replace(item, **changes) if item.subject == subject else item
        for item in pair.oracle.requirements
    )
    return replace(pair, oracle=replace(pair.oracle, requirements=requirements))


def test_all_eight_public_pairs_match_their_annotations(
    public_cases: tuple[FixturePair, ...],
) -> None:
    assert len(public_cases) == 8
    for pair in public_cases:
        assert validate_pair(pair) == (), pair.inputs.id
    assert all(validate_input(pair.inputs) == () for pair in public_cases[:7])
    assert input_codes(public_cases[7].inputs) == {"application_transition"}


@pytest.mark.parametrize("foreign_ref", ["missing", "CAREER-DEV-002:evidence:python"])
def test_claim_evidence_cannot_resolve_outside_its_case(
    base: FixturePair, foreign_ref: str
) -> None:
    bad = replace_claim(base.inputs, "python", evidence_ids=(foreign_ref,))
    assert "reference" in input_codes(bad)
    assert "reviewed_support" in input_codes(bad)


def test_repeated_evidence_reference_is_rejected(base: FixturePair) -> None:
    claim = base.inputs.candidate.claims[0]
    bad = replace_claim(base.inputs, "python", evidence_ids=claim.evidence_ids * 2)
    assert "reference" in input_codes(bad)


def test_duplicate_record_identity_is_rejected(base: FixturePair) -> None:
    original, alternative = base.inputs.cvs
    bad = replace(base.inputs, cvs=(original, replace(alternative, id=original.id)))
    assert input_codes(bad) == {"duplicate_id"}


@pytest.mark.parametrize("identifier", ["", "unsafe/path", "x" * 121])
def test_ids_are_bounded_neutral_identifiers(base: FixturePair, identifier: str) -> None:
    assert "identifier" in input_codes(replace(base.inputs, id=identifier))


def test_nested_record_must_remain_explicitly_synthetic(base: FixturePair) -> None:
    company = replace(base.inputs.companies[0], synthetic=False)
    assert input_codes(replace(base.inputs, companies=(company,))) == {"schema"}


@pytest.mark.parametrize("wrong_value", [True, "2", 2.0])
def test_assertion_value_is_not_coerced(base: FixturePair, wrong_value: object) -> None:
    assert input_codes(replace_claim(base.inputs, "python", value=wrong_value)) == {"schema"}


@pytest.mark.parametrize(
    ("subject", "changes"),
    [
        ("python", {"unit": "months"}),
        ("french", {"unit": "skill_level"}),
        ("experience", {"unit": "cefr_level"}),
        ("python", {"value": 4}),
        ("french", {"value": 7}),
        ("experience", {"value": 601}),
        ("python", {"value": -1}),
    ],
)
def test_assertions_have_bounded_subject_specific_units(
    base: FixturePair, subject: str, changes: dict[str, object]
) -> None:
    assert "claim_scope" in input_codes(replace_claim(base.inputs, subject, **changes))


def test_matching_evidence_id_does_not_prove_the_wrong_subject(base: FixturePair) -> None:
    fastapi_evidence = next(
        item.id for item in base.inputs.candidate.evidence if item.subject == "fastapi"
    )
    bad = replace_claim(base.inputs, "python", evidence_ids=(fastapi_evidence,))
    assert {"evidence_scope", "reviewed_support"} <= input_codes(bad)


def test_reviewed_excerpt_cannot_support_a_stronger_assertion(base: FixturePair) -> None:
    bad = replace_evidence(base.inputs, "python", value=1)
    assert "reviewed_support" in input_codes(bad)


@pytest.mark.parametrize("missing", ["reviewer", "review_method", "reviewed_at"])
def test_review_requires_complete_provenance(base: FixturePair, missing: str) -> None:
    bad = replace_evidence(base.inputs, "python", **{missing: None})
    assert {"review_provenance", "reviewed_support"} <= input_codes(bad)


def test_forged_review_metadata_cannot_upgrade_self_report(base: FixturePair) -> None:
    bad = replace_claim(base.inputs, "french", status="reviewed_supported")
    bad = replace_evidence(
        bad,
        "french",
        reviewer="synthetic-reviewer-99",
        review_method="claimed independent review",
        reviewed_at="2026-01-12T12:00:00Z",
    )
    assert "reviewed_support" in input_codes(bad)


def test_review_must_follow_observation(base: FixturePair) -> None:
    bad = replace_evidence(base.inputs, "python", reviewed_at="2026-01-09T12:00:00Z")
    assert "review_chronology" in input_codes(bad)


def test_contradicted_status_needs_an_actual_reviewed_contradiction(base: FixturePair) -> None:
    bad = replace_claim(base.inputs, "python", status="contradicted")
    assert "contradiction_basis" in input_codes(bad)


def test_reviewed_conflicting_evidence_cannot_be_silently_selected_away(
    public_cases: tuple[FixturePair, ...],
) -> None:
    bad = replace_claim(public_cases[3].inputs, "llm_integration", status="reviewed_supported")
    assert "reviewed_support" in input_codes(bad)


@pytest.mark.parametrize("status", ["self_reported", "candidate_support", "withdrawn"])
def test_noncurrent_or_unreviewed_claim_is_not_requirement_support(
    base: FixturePair, status: str
) -> None:
    inputs = replace_claim(base.inputs, "python", status=status)
    assert validate_input(inputs) == ()
    assert "oracle_assessment" in oracle_codes(replace(base, inputs=inputs))


@pytest.mark.parametrize(
    "timestamp",
    ["2026-10-01T12:00:00", "2026-10-01T12:00:00+02:00", "2026-02-30T12:00:00Z"],
)
def test_observable_instants_must_be_real_aware_utc(base: FixturePair, timestamp: str) -> None:
    assert input_codes(replace(base.inputs, as_of=timestamp)) == {"timestamp"}


def test_future_source_fact_is_not_observable(base: FixturePair) -> None:
    bad = replace_evidence(base.inputs, "python", reviewed_at="2026-10-02T12:00:00Z")
    assert "future_observation" in input_codes(bad)


def test_real_looking_job_url_is_not_a_synthetic_source(base: FixturePair) -> None:
    job = replace(base.inputs.jobs[0], source_reference="https://example.com/real-job")
    assert "synthetic_source" in input_codes(replace(base.inputs, jobs=(job,)))


def test_application_current_state_must_match_last_event(base: FixturePair) -> None:
    app = replace(base.inputs.applications[0], state="applied")
    assert "application_state" in input_codes(replace(base.inputs, applications=(app,)))


def test_application_history_cannot_begin_as_applied(base: FixturePair) -> None:
    app = base.inputs.applications[0]
    history = (replace(app.history[0], state="applied"),)
    bad = replace(app, state="applied", history=history)
    assert "application_start" in input_codes(replace(base.inputs, applications=(bad,)))


def test_preparing_cannot_transition_directly_to_interview(base: FixturePair) -> None:
    app = base.inputs.applications[0]
    skipped = replace(
        app.history[0],
        id=f"{base.inputs.id}:history:skipped",
        state="interview",
        occurred_at="2026-09-20T12:00:00Z",
        recorded_at="2026-09-20T13:00:00Z",
    )
    bad = replace(app, state="interview", history=app.history + (skipped,))
    assert "application_transition" in input_codes(replace(base.inputs, applications=(bad,)))


def test_application_occurrences_must_be_strictly_ordered(
    public_cases: tuple[FixturePair, ...],
) -> None:
    inputs = public_cases[2].inputs
    app = inputs.applications[0]
    repeated = replace(app.history[1], occurred_at=app.history[0].occurred_at)
    bad = replace(app, history=(app.history[0], repeated) + app.history[2:])
    assert "application_chronology" in input_codes(replace(inputs, applications=(bad,)))


def test_recording_cannot_precede_occurrence(base: FixturePair) -> None:
    app = base.inputs.applications[0]
    entry = replace(app.history[0], recorded_at="2026-09-01T12:00:00Z")
    bad = replace(app, history=(entry,))
    assert "recording_chronology" in input_codes(replace(base.inputs, applications=(bad,)))


def test_delayed_recording_preserves_causal_occurrence_order(
    public_cases: tuple[FixturePair, ...],
) -> None:
    inputs = public_cases[2].inputs
    app = inputs.applications[0]
    history = tuple(replace(item, recorded_at="2026-09-30T12:00:00Z") for item in app.history)
    assert validate_input(replace(inputs, applications=(replace(app, history=history),))) == ()


def test_application_cannot_precede_posted_job(base: FixturePair) -> None:
    app = base.inputs.applications[0]
    entry = replace(
        app.history[0],
        occurred_at="2026-08-31T12:00:00Z",
        recorded_at="2026-08-31T13:00:00Z",
    )
    bad = replace(app, history=(entry,))
    assert "application_before_job" in input_codes(replace(base.inputs, applications=(bad,)))


def test_recruiter_message_needs_prior_applied_history(
    public_cases: tuple[FixturePair, ...],
) -> None:
    inputs = public_cases[2].inputs
    app = inputs.applications[0]
    premature = replace(inputs.messages[0], sent_at=app.history[2].occurred_at)
    assert "message_chronology" in input_codes(
        replace(inputs, messages=(premature,) + inputs.messages[1:])
    )


def test_recruiter_message_must_match_application_job(
    public_cases: tuple[FixturePair, ...],
) -> None:
    inputs = public_cases[2].inputs
    other_job = replace(inputs.jobs[0], id=f"{inputs.id}:job:unrelated")
    wrong_job = replace(inputs.messages[0], job_id=other_job.id)
    bad = replace(inputs, jobs=inputs.jobs + (other_job,), messages=(wrong_job,))
    assert "message_chronology" in input_codes(bad)


def test_offer_message_cannot_appear_without_offer_state(
    public_cases: tuple[FixturePair, ...],
) -> None:
    inputs = public_cases[2].inputs
    forged = replace(inputs.messages[0], kind="offer")
    assert "message_state" in input_codes(replace(inputs, messages=(forged,)))


def test_oracle_is_bound_to_its_observable_scenario(base: FixturePair) -> None:
    oracle = replace(base.oracle, scenario_id="CAREER-DEV-002")
    assert "oracle_identity" in oracle_codes(replace(base, oracle=oracle))


def test_requirement_quote_must_exist_in_the_linked_posting(base: FixturePair) -> None:
    bad = replace_requirement(base, "python", source_quote="Invented mandatory Rust requirement.")
    assert "requirement_source" in oracle_codes(bad)


def test_requirement_cannot_use_a_different_subjects_claim(base: FixturePair) -> None:
    fastapi_claim = next(
        item.id for item in base.inputs.candidate.claims if item.subject == "fastapi"
    )
    bad = replace_requirement(base, "python", claim_ids=(fastapi_claim,))
    assert "oracle_scope" in oracle_codes(bad)


def test_oracle_reference_cannot_point_to_another_case(base: FixturePair) -> None:
    bad = replace_requirement(base, "python", claim_ids=("CAREER-DEV-002:claim:python",))
    assert "oracle_reference" in oracle_codes(bad)


@pytest.mark.parametrize("assessment", ["supported", "gap", "partial", "conflict"])
def test_unreviewed_language_is_unknown_even_when_employer_requires_more(
    base: FixturePair, assessment: str
) -> None:
    assert "oracle_assessment" in oracle_codes(
        replace_requirement(base, "french", assessment=assessment)
    )


def test_conflict_cannot_be_relabelled_unknown(public_cases: tuple[FixturePair, ...]) -> None:
    bad = replace_requirement(public_cases[3], "llm_integration", assessment="unknown")
    assert "oracle_assessment" in oracle_codes(bad)


def test_declared_shortfall_is_preserved_without_claiming_verification(base: FixturePair) -> None:
    bad = replace_requirement(base, "french", declared_shortfall=False)
    assert "declared_shortfall" in oracle_codes(bad)


def test_reviewed_sufficient_support_cannot_be_relabelled_unknown(base: FixturePair) -> None:
    bad = replace_requirement(base, "python", assessment="unknown")
    assert "oracle_assessment" in oracle_codes(bad)


def test_numeric_skill_shortfall_requires_partial_not_gap(base: FixturePair) -> None:
    inputs = replace_claim(base.inputs, "python", value=1)
    inputs = replace_evidence(inputs, "python", value=1)
    pair = replace(base, inputs=inputs)
    partial = replace_requirement(pair, "python", assessment="partial")
    # CV annotations may need updating as coverage changes; only the requirement
    # classification is under test here.
    assert "oracle_assessment" not in oracle_codes(partial)
    gap = replace_requirement(pair, "python", assessment="gap")
    assert "oracle_assessment" in oracle_codes(gap)


def test_language_threshold_shortfall_cannot_use_skill_partial(base: FixturePair) -> None:
    inputs = replace_claim(base.inputs, "french", status="reviewed_supported")
    inputs = replace_evidence(
        inputs,
        "french",
        source_kind="document_review",
        reviewer="synthetic-language-reviewer",
        review_method="fixture language-level scope review",
        reviewed_at="2026-01-12T12:00:00Z",
    )
    pair = replace(base, inputs=inputs)
    bad = replace_requirement(pair, "french", assessment="partial", declared_shortfall=False)
    assert "oracle_assessment" in oracle_codes(bad)


def test_unsafe_addition_cannot_be_deleted_from_blocklist(
    public_cases: tuple[FixturePair, ...],
) -> None:
    pair = public_cases[1]
    oracle = replace(pair.oracle, blocked_draft_ids=pair.oracle.blocked_draft_ids[1:])
    assert "draft_oracle" in oracle_codes(replace(pair, oracle=oracle))


def test_safe_addition_cannot_be_arbitrarily_blocked(base: FixturePair) -> None:
    oracle = replace(base.oracle, blocked_draft_ids=(base.inputs.draft_assertions[0].id,))
    assert "draft_oracle" in oracle_codes(replace(base, oracle=oracle))


def test_all_equally_suitable_cv_alternatives_must_be_retained(
    public_cases: tuple[FixturePair, ...],
) -> None:
    pair = public_cases[2]
    assert len(pair.oracle.acceptable_cv_ids) == 2
    oracle = replace(pair.oracle, acceptable_cv_ids=pair.oracle.acceptable_cv_ids[:1])
    assert "cv_oracle" in oracle_codes(replace(pair, oracle=oracle))


def test_cv_using_withdrawn_claims_cannot_be_an_acceptable_alternative(
    public_cases: tuple[FixturePair, ...],
) -> None:
    pair = public_cases[4]
    oracle = replace(
        pair.oracle, acceptable_cv_ids=pair.oracle.acceptable_cv_ids + (pair.inputs.cvs[1].id,)
    )
    assert "cv_oracle" in oracle_codes(replace(pair, oracle=oracle))


def test_cv_alternative_ids_cannot_be_repeated(base: FixturePair) -> None:
    oracle = replace(base.oracle, acceptable_cv_ids=base.oracle.acceptable_cv_ids * 2)
    assert "cv_oracle" in oracle_codes(replace(base, oracle=oracle))


def test_duplicate_opportunity_group_cannot_be_omitted(
    public_cases: tuple[FixturePair, ...],
) -> None:
    pair = public_cases[7]
    oracle = replace(pair.oracle, duplicate_job_groups=())
    assert "duplicate_oracle" in oracle_codes(replace(pair, oracle=oracle))


def test_duplicate_opportunity_groups_cannot_be_repeated(
    public_cases: tuple[FixturePair, ...],
) -> None:
    pair = public_cases[7]
    oracle = replace(pair.oracle, duplicate_job_groups=pair.oracle.duplicate_job_groups * 2)
    assert "duplicate_oracle" in oracle_codes(replace(pair, oracle=oracle))


@pytest.mark.parametrize(
    "occurs_at",
    [
        "2026-10-01T12:00:00Z",
        "2026-09-30T12:00:00Z",
        "2026-10-05T12:00:00",
        "2026-10-05T12:00:00+02:00",
    ],
)
def test_future_narrative_is_utc_and_strictly_after_snapshot(
    public_cases: tuple[FixturePair, ...], occurs_at: str
) -> None:
    pair = public_cases[5]
    outcome = replace(pair.oracle.future_outcomes[0], occurs_at=occurs_at)
    oracle = replace(pair.oracle, future_outcomes=(outcome,))
    assert "future_outcome" in oracle_codes(replace(pair, oracle=oracle))


def test_future_narrative_cannot_refer_to_another_case(
    public_cases: tuple[FixturePair, ...],
) -> None:
    pair = public_cases[5]
    outcome = replace(
        pair.oracle.future_outcomes[0], application_id="CAREER-DEV-001:application:01"
    )
    oracle = replace(pair.oracle, future_outcomes=(outcome,))
    assert "future_outcome" in oracle_codes(replace(pair, oracle=oracle))


def test_injected_canary_answer_is_detected_in_observable_context(
    public_cases: tuple[FixturePair, ...],
) -> None:
    pair = public_cases[6]
    assert pair.oracle.secret_canary is not None
    company = replace(
        pair.inputs.companies[0],
        context=f"Synthetic leaked evaluator canary: {pair.oracle.secret_canary}",
    )
    inputs = replace(pair.inputs, companies=(company,))
    assert validate_input(inputs) == ()
    assert "ground_truth_leak" in oracle_codes(replace(pair, inputs=inputs))


def test_expected_invalid_annotation_never_turns_bad_input_into_valid_input(
    public_cases: tuple[FixturePair, ...],
) -> None:
    pair = public_cases[7]
    assert validate_pair(pair) == ()
    assert input_codes(pair.inputs) == {"application_transition"}
    oracle = replace(pair.oracle, expected_error_codes=())
    assert "expected_invalidity" in {
        violation.code for violation in validate_pair(replace(pair, oracle=oracle))
    }


def test_invented_invalidity_annotation_cannot_reject_a_valid_case(base: FixturePair) -> None:
    oracle = replace(base.oracle, expected_error_codes=("application_transition",))
    assert validate_input(base.inputs) == ()
    assert "expected_invalidity" in {
        violation.code for violation in validate_pair(replace(base, oracle=oracle))
    }


def test_extra_failure_in_an_expected_invalid_case_is_not_hidden(
    public_cases: tuple[FixturePair, ...],
) -> None:
    pair = public_cases[7]
    bad = replace_claim(pair.inputs, "python", evidence_ids=("unresolved",))
    assert {"reference", "reviewed_support", "application_transition"} <= input_codes(bad)
    assert "expected_invalidity" in {
        violation.code for violation in validate_pair(replace(pair, inputs=bad))
    }


def test_repeated_requirement_cannot_gain_authority_from_a_new_record_id(
    base: FixturePair,
) -> None:
    duplicate = replace(base.oracle.requirements[0], id=f"{base.inputs.id}:requirement:repeat")
    oracle = replace(base.oracle, requirements=base.oracle.requirements + (duplicate,))
    assert "oracle_coverage" in oracle_codes(replace(base, oracle=oracle))


def test_distinct_opportunity_cannot_be_left_without_requirement_annotations(
    base: FixturePair,
) -> None:
    distinct = replace(
        base.inputs.jobs[0],
        id=f"{base.inputs.id}:job:second-opportunity",
        canonical_opportunity="synthetic-distinct-opportunity-02",
        source_reference="https://jobs.example.invalid/opportunities/02",
    )
    inputs = replace(base.inputs, jobs=base.inputs.jobs + (distinct,))
    assert validate_input(inputs) == ()
    assert "oracle_coverage" in oracle_codes(replace(base, inputs=inputs))


def test_alias_posting_needs_one_primary_requirement_set(base: FixturePair) -> None:
    primary = base.inputs.jobs[0]
    alias = replace(
        primary,
        id=f"{base.inputs.id}:job:alias",
        source_reference="https://jobs.example.invalid/opportunities/01?board=secondary",
    )
    inputs = replace(base.inputs, jobs=base.inputs.jobs + (alias,))
    oracle = replace(base.oracle, duplicate_job_groups=((primary.id, alias.id),))
    assert validate_input(inputs) == ()
    assert validate_oracle(inputs, oracle) == ()


def test_alias_job_does_not_allow_duplicate_requirement_units(base: FixturePair) -> None:
    primary = base.inputs.jobs[0]
    alias = replace(
        primary,
        id=f"{base.inputs.id}:job:alias",
        source_reference="https://jobs.example.invalid/opportunities/01?board=secondary",
    )
    repeated = replace(
        base.oracle.requirements[0],
        id=f"{base.inputs.id}:requirement:alias-python",
        job_id=alias.id,
    )
    inputs = replace(base.inputs, jobs=base.inputs.jobs + (alias,))
    oracle = replace(
        base.oracle,
        requirements=base.oracle.requirements + (repeated,),
        duplicate_job_groups=((primary.id, alias.id),),
    )
    assert "oracle_coverage" in oracle_codes(replace(base, inputs=inputs, oracle=oracle))


def test_future_interview_cannot_reopen_a_closed_application(
    public_cases: tuple[FixturePair, ...],
) -> None:
    closed_pair = public_cases[2]
    assert closed_pair.inputs.applications[0].state == "closed"
    interview = replace(
        public_cases[5].oracle.future_outcomes[0],
        id=f"{closed_pair.inputs.id}:future:impossible-interview",
        application_id=closed_pair.inputs.applications[0].id,
    )
    oracle = replace(closed_pair.oracle, future_outcomes=(interview,))
    assert "future_outcome" in oracle_codes(replace(closed_pair, oracle=oracle))


@pytest.mark.parametrize("status", ["self_reported", "candidate_support"])
def test_reviewed_contradiction_cannot_be_masked_by_a_weaker_status(
    public_cases: tuple[FixturePair, ...], status: str
) -> None:
    pair = public_cases[3]
    inputs = replace_claim(pair.inputs, "llm_integration", status=status)
    assert "contradiction_status" in input_codes(inputs)
    forged = replace_requirement(
        replace(pair, inputs=inputs), "llm_integration", assessment="unknown"
    )
    assert "oracle_assessment" in oracle_codes(forged)


@pytest.mark.parametrize(
    "source_reference",
    [
        "https://real.example/jobs/.invalid/01",
        "https://user:synthetic-password@jobs.example.invalid/opportunities/01",
        "https://user@jobs.example.invalid/opportunities/01",
        "https:///jobs.example.invalid/opportunities/01",
        "https://jobs.example.invalid:bad/opportunities/01",
        "https://jobs example.invalid/opportunities/01",
    ],
)
def test_reserved_source_is_a_hostname_property_and_never_carries_credentials(
    base: FixturePair, source_reference: str
) -> None:
    job = replace(base.inputs.jobs[0], source_reference=source_reference)
    assert "synthetic_source" in input_codes(replace(base.inputs, jobs=(job,)))


@pytest.mark.parametrize(
    "as_of",
    ["not-a-timestamp", "2026-13-01T12:00:00Z", "2026-10-01T12:00:00"],
)
def test_malformed_snapshot_returns_violations_at_both_validation_boundaries(
    base: FixturePair, as_of: str
) -> None:
    malformed = replace(base.inputs, as_of=as_of)
    assert "timestamp" in input_codes(malformed)
    violations = validate_pair(replace(base, inputs=malformed))
    assert "timestamp" in {item.code for item in violations}


@pytest.mark.parametrize("changed_field", ["company_id", "title", "text"])
def test_duplicate_identity_cannot_conceal_conflicting_opportunity_content(
    public_cases: tuple[FixturePair, ...], changed_field: str
) -> None:
    pair = public_cases[7]
    inputs = pair.inputs
    primary, alias = inputs.jobs
    if changed_field == "company_id":
        different_company = replace(inputs.companies[0], id=f"{inputs.id}:company:different")
        inputs = replace(inputs, companies=inputs.companies + (different_company,))
        alias = replace(alias, company_id=different_company.id)
    elif changed_field == "title":
        alias = replace(alias, title="Synthetic separate lead backend engineer role")
    else:
        alias = replace(alias, text=f"{alias.text} Strong Azure is now mandatory.")
    conflicting = replace(inputs, jobs=(primary, alias))
    assert {"duplicate_content", "application_transition"} <= input_codes(conflicting)
    assert "expected_invalidity" in {
        item.code for item in validate_pair(replace(pair, inputs=conflicting))
    }
