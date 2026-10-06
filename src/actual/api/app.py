"""Thin typed routes delegate all Career intents to application use cases."""

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Annotated, cast

from fastapi import APIRouter, Depends, FastAPI, Path, Query, Request
from fastapi.exceptions import RequestValidationError
from sqlalchemy import Engine, text
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse

from actual.application.commands import (
    AddJob,
    AttachEvidence,
    CreateApplication,
    CreateClaim,
    InitializeCareer,
    TransitionApplication,
)
from actual.application.errors import UseCaseCode, UseCaseError
from actual.application.ports import CareerState
from actual.application.profile_commands import (
    ReviewSyntheticClaim,
    ReviewSyntheticEvidence,
    WithdrawEvidence,
)
from actual.application.service import CareerService
from actual.career.applications import Application
from actual.career.events import WorkEvent
from actual.career.jobs import Job
from actual.core.primitives import ApplicationId, ClaimId, EvidenceId, JobId
from actual.persistence.database import create_database_engine, verify_schema
from actual.persistence.errors import (
    ConflictError,
    CorruptStorageError,
    DeletedWorkspaceError,
    NotFoundError,
    PersistenceError,
    SchemaMismatchError,
)
from actual.persistence.repository import CareerStore

from .config import ApiSettings
from .contracts import (
    ApplicationView,
    CareerView,
    ErrorResponse,
    EvidenceProfileResponse,
    Health,
    JobView,
    Page,
    ProfileView,
    StatePage,
)
from .transport import LocalBoundary, error_response
from .wiring import ApiRuntime, career_service, runtime

type Service = Annotated[CareerService, Depends(career_service)]
type Offset = Annotated[int, Query(ge=0, le=1_000_000)]
type Limit = Annotated[int, Query(ge=1, le=100)]
type JobPath = Annotated[str, Path(pattern=r"^job_[0-9a-f]{32}$")]
type ApplicationPath = Annotated[str, Path(pattern=r"^application_[0-9a-f]{32}$")]
type EvidencePath = Annotated[str, Path(pattern=r"^evidence_[0-9a-f]{32}$")]
type ClaimPath = Annotated[str, Path(pattern=r"^claim_[0-9a-f]{32}$")]

_ERRORS: dict[UseCaseCode, tuple[int, str]] = {
    UseCaseCode.RESOURCE_NOT_FOUND: (404, "The requested resource is absent."),
    UseCaseCode.STATE_CONFLICT: (409, "The operation conflicts with current state."),
    UseCaseCode.STALE_GENERATION: (409, "Reload current state before attempting this mutation."),
    UseCaseCode.DUPLICATE_RESOURCE: (409, "The resource or application intent already exists."),
    UseCaseCode.INVALID_APPLICATION_TRANSITION: (
        409,
        "The application transition is not permitted.",
    ),
    UseCaseCode.INVALID_DOMAIN_INPUT: (422, "The command does not satisfy the domain contract."),
    UseCaseCode.DEPENDENCY_RECONCILIATION_REQUIRED: (
        409,
        "This change requires an explicit review or dependency reconciliation use case.",
    ),
    UseCaseCode.SYNTHETIC_ONLY: (403, "Only isolated synthetic development records may be served."),
}


def _window[T](items: tuple[T, ...], offset: int, limit: int) -> tuple[tuple[T, ...], int | None]:
    selected = items[offset : offset + limit]
    following = offset + len(selected)
    return selected, following if following < len(items) else None


def _application_view(state: CareerState, identifier: ApplicationId) -> ApplicationView:
    record = next(item for item in state.snapshot.applications if item.id == identifier)
    return ApplicationView(generation=state.generation, application=record)


