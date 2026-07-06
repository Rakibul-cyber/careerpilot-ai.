# Job HTTP endpoints (v1) — read-only, all protected.
#
# Thin transport layer: resolve dependencies, delegate to JobService, translate
# not-found into 404. Soft-deleted rows are already excluded by the repository.

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import (
    get_current_user,
    get_db,
    get_job_embedding_service,
    get_job_service,
    get_semantic_job_search_service,
    require_role,
)
from app.models.job import JobSource, JobStatus
from app.models.user import User, UserRole
from app.schemas.job import JobFilter, JobRead
from app.schemas.semantic_search import (
    EmbeddingRebuildResponse,
    JobEmbeddingRead,
    SemanticSearchRequest,
    SemanticSearchResult,
)
from app.services.ai.base_embedding_client import EmbeddingAIError
from app.services.job_embedding_service import (
    JobEmbeddingService,
    JobNotFoundError,
)
from app.services.job_service import JobService
from app.services.semantic_job_search_service import (
    SemanticJobSearchService,
)

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.get("", response_model=list[JobRead])
def list_jobs(
    query: str | None = None,
    location: str | None = None,
    employment_type: str | None = None,
    remote_type: str | None = None,
    status: JobStatus | None = None,
    source: JobSource | None = None,
    company: str | None = None,
    salary_min: int | None = Query(None, ge=0),
    salary_max: int | None = Query(None, ge=0),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    job_service: JobService = Depends(get_job_service),
    current_user: User = Depends(get_current_user),
) -> list[JobRead]:
    """Search jobs by optional filters, paginated.

    With no ``status`` filter the result is restricted to ACTIVE jobs. Text
    ``query`` uses full-text search plus a safe ILIKE substring fallback.
    ``sort_by`` accepts created_at / posted_at / salary_min / salary_max /
    relevance (relevance needs a ``query``); invalid ``sort_by`` / ``sort_order``
    fall back to ``created_at`` / ``desc``.
    """
    filters = JobFilter(
        query=query,
        location=location,
        employment_type=employment_type,
        remote_type=remote_type,
        status=status,
        source=source,
        company=company,
        salary_min=salary_min,
        salary_max=salary_max,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return job_service.search_jobs(db, filters=filters, skip=skip, limit=limit)


@router.post("/semantic-search", response_model=list[SemanticSearchResult])
def semantic_search_jobs(
    payload: SemanticSearchRequest,
    db: Session = Depends(get_db),
    search_service: SemanticJobSearchService = Depends(
        get_semantic_job_search_service
    ),
    current_user: User = Depends(get_current_user),
) -> list[SemanticSearchResult]:
    """Rank ACTIVE jobs by semantic similarity to a natural-language query.

    Sits beside the filter/full-text search on GET /jobs (does not replace it).
    Excludes soft-deleted, non-ACTIVE, and non-embedded jobs. A provider
    failure returns a clean 502 rather than crashing.
    """
    try:
        results = search_service.search(db, payload.query, limit=payload.limit)
    except EmbeddingAIError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Embedding provider is unavailable",
        )
    return [
        SemanticSearchResult(job=job, similarity_score=score)
        for job, score in results
    ]


@router.post("/embeddings/rebuild", response_model=EmbeddingRebuildResponse)
def rebuild_job_embeddings(
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    embedding_service: JobEmbeddingService = Depends(
        get_job_embedding_service
    ),
    _: User = Depends(require_role(UserRole.ADMIN)),
) -> EmbeddingRebuildResponse:
    """Batch-embed ACTIVE jobs whose embedding is pending or failed (admin)."""
    result = embedding_service.rebuild(db, limit=limit)
    return EmbeddingRebuildResponse(**result)


@router.post("/{job_id}/embedding", response_model=JobEmbeddingRead)
def embed_job(
    job_id: UUID,
    db: Session = Depends(get_db),
    embedding_service: JobEmbeddingService = Depends(
        get_job_embedding_service
    ),
    current_user: User = Depends(get_current_user),
) -> JobEmbeddingRead:
    """Generate (or refresh) the embedding for one job.

    Returns 200 with embedding_status even on provider failure (the row is
    persisted with embedding_status=failed). Unknown/deleted job -> 404.
    """
    try:
        job = embedding_service.embed_job(db, job_id)
    except JobNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job not found"
        )
    return JobEmbeddingRead(
        job_id=job.id,
        embedding_status=job.embedding_status,
        embedding_model=job.embedding_model,
        embedding_error=job.embedding_error,
        embedded_at=job.embedded_at,
    )


@router.get("/{job_id}", response_model=JobRead)
def get_job(
    job_id: UUID,
    db: Session = Depends(get_db),
    job_service: JobService = Depends(get_job_service),
    current_user: User = Depends(get_current_user),
) -> JobRead:
    """Fetch a single job by id."""
    job = job_service.get_job_by_id(db, job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )
    return job
