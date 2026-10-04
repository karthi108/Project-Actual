"""Fixture integrity and authored-label consistency, not a career assessment service."""

import re
from dataclasses import dataclass, fields
from datetime import UTC, datetime
from urllib.parse import urlsplit

from .codec import SchemaError, observable_bytes, record_data
from .contracts import (
    DraftAssertion,
    Evidence,
    FixturePair,
    GroundTruth,
    ProfileClaim,
    Record,
    RequirementOracle,
    ScenarioInput,
    State,
)


@dataclass(frozen=True)
class Violation:
    code: str
    path: str
    detail: str


# Synthetic fixture transition policy only. Phase 2 must review its production policy.
TRANSITIONS: dict[State, set[State]] = {
    "preparing": {"ready_for_review", "closed"},
    "ready_for_review": {"preparing", "reviewed", "closed"},
    "reviewed": {"preparing", "applied", "closed"},
    "applied": {"interview", "closed"},
    "interview": {"offer", "closed"},
    "offer": {"closed"},
    "closed": set(),
}


def records(value: Record) -> tuple[Record, ...]:
    result = [value]
    for field in fields(value):
        child = getattr(value, field.name)
        if isinstance(child, Record):
            result.extend(records(child))
        elif isinstance(child, tuple):
            for item in child:
                if isinstance(item, Record):
                    result.extend(records(item))
    return tuple(result)


def instant(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() != UTC.utcoffset(parsed):
        raise ValueError("Timestamp must be aware UTC")
    return parsed


def is_reviewed(evidence: Evidence) -> bool:
    return (
        evidence.source_kind != "self_report"
        and bool(evidence.reviewer)
        and bool(evidence.review_method)
        and bool(evidence.reviewed_at)
    )


def claim_supported(claim: ProfileClaim, evidence: dict[str, Evidence]) -> bool:
    relevant = [evidence[ref] for ref in claim.evidence_ids if ref in evidence]
    if claim.status != "reviewed_supported":
        return False
    if any(item.relation == "contradicts" and is_reviewed(item) for item in relevant):
        return False
    return any(
        item.subject == claim.subject
        and item.unit == claim.unit
        and item.value >= claim.value
        and item.relation == "supports"
        and is_reviewed(item)
        for item in relevant
    )


def _shape(value: Record) -> list[Violation]:
    try:
        record_data(value)
    except SchemaError as error:
        return [Violation("schema", value.id, str(error))]
    result: list[Violation] = []
    seen: set[str] = set()
    for item in records(value):
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,119}", item.id):
            result.append(Violation("identifier", item.id, "Nonempty bounded neutral ID required"))
        if item.id in seen:
            result.append(Violation("duplicate_id", item.id, "Record IDs must be unique"))
        seen.add(item.id)
        for field in fields(item):
            text = getattr(item, field.name)
            if isinstance(text, str) and (not text.strip() or len(text) > 12000):
                result.append(Violation("text_bounds", item.id, field.name))
        if isinstance(item, (Evidence, ProfileClaim, DraftAssertion, RequirementOracle)):
            subject = item.subject
            unit = item.unit
            number = item.minimum if isinstance(item, RequirementOracle) else item.value
            expected = (
                "months"
                if subject == "experience"
                else ("cefr_level" if subject == "french" else "skill_level")
            )
            limit = 600 if unit == "months" else (6 if unit == "cefr_level" else 3)
            if unit != expected or number is None or not 0 <= number <= limit:
                result.append(Violation("claim_scope", item.id, "Subject/unit/value mismatch"))
    return result


