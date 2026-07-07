# Data-access layer for Application.
#
# Persistence only: no ownership/resource validation and no workflow rules.

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.application import Application
from app.models.company import Company
from app.models.job import Job
from app.schemas.application import ApplicationFilter
from app.utils.normalization import normalize_company_name
from app.utils.search import escape_like

_LIKE_ESCAPE = "\\"


def _ilike_contains(column, text: str):
    return column.ilike(f"%{escape_like(text)}%", escape=_LIKE_ESCAPE)


class ApplicationRepository:
    """Persistence operations for :class:`Application`."""

    def create(self, db: Session, application: Application) -> Application:
        db.add(application)
        db.commit()
        db.refresh(application)
        return application

    def update(self, db: Session, application: Application) -> Application:
        db.commit()
        db.refresh(application)
        return application

    def get_by_id(
        self, db: Session, application_id: UUID, user_id: UUID
    ) -> Application | None:
        stmt = select(Application).where(
            Application.id == application_id,
            Application.user_id == user_id,
            Application.deleted_at.is_(None),
        )
        return db.execute(stmt).scalar_one_or_none()

    def list(
        self,
        db: Session,
        user_id: UUID,
        filters: ApplicationFilter | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Application]:
        filters = filters or ApplicationFilter()
        conditions = [
            Application.user_id == user_id,
            Application.deleted_at.is_(None),
        ]
        stmt = select(Application)

        if filters.status is not None:
            conditions.append(Application.status == filters.status)
        if filters.source is not None:
            conditions.append(Application.source == filters.source)
        if filters.date_from is not None:
            conditions.append(Application.created_at >= filters.date_from)
        if filters.date_to is not None:
            conditions.append(Application.created_at <= filters.date_to)

        if filters.company:
            stmt = stmt.join(Job, Application.job_id == Job.id).join(
                Company, Job.company_id == Company.id
            )
            company_branches = [_ilike_contains(Company.name, filters.company)]
            normalized_company = normalize_company_name(filters.company)
            if normalized_company:
                company_branches.append(
                    _ilike_contains(Company.normalized_name, normalized_company)
                )
            conditions.append(or_(*company_branches))

        stmt = (
            stmt.where(*conditions)
            .order_by(Application.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(db.execute(stmt).scalars().all())

    def soft_delete(self, db: Session, application: Application) -> Application:
        application.deleted_at = datetime.now(UTC)
        db.commit()
        db.refresh(application)
        return application
