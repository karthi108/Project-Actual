"""Optional versioned preparation linkage; absence preserves legacy draft bytes."""

from typing import Literal, Self

from pydantic import model_validator

from actual.core.primitives import Contract
from actual.core.references import BusinessObjectRef

type MaterialKind = Literal["cv_adaptation", "application_message", "cover_letter"]


class PreparationContext(Contract):
    context_version: Literal["actual-preparation-v1"] = "actual-preparation-v1"
    template_version: Literal["source-linked-preparation-v1"] = "source-linked-preparation-v1"
    material_kind: MaterialKind
    job: BusinessObjectRef
    cv: BusinessObjectRef

    @model_validator(mode="after")
    def valid_refs(self) -> Self:
        if self.job.kind != "job" or self.cv.kind != "cv":
            raise ValueError("Preparation requires exact job and CV references")
        if (self.job.workspace_id, self.job.classification) != (
            self.cv.workspace_id,
            self.cv.classification,
        ):
            raise ValueError("Preparation sources differ in owner/classification")
        return self
