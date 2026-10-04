"""Cover concrete normalized and reconciled contracts absent from public fixtures."""

import pytest
from pydantic import ValidationError
from sqlalchemy import Engine, insert
from sqlalchemy.exc import IntegrityError
from test_integration import ACTOR, advanced_application, job_event, reference, world

from actual.career.events import CVRecommended, DraftReviewed, RequirementsReviewed
from actual.career.jobs import Requirement
from actual.career.snapshot import CareerSnapshot
from actual.core.primitives import RequirementId, canonical_bytes
from actual.core.workflow import ContentReview
from actual.persistence import schema
from actual.persistence.errors import ConflictError, PersistenceError
from actual.persistence.mapping import entity_row
from actual.persistence.repository import CareerStore
from actual.profile.contracts import Assertion, claim_ref, evidence_ref


def requirement(snapshot: CareerSnapshot) -> Requirement:
    job = snapshot.jobs[0]
    quote = "Python at working level is essential."
    start = job.text.index(quote)
    return Requirement(
        id=RequirementId("requirement_" + "a" * 32),
        workspace_id=snapshot.workspace_id,
        revision=1,
        classification=snapshot.classification,
        job_id=job.id,
        job_revision=job.revision,
        job_digest=job.content_digest,
        assertion=Assertion(kind="skill", subject="python", unit="skill_level", value=2),
        priority="essential",
        source_start=start,
        source_end=start + len(quote),
        source_quote=quote,
        origin="ai_proposal",
    )


def reviewed(record: object, when: object) -> object:
    changed = record.model_copy(update={"revision": record.revision + 1})
    return changed.model_copy(
        update={
            "review": ContentReview(
                revision=changed.revision,
                content_digest=changed.content_digest,
                reviewer_id=ACTOR,
                reviewed_at=when,
                method="Synthetic explicit structured review",
                decision="accepted",
            )
        }
    )


def test_normalized_requirement_and_exact_review_observation_are_atomic(pg_engine: Engine) -> None:
    original = world()
    record = requirement(original)
    proposed = original.model_copy(update={"requirements": (record,)})
    store = CareerStore(pg_engine, original.workspace_id)
    store.save(proposed, expected_generation=0)
    assert store.export() == canonical_bytes(proposed)
    accepted = reviewed(record, original.as_of)
    changed = proposed.model_copy(update={"requirements": (accepted,)})
    with pytest.raises(ConflictError):
        store.save(changed, expected_generation=1)
    assert store.load().snapshot == proposed
    job, req = reference(original.jobs[0]), reference(accepted)
    event = job_event(
        changed,
        business_objects=(job, req),
        activity="requirements_reviewed",
        payload=RequirementsReviewed(
            job=job, requirements=(req,), reviewer_id=ACTOR, reviewed_at=original.as_of
        ),
    )
    store.save(changed, expected_generation=1, events=(event,))
    assert store.export() == canonical_bytes(changed)
    assert store.load().snapshot.requirements[0].origin == "ai_proposal"
    assert store.load_events() == (event,)


def test_requirement_observation_cannot_promote_an_unreviewed_proposal(pg_engine: Engine) -> None:
    original = world()
    record = requirement(original)
    proposed = original.model_copy(update={"requirements": (record,)})
    store = CareerStore(pg_engine, original.workspace_id)
    store.save(proposed, expected_generation=0)
    job, req = reference(original.jobs[0]), reference(record)
    event = job_event(
        proposed,
        business_objects=(job, req),
        activity="requirements_reviewed",
        payload=RequirementsReviewed(
            job=job, requirements=(req,), reviewer_id=ACTOR, reviewed_at=original.as_of
        ),
    )
    with pytest.raises(PersistenceError):
        store.append_events((event,))
    assert store.load().snapshot == proposed
    assert store.load_events() == ()


def test_database_requirement_reference_binds_exact_source_job_digest(pg_engine: Engine) -> None:
    original = world()
    store = CareerStore(pg_engine, original.workspace_id)
    store.save(original, expected_generation=0)
    stale = requirement(original).model_copy(update={"job_digest": "a" * 64})
    row = entity_row(stale, 0, {job.id.root: job for job in original.jobs})
    with pytest.raises(IntegrityError) as caught:
        with pg_engine.begin() as connection:
            connection.execute(
                insert(schema.object_identities),
                {
                    "workspace_id": original.workspace_id.root,
                    "object_id": stale.id.root,
                    "kind": "requirement",
                    "revision": stale.revision,
                    "classification": stale.classification,
                    "digest": row["payload_digest"],
                },
            )
            connection.execute(insert(schema.requirements), row)
    assert caught.value.orig.sqlstate == "23503"
    assert store.load().snapshot == original


