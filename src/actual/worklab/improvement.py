"""Evidence-linked improvement proposals and explicit measured comparisons."""

from typing import Annotated, Literal

from pydantic import Field, model_validator

from actual.core.primitives import ActorId, Contract, Digest, WorkspaceId, content_digest
from actual.workflows.ir import Name

from .teach import Activity, Event

type Mechanism = Literal[
    "ELIMINATE", "SIMPLIFY", "INTEGRATE", "DETERMINISTIC", "AI_ASSISTED", "HUMAN"
]


class Reference(Contract):
    session: Name
    event: Name


class Judgment(Contract):
    activity: Activity
    mechanism: Mechanism
    references: Annotated[tuple[Reference, ...], Field(min_length=1, max_length=16)]
    basis: Literal[
        "redundant_output",
        "rework_reduction",
        "structured_lookup",
        "structured_copy",
        "ambiguous_interpretation",
        "consequential_review",
    ]
    reviewer: ActorId
    provenance: Literal["synthetic_design_review", "human_claim"]
    consequence: Literal["none", "communication", "financial", "privileged", "unknown"]

    @model_validator(mode="after")
    def supported_kind(self) -> "Judgment":
        if (
            self.basis
            != {
                "ELIMINATE": "redundant_output",
                "SIMPLIFY": "rework_reduction",
                "INTEGRATE": "structured_lookup",
                "DETERMINISTIC": "structured_copy",
                "AI_ASSISTED": "ambiguous_interpretation",
                "HUMAN": "consequential_review",
            }[self.mechanism]
        ):
            raise ValueError("Mechanism requires its explicit reviewed basis")
        return self


class Recommendation(Contract):
    activity: Activity
    mechanism: Mechanism
    evidence_digest: Digest
    references: tuple[Reference, ...]
    provenance: Literal["synthetic_design_review", "human_claim"]
    reasoning: Annotated[str, Field(max_length=1024)]
    requires_review: Literal[True] = True
    executes: Literal[False] = False


REASONS: dict[Mechanism, str] = {
    "ELIMINATE": (
        "Review identifies redundant output. Check downstream needs before removal; "
        "repetition alone does not prove redundancy."
    ),
    "SIMPLIFY": "Review identifies rework. Propose fewer steps and verify outputs and controls.",
    "INTEGRATE": "Review identifies a structured lookup. Verify a scoped API and permission.",
    "DETERMINISTIC": "Review identifies structured copying. Prefer typed deterministic software.",
    "AI_ASSISTED": "Review identifies ambiguity. Require bounded assistance and human review.",
    "HUMAN": "Consequential or uncertain work needs review. Observations grant no authority.",
}


def recommend(
    events: tuple[Event, ...], judgments: tuple[Judgment, ...], owner: WorkspaceId
) -> tuple[Recommendation, ...]:
    if len(events) > 20_000 or len(judgments) > 128:
        raise ValueError("Improvement input budget exceeded")
    owner = WorkspaceId.model_validate(owner)
    observed: dict[tuple[str, str], Event] = {}
    for event in events:
        event = Event.model_validate(event)
        if event.workspace_id != owner:
            raise ValueError("Improvement owner mismatch")
        key = event.session, event.source_event
        if key in observed and observed[key] != event:
            raise ValueError("Conflicting evidence identity")
        observed[key] = event
    result = []
    judgments = tuple(Judgment.model_validate(supplied) for supplied in judgments)
    risky = {j.activity for j in judgments if j.consequence != "none"}
    for judgment in judgments:
        for reference in judgment.references:
            source = observed.get((reference.session, reference.event))
            if source is None or source.activity != judgment.activity:
                raise ValueError("Exact matching observation evidence required")
        mechanism: Mechanism = "HUMAN" if judgment.activity in risky else judgment.mechanism
        result.append(
            Recommendation(
                activity=judgment.activity,
                mechanism=mechanism,
                evidence_digest=content_digest(
                    {
                        "review": judgment.model_dump(mode="json"),
                        "events": [
                            observed[r.session, r.event].model_dump(mode="json")
                            for r in judgment.references
                        ],
                    }
                ),
                references=judgment.references,
                provenance=judgment.provenance,
                reasoning=REASONS[mechanism],
            )
        )
    order = {name: index for index, name in enumerate(REASONS)}
    return tuple(sorted(result, key=lambda r: (r.activity, order[r.mechanism], r.evidence_digest)))


class Measurements(Contract):
    workload_digest: Digest
    classification: Literal["synthetic"] = "synthetic"
    runs: Annotated[int, Field(ge=1)]
    failures: Annotated[int, Field(ge=0)]
    human_interventions: Annotated[int, Field(ge=0)]
    model_calls: Annotated[int, Field(ge=0)]
    human_active_seconds: Annotated[float, Field(ge=0, allow_inf_nan=False)] | None = None
    elapsed_seconds: Annotated[float, Field(ge=0, allow_inf_nan=False)] | None = None

    @model_validator(mode="after")
    def counts(self) -> "Measurements":
        if self.failures > self.runs:
            raise ValueError("Failure count exceeds measured runs")
        return self


def compare_measurements(
    manual: Measurements, assisted: Measurements
) -> dict[str, float | int | None]:
    manual, assisted = Measurements.model_validate(manual), Measurements.model_validate(assisted)
    if manual.workload_digest != assisted.workload_digest or manual.runs != assisted.runs:
        raise ValueError("Matched measured workload and count required")
    return {
        "human_active_seconds_change": None
        if manual.human_active_seconds is None or assisted.human_active_seconds is None
        else assisted.human_active_seconds - manual.human_active_seconds,
        "elapsed_seconds_change": None
        if manual.elapsed_seconds is None or assisted.elapsed_seconds is None
        else assisted.elapsed_seconds - manual.elapsed_seconds,
        "failures_change": assisted.failures - manual.failures,
        "interventions_change": assisted.human_interventions - manual.human_interventions,
        "model_calls_change": assisted.model_calls - manual.model_calls,
    }