def create_app(
    settings: ApiSettings | None = None,
    engine: Engine | None = None,
    clock: Callable[[], datetime] | None = None,
) -> FastAPI:
    configured = settings if settings is not None else ApiSettings.from_environment()
    owned_engine = engine is None
    active_engine = engine if engine is not None else create_database_engine()
    current_clock = clock if clock is not None else lambda: datetime.now(UTC)

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        application.state.runtime = ApiRuntime(configured, active_engine, current_clock)
        try:
            yield
        finally:
            if owned_engine:
                active_engine.dispose()

    app = FastAPI(
        title="ACTUAL synthetic Career API",
        version="1.0.0",
        description=(
            "Isolated local synthetic development only. No authentication or real-data access. "
            "All mutations require the current aggregate generation. Synthetic source and claim "
            "reviews are separate operations; independent verification and external submission "
            "are not API operations."
        ),
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url="/api/v1/openapi.json",
        redirect_slashes=False,
    )
    app.add_middleware(LocalBoundary, settings=configured)

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request: Request, error: Exception) -> JSONResponse:
        return error_response(
            request.scope, 422, "INVALID_REQUEST", "Request does not match the API contract."
        )

    @app.exception_handler(UseCaseError)
    async def use_case_failure(request: Request, error: Exception) -> JSONResponse:
        failure = cast(UseCaseError, error)
        status, message = _ERRORS[failure.code]
        return error_response(request.scope, status, failure.code.value, message)

    @app.exception_handler(PersistenceError)
    async def storage_failure(request: Request, error: Exception) -> JSONResponse:
        if isinstance(error, DeletedWorkspaceError):
            status, code, message = 410, "WORKSPACE_DELETED", "The workspace was deleted."
        elif isinstance(error, NotFoundError):
            status, code, message = 404, "RESOURCE_NOT_FOUND", "The requested resource is absent."
        elif isinstance(error, ConflictError):
            status, code, message = (
                409,
                "STATE_CONFLICT",
                "The transaction conflicts with stored state.",
            )
        elif isinstance(error, CorruptStorageError):
            status, code, message = (
                500,
                "STORAGE_INTEGRITY_ERROR",
                "Stored state failed integrity validation.",
            )
        elif isinstance(error, SchemaMismatchError):
            status, code, message = 503, "NOT_READY", "The database schema is not ready."
        else:
            status, code, message = (
                503,
                "DATABASE_UNAVAILABLE",
                "The database operation is unavailable.",
            )
        return error_response(request.scope, status, code, message)

    @app.exception_handler(HTTPException)
    async def http_failure(request: Request, error: Exception) -> JSONResponse:
        failure = cast(HTTPException, error)
        status = failure.status_code
        code = "METHOD_NOT_ALLOWED" if status == 405 else "RESOURCE_NOT_FOUND"
        response = error_response(
            request.scope, status, code, "The requested operation is unavailable."
        )
        if status == 405 and failure.headers is not None and "Allow" in failure.headers:
            response.headers["Allow"] = failure.headers["Allow"]
        return response

    responses: dict[int | str, dict[str, object]] = {
        status: {"model": ErrorResponse}
        for status in (400, 403, 404, 408, 409, 410, 413, 415, 422, 500, 503)
    }
    router = APIRouter(prefix="/api/v1", responses=responses)

    @app.get("/health/live", response_model=Health, responses=responses, tags=["health"])
    def live() -> Health:
        return Health(status="live")

    @app.get("/health/ready", response_model=Health, responses=responses, tags=["health"])
    def ready(request: Request) -> Health | JSONResponse:
        context = runtime(request)
        try:
            with context.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
                verify_schema(connection)
            stored = CareerStore(context.engine, context.settings.workspace_id).load()
            if stored.snapshot.classification != "synthetic":
                raise UseCaseError(UseCaseCode.SYNTHETIC_ONLY)
        except NotFoundError:
            pass  # A migrated empty development database is ready to initialize.
        except Exception:
            return error_response(
                request.scope, 503, "NOT_READY", "The development database is not ready."
            )
        return Health(status="ready")

    @router.post("/career", response_model=CareerView, status_code=201, tags=["career"])
    def initialize(command: InitializeCareer, service: Service) -> CareerView:
        """Initialize the configured synthetic workspace with its first manual job."""
        state = service.initialize(command)
        return CareerView(generation=state.generation, snapshot=state.snapshot)

    @router.get("/career", response_model=CareerView, tags=["career"])
    def career(service: Service) -> CareerView:
        """Read current jobs, profile/evidence, CV metadata and application histories."""
        state = service.get_state()
        return CareerView(generation=state.generation, snapshot=state.snapshot)

    @router.post("/jobs", response_model=JobView, status_code=201, tags=["jobs"])
    def intake_job(command: AddJob, service: Service) -> JobView:
        """Paste a manual job; source references are metadata and are never fetched."""
        state = service.add_job(command)
        job = next(item for item in state.snapshot.jobs if item.id == command.job.id)
        return JobView(generation=state.generation, job=job)

    @router.get("/jobs", response_model=StatePage[Job], tags=["jobs"])
    def jobs(service: Service, offset: Offset = 0, limit: Limit = 20) -> StatePage[Job]:
        """List current jobs in stable typed-ID order; each page identifies its generation."""
        state = service.get_state()
        records = tuple(sorted(state.snapshot.jobs, key=lambda item: item.id.root))
        items, following = _window(records, offset, limit)
        return StatePage[Job](
            generation=state.generation,
            items=items,
            offset=offset,
            limit=limit,
            total=len(records),
            next_offset=following,
        )

    @router.get("/jobs/{job_id}", response_model=JobView, tags=["jobs"])
    def job(job_id: JobPath, service: Service) -> JobView:
        state, record = service.job(JobId(job_id))
        return JobView(generation=state.generation, job=record)

    @router.get("/profile", response_model=ProfileView, tags=["profile"])
    def profile(service: Service) -> ProfileView:
        """Inspect claim/evidence state without retrieving the complete career snapshot."""
        state = service.get_state()
        return ProfileView(generation=state.generation, profile=state.snapshot.profile)

    @router.post("/profile/claims", response_model=ProfileView, status_code=201, tags=["profile"])
    def create_claim(command: CreateClaim, service: Service) -> ProfileView:
        """Record a self-reported claim; callers cannot assign review or verification state."""
        state = service.create_claim(command)
        return ProfileView(generation=state.generation, profile=state.snapshot.profile)

    @router.post("/profile/evidence", response_model=ProfileView, status_code=201, tags=["profile"])
    def attach_evidence(command: AttachEvidence, service: Service) -> ProfileView:
        """Attach an unreviewed source to an unreviewed, material-independent claim."""
        state = service.attach_evidence(command)
        return ProfileView(generation=state.generation, profile=state.snapshot.profile)

    @router.get("/profile/evidence", response_model=EvidenceProfileResponse, tags=["profile"])
    def evidence_profile(service: Service) -> EvidenceProfileResponse:
        """Read current declarations, source reviews, support and conflicts separately."""
        state, view = service.evidence_profile()
        return EvidenceProfileResponse(generation=state.generation, profile=view)

    @router.post(
        "/profile/evidence/{evidence_id}/synthetic-review",
        response_model=ProfileView,
        tags=["profile"],
    )
    def review_evidence(
        evidence_id: EvidencePath, command: ReviewSyntheticEvidence, service: Service
    ) -> ProfileView:
        """Review an exact synthetic fixture source; this does not accept its claims."""
        state = service.review_synthetic_evidence(EvidenceId(evidence_id), command)
        return ProfileView(generation=state.generation, profile=state.snapshot.profile)

    @router.post(
        "/profile/claims/{claim_id}/synthetic-review",
        response_model=ProfileView,
        tags=["profile"],
    )
    def review_claim(
        claim_id: ClaimPath, command: ReviewSyntheticClaim, service: Service
    ) -> ProfileView:
        """Accept a pinned claim only against sufficient current reviewed synthetic support."""
        state = service.review_synthetic_claim(ClaimId(claim_id), command)
        return ProfileView(generation=state.generation, profile=state.snapshot.profile)

    @router.post(
        "/profile/evidence/{evidence_id}/withdraw",
        response_model=ProfileView,
        tags=["profile"],
    )
    def withdraw_evidence(
        evidence_id: EvidencePath, command: WithdrawEvidence, service: Service
    ) -> ProfileView:
        """Retain a withdrawn source and atomically invalidate dependent claim support."""
        state = service.withdraw_evidence(EvidenceId(evidence_id), command)
        return ProfileView(generation=state.generation, profile=state.snapshot.profile)

    @router.post(
        "/applications", response_model=ApplicationView, status_code=201, tags=["applications"]
    )
    def create_application(command: CreateApplication, service: Service) -> ApplicationView:
        """Start preparing; supplied history and initial later states are forbidden."""
        state = service.create_application(command)
        return _application_view(state, command.id)

    @router.get("/applications", response_model=StatePage[Application], tags=["applications"])
    def applications(
        service: Service, offset: Offset = 0, limit: Limit = 20
    ) -> StatePage[Application]:
        state = service.get_state()
        records = tuple(sorted(state.snapshot.applications, key=lambda item: item.id.root))
        items, following = _window(records, offset, limit)
        return StatePage[Application](
            generation=state.generation,
            items=items,
            offset=offset,
            limit=limit,
            total=len(records),
            next_offset=following,
        )

    @router.get(
        "/applications/{application_id}", response_model=ApplicationView, tags=["applications"]
    )
    def application(application_id: ApplicationPath, service: Service) -> ApplicationView:
        state, record = service.application(ApplicationId(application_id))
        return ApplicationView(generation=state.generation, application=record)

    @router.post(
        "/applications/{application_id}/status",
        response_model=ApplicationView,
        tags=["applications"],
    )
    def transition(
        application_id: ApplicationPath, command: TransitionApplication, service: Service
    ) -> ApplicationView:
        """Append a valid reported status; this neither reviews content nor submits externally."""
        identifier = ApplicationId(application_id)
        return _application_view(service.transition_application(identifier, command), identifier)

    @router.get("/events", response_model=Page[WorkEvent], tags=["events"])
    def events(service: Service, offset: Offset = 0, limit: Limit = 20) -> Page[WorkEvent]:
        """Read retained observations ordered by occurrence and event ID."""
        records = service.events()
        items, following = _window(records, offset, limit)
        return Page[WorkEvent](
            items=items, offset=offset, limit=limit, total=len(records), next_offset=following
        )

    app.include_router(router)
    return app
