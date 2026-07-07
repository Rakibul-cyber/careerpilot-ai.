# Data-access layer for the Job aggregate.
#
# Works purely with ORM models, contains no business logic (normalization/dedup
# rules live in the service layer), and excludes soft-deleted rows
# (deleted_at IS NULL). List results are newest-first.

# Deferred annotations: the `list` method shadows the builtin `list` in the
# class namespace, which would break `-> list[Job]` return hints if evaluated
# eagerly. This keeps them as strings.
from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.job import Job, JobSource, JobStatus
from app.schemas.job import JobFilter
from app.utils.normalization import normalize_company_name, normalize_job_title
from app.utils.search import escape_like

# Whitelisted sort columns; anything else falls back to created_at.
_SORT_COLUMNS = {
    "created_at": Job.created_at,
    "posted_at": Job.posted_at,
    "salary_min": Job.salary_min,
    "salary_max": Job.salary_max,
}

# Escape char used with every ILIKE so escape_like()'s backslashes take effect.
_LIKE_ESCAPE = "\\"

# PostgreSQL text-search configuration used for the FTS vector/query.
_FTS_CONFIG = "english"


def _ilike_contains(column, text: str):
    """Build a literal, wildcard-escaped case-insensitive contains match.

    Centralizes the escape + '%...%' pattern so every text filter is built the
    same safe way and trigram-index-friendly.
    """
    return column.ilike(f"%{escape_like(text)}%", escape=_LIKE_ESCAPE)


