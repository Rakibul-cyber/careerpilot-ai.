# Job ingestion + deduplication engine.
#
# Single entry point for turning a RawJobInput (from a scraper/importer) into a
# persisted Job: it normalizes the title, resolves/creates the Company, and
# dedups on (source, external_id) — upserting the mutable fields when the same
# listing is seen again. Scrapers must go through here, never the repository.

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.job import Job, JobStatus
from app.repositories.job_repository import JobRepository
from app.schemas.ingestion import RawJobInput
from app.services.company_service import CompanyService
from app.utils.normalization import normalize_job_title

logger = get_logger(__name__)


class JobIngestionService:
    def __init__(
        self,
        job_repository: JobRepository | None = None,
        company_service: CompanyService | None = None,
    ) -> None:
        self.job_repository = job_repository or JobRepository()
        self.company_service = company_service or CompanyService()

    def ingest_job(self, db: Session, raw_job: RawJobInput) -> Job:
        """Ingest one raw job: normalize, resolve company, dedup-or-create."""
        normalized_title = normalize_job_title(raw_job.title)
        company = self.company_service.get_or_create_company(
            db, name=raw_job.company_name, location=raw_job.location
        )
        now = datetime.now(UTC)

        # Dedup only when the source provided a stable external id.
        if raw_job.external_id:
            existing = self.job_repository.get_by_source_external_id(
                db, raw_job.source, raw_job.external_id
            )
            if existing is not None:
                existing.title = raw_job.title
                existing.normalized_title = normalized_title
                existing.company_id = company.id
                existing.location = raw_job.location
                existing.remote_type = raw_job.remote_type
                existing.employment_type = raw_job.employment_type
                existing.source_url = raw_job.source_url
                existing.description = raw_job.description
                existing.requirements = raw_job.requirements
                existing.salary_min = raw_job.salary_min
                existing.salary_max = raw_job.salary_max
                existing.currency = raw_job.currency
                existing.posted_at = raw_job.posted_at
                existing.expires_at = raw_job.expires_at
                existing.last_verified_at = now
                existing.status = JobStatus.ACTIVE
                logger.info(
                    "Job deduplicated job_id=%s source=%s external_id=%s",
                    existing.id,
                    raw_job.source.value,
                    raw_job.external_id,
                )
                return self.job_repository.update(db, existing)

        job = Job(
            title=raw_job.title,
            normalized_title=normalized_title,
            company_id=company.id,
            location=raw_job.location,
            remote_type=raw_job.remote_type,
            employment_type=raw_job.employment_type,
            source=raw_job.source,
            source_url=raw_job.source_url,
            external_id=raw_job.external_id,
            description=raw_job.description,
            requirements=raw_job.requirements,
            salary_min=raw_job.salary_min,
            salary_max=raw_job.salary_max,
            currency=raw_job.currency,
            posted_at=raw_job.posted_at,
            expires_at=raw_job.expires_at,
            last_verified_at=now,
            status=JobStatus.ACTIVE,
        )
        created = self.job_repository.create(db, job)
        logger.info(
            "Job ingested job_id=%s source=%s external_id=%s",
            created.id,
            raw_job.source.value,
            raw_job.external_id,
        )
        return created