def validate_input(value: ScenarioInput) -> tuple[Violation, ...]:
    errors = _shape(value)
    if errors:
        return tuple(errors)
    times: dict[str, datetime] = {}
    for item in records(value):
        for field in fields(item):
            text = getattr(item, field.name)
            if (field.name.endswith("_at") or field.name == "as_of") and text is not None:
                try:
                    times[f"{item.id}.{field.name}"] = instant(text)
                except ValueError:
                    errors.append(Violation("timestamp", item.id, field.name))
    if errors:
        return tuple(errors)
    as_of = times[f"{value.id}.as_of"]
    for key, time in times.items():
        if time > as_of:
            errors.append(Violation("future_observation", key, "Not observable as of this case"))
    company_ids = {item.id for item in value.companies}
    jobs = {item.id: item for item in value.jobs}
    claims = {item.id: item for item in value.candidate.claims}
    evidence = {item.id: item for item in value.candidate.evidence}

    def refs(refs: tuple[str, ...], allowed: set[str], path: str) -> None:
        if len(set(refs)) != len(refs) or not set(refs) <= allowed:
            errors.append(Violation("reference", path, "Missing, repeated or cross-case reference"))

    if not value.companies or not jobs or not value.cvs:
        errors.append(Violation("required_records", value.id, "Company, job and CV required"))
    for job in value.jobs:
        refs((job.company_id,), company_ids, job.id)
        try:
            source = urlsplit(job.source_reference)
            port = source.port  # Parse only; no network request.
            valid_source = (
                source.scheme == "https"
                and source.hostname is not None
                and source.hostname.endswith(".invalid")
                and source.username is None
                and source.password is None
                and (port is None or port > 0)
                and not any(char.isspace() for char in job.source_reference)
            )
        except ValueError:
            valid_source = False
        if not valid_source:
            errors.append(
                Violation("synthetic_source", job.id, "Reserved .invalid source required")
            )
    # A tracking URL or opaque ID may alias the same posting. A changed source
    # body/title/company is a conflicting revision, not an interchangeable alias.
    opportunity_content: dict[str, tuple[str, str, str]] = {}
    for job in value.jobs:
        content = (job.company_id, job.title, job.text)
        previous_content = opportunity_content.setdefault(job.canonical_opportunity, content)
        if content != previous_content:
            errors.append(
                Violation(
                    "duplicate_content", job.id, "Opportunity aliases have conflicting content"
                )
            )
    for item in value.candidate.evidence:
        review = (item.reviewer, item.review_method, item.reviewed_at)
        if any(part is not None for part in review) and not all(review):
            errors.append(Violation("review_provenance", item.id, "Incomplete review"))
        if item.reviewed_at is not None and instant(item.reviewed_at) < instant(item.observed_at):
            errors.append(Violation("review_chronology", item.id, "Review precedes observation"))
    for claim in claims.values():
        refs(claim.evidence_ids, set(evidence), claim.id)
        relevant = [evidence[ref] for ref in claim.evidence_ids if ref in evidence]
        if any(item.subject != claim.subject or item.unit != claim.unit for item in relevant):
            errors.append(Violation("evidence_scope", claim.id, "Evidence has wrong subject/unit"))
        if claim.status == "reviewed_supported" and not claim_supported(claim, evidence):
            errors.append(
                Violation("reviewed_support", claim.id, "Review does not cover assertion")
            )
        if claim.status == "contradicted" and not any(
            item.relation == "contradicts" and is_reviewed(item) for item in relevant
        ):
            errors.append(
                Violation("contradiction_basis", claim.id, "Missing reviewed contradiction")
            )
        if claim.status not in ("contradicted", "withdrawn") and any(
            item.relation == "contradicts" and is_reviewed(item) for item in relevant
        ):
            errors.append(
                Violation("contradiction_status", claim.id, "Reviewed contrary evidence masked")
            )
    for cv in value.cvs:
        refs(cv.claim_ids, set(claims), cv.id)
    for draft in value.draft_assertions:
        refs(draft.source_claim_ids, set(claims), draft.id)
    applications = {item.id: item for item in value.applications}
    for app in value.applications:
        refs((app.job_id,), set(jobs), app.id)
        refs((app.candidate_id,), {value.candidate.id}, app.id)
        if not app.history or app.history[0].state != "preparing":
            errors.append(Violation("application_start", app.id, "History starts with preparing"))
            continue
        if app.state != app.history[-1].state:
            errors.append(Violation("application_state", app.id, "State differs from history"))
        previous: State | None = None
        previous_time: datetime | None = None
        for entry in app.history:
            occurred = instant(entry.occurred_at)
            if previous is not None and entry.state not in TRANSITIONS[previous]:
                errors.append(
                    Violation("application_transition", entry.id, "Disallowed transition")
                )
            if previous_time is not None and occurred <= previous_time:
                errors.append(
                    Violation("application_chronology", entry.id, "Occurrence out of order")
                )
            if instant(entry.recorded_at) < occurred:
                errors.append(
                    Violation("recording_chronology", entry.id, "Recorded before occurrence")
                )
            if app.job_id in jobs and occurred < instant(jobs[app.job_id].posted_at):
                errors.append(Violation("application_before_job", entry.id, "Job not yet posted"))
            previous, previous_time = entry.state, occurred
    for message in value.messages:
        refs((message.application_id,), set(applications), message.id)
        refs((message.job_id,), set(jobs), message.id)
        if message.application_id not in applications:
            continue
        app = applications[message.application_id]
        before = [
            h.state for h in app.history if instant(h.occurred_at) <= instant(message.sent_at)
        ]
        if app.job_id != message.job_id or "applied" not in before:
            errors.append(
                Violation("message_chronology", message.id, "No matching prior application")
            )
        target = {"interview": "interview", "offer": "offer", "rejection": "closed"}.get(
            message.kind
        )
        if target is not None and target not in before:
            errors.append(
                Violation("message_state", message.id, "Outcome inconsistent with history")
            )
    return tuple(errors)