class JobRepository:
    """Persistence operations for :class:`Job`."""

    def get_by_id(self, db: Session, job_id: UUID) -> Job | None:
        """Return the live job with this id, or None."""
        stmt = select(Job).where(
            Job.id == job_id,
            Job.deleted_at.is_(None),
        )
        return db.execute(stmt).scalar_one_or_none()

    def get_by_source_external_id(
        self, db: Session, source: JobSource, external_id: str
    ) -> Job | None:
        """Return the live job matching this (source, external_id) pair, or None."""
        stmt = select(Job).where(
            Job.source == source,
            Job.external_id == external_id,
            Job.deleted_at.is_(None),
        )
        return db.execute(stmt).scalar_one_or_none()

    def list(self, db: Session, skip: int = 0, limit: int = 50) -> list[Job]:
        """Return a page of live jobs, newest first."""
        stmt = (
            select(Job)
            .where(Job.deleted_at.is_(None))
            .order_by(Job.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(db.execute(stmt).scalars().all())

    def list_by_company(
        self, db: Session, company_id: UUID, skip: int = 0, limit: int = 50
    ) -> list[Job]:
        """Return a page of live jobs for one company, newest first."""
        stmt = (
            select(Job)
            .where(
                Job.company_id == company_id,
                Job.deleted_at.is_(None),
            )
            .order_by(Job.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(db.execute(stmt).scalars().all())

    def search(
        self,
        db: Session,
        filters: JobFilter,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Job]:
        """Search live jobs by the given filters.

        Status defaults to ACTIVE when the caller doesn't specify one, so the
        default listing never surfaces expired/archived/duplicate jobs. All text
        matches are literal (LIKE wildcards escaped) and sorting is whitelisted.
        """
        conditions = [Job.deleted_at.is_(None)]

        status = filters.status if filters.status is not None else JobStatus.ACTIVE
        conditions.append(Job.status == status)

        # Compute the tsquery once when a query is present; reused by the match
        # branch and (for sort_by="relevance") the ranking expression.
        tsquery = None
        if filters.query:
            # websearch_to_tsquery is safe on arbitrary user input (it never
            # raises), so FTS + the ILIKE branches simply OR together — ILIKE
            # remains the substring fallback when FTS doesn't match.
            tsquery = func.websearch_to_tsquery(_FTS_CONFIG, filters.query)
            query_branches = [
                Job.search_vector.op("@@")(tsquery),
                _ilike_contains(Job.description, filters.query),
                _ilike_contains(Job.requirements, filters.query),
            ]
            # Only match normalized_title when the query normalizes to something;
            # otherwise "%%" would match every row (e.g. query="remote").
            normalized_query = normalize_job_title(filters.query)
            if normalized_query:
                query_branches.insert(
                    1, _ilike_contains(Job.normalized_title, normalized_query)
                )
            conditions.append(or_(*query_branches))

        if filters.location:
            conditions.append(_ilike_contains(Job.location, filters.location))

        if filters.employment_type:
            conditions.append(Job.employment_type == filters.employment_type)

        if filters.remote_type:
            conditions.append(Job.remote_type == filters.remote_type)

        if filters.source:
            conditions.append(Job.source == filters.source)

        if filters.salary_min is not None:
            # Keep jobs with unknown upper salary rather than excluding them.
            conditions.append(
                or_(
                    Job.salary_max >= filters.salary_min,
                    Job.salary_max.is_(None),
                )
            )

        if filters.salary_max is not None:
            conditions.append(
                or_(
                    Job.salary_min <= filters.salary_max,
                    Job.salary_min.is_(None),
                )
            )

        stmt = select(Job)

        if filters.company:
            stmt = stmt.join(Company, Job.company_id == Company.id)
            company_branches = [_ilike_contains(Company.name, filters.company)]
            normalized_company = normalize_company_name(filters.company)
            if normalized_company:
                company_branches.append(
                    _ilike_contains(Company.normalized_name, normalized_company)
                )
            conditions.append(or_(*company_branches))

        # Ordering. "relevance" ranks FTS matches (only meaningful with a query);
        # otherwise a whitelisted column + direction, with invalid values falling
        # back to created_at desc.
        if filters.sort_by == "relevance":
            if tsquery is not None:
                ordering = [
                    func.ts_rank_cd(Job.search_vector, tsquery).desc(),
                    Job.created_at.desc(),
                ]
            else:
                ordering = [Job.created_at.desc()]
        else:
            sort_column = _SORT_COLUMNS.get(filters.sort_by, Job.created_at)
            ascending = filters.sort_order.lower() == "asc"
            direction = sort_column.asc() if ascending else sort_column.desc()
            ordering = [direction.nullslast()]

        stmt = stmt.where(*conditions).order_by(*ordering).offset(skip).limit(limit)
        return list(db.execute(stmt).scalars().all())

    def list_stale_active_jobs(
        self,
        db: Session,
        older_than: datetime,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Job]:
        """Active jobs never verified or last verified before ``older_than``.

        Ordered oldest-verified first (NULLs first) so the most overdue jobs
        are processed before fresher ones.
        """
        stmt = (
            select(Job)
            .where(
                Job.deleted_at.is_(None),
                Job.status == JobStatus.ACTIVE,
                or_(
                    Job.last_verified_at.is_(None),
                    Job.last_verified_at < older_than,
                ),
            )
            .order_by(Job.last_verified_at.asc().nullsfirst())
            .offset(skip)
            .limit(limit)
        )
        return list(db.execute(stmt).scalars().all())

    def list_expired_jobs(
        self,
        db: Session,
        now: datetime,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Job]:
        """Active jobs whose expires_at deadline has passed."""
        stmt = (
            select(Job)
            .where(
                Job.deleted_at.is_(None),
                Job.status == JobStatus.ACTIVE,
                Job.expires_at.is_not(None),
                Job.expires_at < now,
            )
            .order_by(Job.expires_at.asc())
            .offset(skip)
            .limit(limit)
        )
        return list(db.execute(stmt).scalars().all())

    def list_jobs_for_archival(
        self,
        db: Session,
        older_than: datetime,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Job]:
        """Expired jobs untouched since ``older_than`` (candidates to archive)."""
        stmt = (
            select(Job)
            .where(
                Job.deleted_at.is_(None),
                Job.status == JobStatus.EXPIRED,
                Job.updated_at < older_than,
            )
            .order_by(Job.updated_at.asc())
            .offset(skip)
            .limit(limit)
        )
        return list(db.execute(stmt).scalars().all())

    def create(self, db: Session, job: Job) -> Job:
        """Persist a new job."""
        db.add(job)
        db.commit()
        db.refresh(job)
        return job

    def update(self, db: Session, job: Job) -> Job:
        """Flush pending changes on an already-tracked job instance."""
        db.commit()
        db.refresh(job)
        return job

    def soft_delete(self, db: Session, job: Job) -> Job:
        """Mark the job deleted by stamping deleted_at (UTC)."""
        job.deleted_at = datetime.now(UTC)
        db.commit()
        db.refresh(job)
        return job
