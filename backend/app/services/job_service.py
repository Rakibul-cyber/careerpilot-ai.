# Read-side business-logic layer for the Job aggregate.
#
# Kept separate from JobIngestionService (writes/dedup) and
# JobVerificationService (lifecycle) so read endpoints depend only on read
# concerns. Thin pass-through to the repository, which already excludes
# soft-deleted rows.

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.job import Job
from app.repositories.job_repository import JobRepository


class JobService:
    def __init__(self, job_repository: JobRepository | None = None) -> None:
        self.job_repository = job_repository or JobRepository()

    def get_job_by_id(self, db: Session, job_id: UUID) -> Job | None:
        return self.job_repository.get_by_id(db, job_id)

    def list_jobs(
        self, db: Session, skip: int = 0, limit: int = 50
    ) -> list[Job]:
        return self.job_repository.list(db, skip=skip, limit=limit)

    def list_jobs_by_company(
        self, db: Session, company_id: UUID, skip: int = 0, limit: int = 50
    ) -> list[Job]:
        return self.job_repository.list_by_company(
            db, company_id=company_id, skip=skip, limit=limit
        )