def validate_oracle(value: ScenarioInput, oracle: GroundTruth) -> tuple[Violation, ...]:
    input_shape = _shape(value)
    if input_shape:
        return tuple(input_shape)
    errors = _shape(oracle)
    if errors:
        return tuple(errors)
    try:
        as_of = instant(value.as_of)
    except ValueError:
        return (Violation("timestamp", value.id, "as_of"),)
    claims = {item.id: item for item in value.candidate.claims}
    evidence = {item.id: item for item in value.candidate.evidence}
    jobs = {item.id: item for item in value.jobs}
    cvs = {item.id: item for item in value.cvs}
    if oracle.scenario_id != value.id:
        errors.append(Violation("oracle_identity", oracle.id, "Wrong input identity"))
    if not oracle.requirements or not oracle.acceptable_cv_ids:
        errors.append(
            Violation("oracle_coverage", oracle.id, "Requirements/CV alternatives missing")
        )
    units = [
        (jobs[r.job_id].canonical_opportunity, r.subject)
        for r in oracle.requirements
        if r.job_id in jobs
    ]
    if len(set(units)) != len(units):
        errors.append(Violation("oracle_coverage", oracle.id, "Duplicate opportunity/subject unit"))
    if {key for key, _ in units} != {job.canonical_opportunity for job in value.jobs}:
        errors.append(Violation("oracle_coverage", oracle.id, "Unlabeled canonical opportunity"))
    observed = observable_bytes(value)
    if oracle.secret_canary is not None and oracle.secret_canary.encode() in observed:
        errors.append(Violation("ground_truth_leak", value.id, "Canary is observable"))
    for requirement in oracle.requirements:
        if (
            requirement.job_id not in jobs
            or requirement.source_quote not in jobs[requirement.job_id].text
        ):
            errors.append(Violation("requirement_source", requirement.id, "Quote/source mismatch"))
        selected = [claims[ref] for ref in requirement.claim_ids if ref in claims]
        if len(selected) != len(requirement.claim_ids) or len(set(requirement.claim_ids)) != len(
            selected
        ):
            errors.append(Violation("oracle_reference", requirement.id, "Bad claim references"))
        if any(c.subject != requirement.subject or c.unit != requirement.unit for c in selected):
            errors.append(Violation("oracle_scope", requirement.id, "Wrong claim subject/unit"))
        reviewed = [c for c in selected if claim_supported(c, evidence)]
        conflict = any(
            c.status == "contradicted"
            or any(
                evidence[ref].relation == "contradicts" and is_reviewed(evidence[ref])
                for ref in c.evidence_ids
                if ref in evidence
            )
            for c in selected
        )
        if conflict and requirement.assessment != "conflict":
            errors.append(Violation("oracle_assessment", requirement.id, "Conflict must escalate"))
        if requirement.assessment == "conflict" and not conflict:
            errors.append(Violation("oracle_assessment", requirement.id, "Conflict lacks basis"))
        if requirement.assessment == "supported" and not any(
            c.value >= requirement.minimum for c in reviewed
        ):
            errors.append(Violation("oracle_assessment", requirement.id, "Supported lacks review"))
        if requirement.assessment in ("partial", "gap") and not any(
            c.value < requirement.minimum for c in reviewed
        ):
            errors.append(Violation("oracle_assessment", requirement.id, "Shortfall lacks review"))
        if requirement.assessment == "partial" and not (
            requirement.unit == "skill_level"
            and any(0 < c.value < requirement.minimum for c in reviewed)
        ):
            errors.append(
                Violation("oracle_assessment", requirement.id, "Partial must establish a skill")
            )
        declared = any(
            c.status in ("self_reported", "candidate_support", "withdrawn")
            and c.value < requirement.minimum
            for c in selected
        )
        if requirement.declared_shortfall != declared:
            errors.append(Violation("declared_shortfall", requirement.id, "Declaration mismatch"))
        if requirement.assessment == "unknown" and reviewed and requirement.priority != "ambiguous":
            errors.append(
                Violation("oracle_assessment", requirement.id, "Reviewed fact labeled unknown")
            )
        if reviewed and not conflict and requirement.priority != "ambiguous":
            maximum = max(c.value for c in reviewed)
            expected_assessment = (
                "supported"
                if maximum >= requirement.minimum
                else ("partial" if requirement.unit == "skill_level" and maximum > 0 else "gap")
            )
            if requirement.assessment != expected_assessment:
                errors.append(
                    Violation("oracle_assessment", requirement.id, "Rubric shortfall differs")
                )
    blocked: set[str] = set()
    for draft in value.draft_assertions:
        if not any(
            ref in claims
            and claim_supported(claims[ref], evidence)
            and claims[ref].subject == draft.subject
            and claims[ref].unit == draft.unit
            and claims[ref].value >= draft.value
            for ref in draft.source_claim_ids
        ):
            blocked.add(draft.id)
    if set(oracle.blocked_draft_ids) != blocked or len(set(oracle.blocked_draft_ids)) != len(
        oracle.blocked_draft_ids
    ):
        errors.append(Violation("draft_oracle", oracle.id, "Blocked factual additions disagree"))
    safe_cvs = {
        cv.id: cv
        for cv in value.cvs
        if cv.claim_ids
        and all(ref in claims and claim_supported(claims[ref], evidence) for ref in cv.claim_ids)
    }
    scores = {
        cv_id: sum(
            requirement.assessment == "supported"
            and bool(set(requirement.claim_ids) & set(cv.claim_ids))
            for requirement in oracle.requirements
        )
        for cv_id, cv in safe_cvs.items()
    }
    maximum = max(scores.values(), default=-1)
    expected_cvs = {cv_id for cv_id, score in scores.items() if score == maximum}
    if (
        len(set(oracle.acceptable_cv_ids)) != len(oracle.acceptable_cv_ids)
        or set(oracle.acceptable_cv_ids) != expected_cvs
        or not set(oracle.acceptable_cv_ids) <= set(cvs)
    ):
        errors.append(
            Violation("cv_oracle", oracle.id, "Safe maximum-coverage alternatives disagree")
        )
    duplicates = {
        tuple(sorted(j.id for j in value.jobs if j.canonical_opportunity == key))
        for key in {j.canonical_opportunity for j in value.jobs}
    }
    duplicates = {group for group in duplicates if len(group) > 1}
    if (
        len(set(oracle.duplicate_job_groups)) != len(oracle.duplicate_job_groups)
        or any(len(set(group)) != len(group) for group in oracle.duplicate_job_groups)
        or {tuple(sorted(group)) for group in oracle.duplicate_job_groups} != duplicates
    ):
        errors.append(Violation("duplicate_oracle", oracle.id, "Opportunity alias groups disagree"))
    apps = {app.id: app for app in value.applications}
    future_states = {app.id: app.state for app in value.applications}
    future_times = {app.id: as_of for app in value.applications}
    for outcome in oracle.future_outcomes:
        try:
            valid_time = (
                outcome.application_id in apps
                and instant(outcome.occurs_at) > future_times[outcome.application_id]
            )
        except ValueError:
            valid_time = False
        valid_transition = (
            outcome.application_id in apps
            and outcome.state in TRANSITIONS[future_states[outcome.application_id]]
        )
        if not valid_time or not valid_transition:
            errors.append(Violation("future_outcome", outcome.id, "Invalid future narrative"))
        elif outcome.application_id in apps:
            future_states[outcome.application_id] = outcome.state
            future_times[outcome.application_id] = instant(outcome.occurs_at)
    return tuple(errors)


def validate_pair(pair: FixturePair) -> tuple[Violation, ...]:
    actual = validate_input(pair.inputs)
    oracle_shape = _shape(pair.oracle)
    if oracle_shape:
        return tuple(oracle_shape)
    expected = pair.oracle.expected_error_codes
    errors = list(validate_oracle(pair.inputs, pair.oracle))
    if sorted(item.code for item in actual) != sorted(expected):
        errors.append(Violation("expected_invalidity", pair.inputs.id, "Rejection reasons differ"))
    # Expected-invalid fixtures are still invalid inputs; matching the annotation only
    # makes the paired synthetic fixture suitable as a rejection test.
    return tuple(errors)
