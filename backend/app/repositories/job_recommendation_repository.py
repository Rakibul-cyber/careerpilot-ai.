# Data-access layer for the JobRecommendation aggregate.
#
# All reads are scoped by user_id and exclude soft-deleted rows. No ranking
# logic here (that lives in JobRecommendationService). Lists are ranked by
# final_score descending.

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.job_recommendation import JobRecommendation


class JobRecommendationRepository:
    """Persistence operations for :class:`JobRecommendation`."""

    def create(
        self, db: Session, recommendation: JobRecommendation
    ) -> JobRecommendation:
        """Persist a new recommendation."""
        db.add(recommendation)
        db.commit()
        db.refresh(recommendation)
        return recommendation

    def update(
        self, db: Session, recommendation: JobRecommendation
    ) -> JobRecommendation:
        """Flush pending changes on an already-tracked recommendation."""
        db.commit()
        db.refresh(recommendation)
        return recommendation

    def get_by_profile_job(
        self,
        db: Session,
        resume_profile_id: UUID,
        job_id: UUID,
        user_id: UUID,
    ) -> JobRecommendation | None:
        """Return the user's live recommendation for (profile, job), or None."""
        stmt = select(JobRecommendation).where(
            JobRecommendation.resume_profile_id == resume_profile_id,
            JobRecommendation.job_id == job_id,
            JobRecommendation.user_id == user_id,
            JobRecommendation.deleted_at.is_(None),
        )
        return db.execute(stmt).scalar_one_or_none()

    def get_by_id(
        self, db: Session, recommendation_id: UUID, user_id: UUID
    ) -> JobRecommendation | None:
        """Return the user's live recommendation with this id, or None."""
        stmt = select(JobRecommendation).where(
            JobRecommendation.id == recommendation_id,
            JobRecommendation.user_id == user_id,
            JobRecommendation.deleted_at.is_(None),
        )
        return db.execute(stmt).scalar_one_or_none()

    def list_by_profile(
        self,
        db: Session,
        resume_profile_id: UUID,
        user_id: UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> list[JobRecommendation]:
        """Return the user's live recommendations for a profile, best first."""
        stmt = (
            select(JobRecommendation)
            .where(
                JobRecommendation.resume_profile_id == resume_profile_id,
                JobRecommendation.user_id == user_id,
                JobRecommendation.deleted_at.is_(None),
            )
            .order_by(
                JobRecommendation.final_score.desc(),
                JobRecommendation.created_at.desc(),
            )
            .offset(skip)
            .limit(limit)
        )
        return list(db.execute(stmt).scalars().all())

    def soft_delete(
        self, db: Session, recommendation: JobRecommendation
    ) -> JobRecommendation:
        """Mark the recommendation deleted by stamping deleted_at (UTC)."""
        recommendation.deleted_at = datetime.now(UTC)
        db.commit()
        db.refresh(recommendation)
        return recommendation
