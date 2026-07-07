# Data-access layer for InterviewPreparation.

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.interview_preparation import InterviewPreparation


class InterviewPreparationRepository:
    """Persistence operations for :class:`InterviewPreparation`."""

    def create(
        self, db: Session, preparation: InterviewPreparation
    ) -> InterviewPreparation:
        db.add(preparation)
        db.commit()
        db.refresh(preparation)
        return preparation

    def update(
        self, db: Session, preparation: InterviewPreparation
    ) -> InterviewPreparation:
        db.commit()
        db.refresh(preparation)
        return preparation

    def get_by_application(
        self, db: Session, application_id: UUID, user_id: UUID
    ) -> InterviewPreparation | None:
        stmt = select(InterviewPreparation).where(
            InterviewPreparation.application_id == application_id,
            InterviewPreparation.user_id == user_id,
            InterviewPreparation.deleted_at.is_(None),
        )
        return db.execute(stmt).scalar_one_or_none()

    def get_by_id(
        self, db: Session, preparation_id: UUID, user_id: UUID
    ) -> InterviewPreparation | None:
        stmt = select(InterviewPreparation).where(
            InterviewPreparation.id == preparation_id,
            InterviewPreparation.user_id == user_id,
            InterviewPreparation.deleted_at.is_(None),
        )
        return db.execute(stmt).scalar_one_or_none()

    def list_by_user(
        self, db: Session, user_id: UUID, skip: int = 0, limit: int = 50
    ) -> list[InterviewPreparation]:
        stmt = (
            select(InterviewPreparation)
            .where(
                InterviewPreparation.user_id == user_id,
                InterviewPreparation.deleted_at.is_(None),
            )
            .order_by(InterviewPreparation.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(db.execute(stmt).scalars().all())

    def soft_delete(
        self, db: Session, preparation: InterviewPreparation
    ) -> InterviewPreparation:
        preparation.deleted_at = datetime.now(UTC)
        db.commit()
        db.refresh(preparation)
        return preparation