def test_cv_recommendation_preserves_authored_order_and_current_references(
    pg_engine: Engine,
) -> None:
    original = world()
    store = CareerStore(pg_engine, original.workspace_id)
    store.save(original, expected_generation=0)
    job, profile = reference(original.jobs[0]), reference(original.profile)
    cvs = tuple(reference(cv) for cv in reversed(original.cvs))
    event = job_event(
        original,
        business_objects=(job, profile, *cvs),
        activity="cv_recommended",
        payload=CVRecommended(job=job, profile=profile, cvs=cvs),
    )
    store.append_events((event,))
    restored = store.load_events()[0]
    assert restored == event
    assert restored.payload.cvs == cvs


@pytest.mark.parametrize("source_indexes", [(1,), (3,), (0, 1)])
def test_accepted_draft_observation_requires_exact_bound_positive_sources(
    pg_engine: Engine, source_indexes: tuple[int, ...]
) -> None:
    original = world()
    store = CareerStore(pg_engine, original.workspace_id)
    store.save(original, expected_generation=0)
    draft = reviewed(original.drafts[0], original.as_of)
    changed = original.model_copy(update={"drafts": (draft, *original.drafts[1:])})
    ref = reference(draft)
    event = job_event(
        changed,
        business_objects=(ref,),
        evidence_refs=tuple(evidence_ref(original.profile.evidence[i]) for i in source_indexes),
        activity="draft_reviewed",
        payload=DraftReviewed(
            draft=ref, decision="accepted", reviewer_id=ACTOR, reviewed_at=original.as_of
        ),
    )
    with pytest.raises(PersistenceError):
        store.save(changed, expected_generation=1, events=(event,))
    assert store.load().snapshot == original
    assert store.load_events() == ()


def test_source_withdrawal_requires_explicit_reconciliation_of_all_dependents(
    pg_engine: Engine,
) -> None:
    original = world()
    store = CareerStore(pg_engine, original.workspace_id)
    store.save(original, expected_generation=0)
    historical = job_event(original, evidence_refs=(evidence_ref(original.profile.evidence[0]),))
    store.append_events((historical,))
    withdrawn = original.profile.evidence[0].model_copy(
        update={"revision": 2, "status": "withdrawn"}
    )
    sources = (withdrawn, *original.profile.evidence[1:])
    with pytest.raises(ValidationError):
        original.profile.model_copy(update={"revision": 2, "evidence": sources})
    old_claim = original.profile.claims[0]
    claim = old_claim.model_copy(
        update={
            "revision": 2,
            "status": "withdrawn",
            "review": None,
            "evidence_refs": (evidence_ref(withdrawn),),
        }
    )
    profile = original.profile.model_copy(
        update={"revision": 2, "evidence": sources, "claims": (claim, *original.profile.claims[1:])}
    )
    replacements = {old_claim.id: claim_ref(claim)}
    cvs = tuple(
        cv.model_copy(
            update={
                "revision": cv.revision + 1,
                "claim_refs": tuple(replacements.get(ref.claim_id, ref) for ref in cv.claim_refs),
            }
        )
        if any(ref.claim_id in replacements for ref in cv.claim_refs)
        else cv
        for cv in original.cvs
    )
    draft = original.drafts[0]
    reconciled = draft.model_copy(
        update={
            "revision": draft.revision + 1,
            "assertions": tuple(
                proposal.model_copy(
                    update={
                        "source_claim_refs": tuple(
                            replacements.get(ref.claim_id, ref)
                            for ref in proposal.source_claim_refs
                        )
                    }
                )
                for proposal in draft.assertions
            ),
        }
    )
    changed = original.model_copy(
        update={"profile": profile, "cvs": cvs, "drafts": (reconciled, *original.drafts[1:])}
    )
    store.save(changed, expected_generation=1)
    assert store.export() == canonical_bytes(changed)
    assert store.load().snapshot.profile.claims[0].status == "withdrawn"
    assert (
        store.load().snapshot.profile.evidence[0].source_kind
        == original.profile.evidence[0].source_kind
    )
    # Historical metadata retains the original source snapshot without claiming
    # that its previous support remains current after withdrawal.
    assert store.load_events() == (historical,)


def test_ordinary_updates_cannot_import_a_historical_application(pg_engine: Engine) -> None:
    original = world()
    empty = original.model_copy(update={"applications": ()})
    store = CareerStore(pg_engine, original.workspace_id)
    store.save(empty, expected_generation=0)
    historical, event = advanced_application(original)
    assert len(historical.applications[0].history) == 2
    with pytest.raises(ConflictError):
        store.save(historical, expected_generation=1, events=(event,))
    assert store.load().snapshot == empty
    assert store.load_events() == ()
