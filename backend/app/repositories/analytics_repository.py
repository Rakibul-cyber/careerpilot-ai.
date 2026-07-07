# Read-only aggregate queries for the analytics dashboard (M35).

from collections import Counter
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, literal, select, union
from sqlalchemy.orm import Session

from app.models.application import Application, ApplicationStatus
from app.models.company import Company
from app.models.cover_letter import CoverLetter, CoverLetterStatus
from app.models.interview_preparation import (
    InterviewPreparation,
    InterviewPreparationStatus,
)
from app.models.job import Job, JobEmbeddingStatus
from app.models.job_match import JobMatch
from app.models.job_recommendation import JobRecommendation
from app.models.resume_profile import ResumeParseStatus, ResumeProfile

_TERMINAL_STATUSES = {
    ApplicationStatus.ACCEPTED,
    ApplicationStatus.REJECTED,
    ApplicationStatus.WITHDRAWN,
}
_INTERVIEW_STATUSES = {
    ApplicationStatus.PHONE_SCREEN,
    ApplicationStatus.TECHNICAL_INTERVIEW,
    ApplicationStatus.HR_INTERVIEW,
    ApplicationStatus.FINAL_INTERVIEW,
}
_RESPONSE_STATUSES = _INTERVIEW_STATUSES | {
    ApplicationStatus.VIEWED,
    ApplicationStatus.OFFER,
    ApplicationStatus.ACCEPTED,
    ApplicationStatus.REJECTED,
}


class AnalyticsRepository:
    """Read-only analytics queries scoped to one user."""

    def application_count(
        self,
        db: Session,
        user_id: UUID,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(Application)
            .where(*self._application_conditions(user_id, start_date, end_date))
        )
        return int(db.execute(stmt).scalar_one() or 0)

    def application_counts_by_status(
        self, db: Session, user_id: UUID, start_date=None, end_date=None
    ) -> list[tuple[str, int]]:
        stmt = (
            select(Application.status, func.count())
            .where(*self._application_conditions(user_id, start_date, end_date))
            .group_by(Application.status)
        )
        return [(status.value, int(count)) for status, count in db.execute(stmt)]

    def application_counts_by_source(
        self, db: Session, user_id: UUID, start_date=None, end_date=None
    ) -> list[tuple[str, int]]:
        stmt = (
            select(Application.source, func.count())
            .where(*self._application_conditions(user_id, start_date, end_date))
            .group_by(Application.source)
        )
        return [(source.value, int(count)) for source, count in db.execute(stmt)]

    def active_application_count(
        self, db: Session, user_id: UUID, start_date=None, end_date=None
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(Application)
            .where(
                *self._application_conditions(user_id, start_date, end_date),
                Application.status.not_in(_TERMINAL_STATUSES),
            )
        )
        return int(db.execute(stmt).scalar_one() or 0)

    def status_group_count(
        self, db: Session, user_id: UUID, statuses, start_date=None, end_date=None
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(Application)
            .where(
                *self._application_conditions(user_id, start_date, end_date),
                Application.status.in_(statuses),
            )
        )
        return int(db.execute(stmt).scalar_one() or 0)

    def upcoming_followup_count(self, db: Session, user_id: UUID) -> int:
        now = datetime.now(UTC)
        stmt = (
            select(func.count())
            .select_from(Application)
            .where(
                Application.user_id == user_id,
                Application.deleted_at.is_(None),
                Application.follow_up_date.is_not(None),
                Application.follow_up_date >= now,
                Application.status.not_in(_TERMINAL_STATUSES),
            )
        )
        return int(db.execute(stmt).scalar_one() or 0)

    def due_followup_count(self, db: Session, user_id: UUID) -> int:
        now = datetime.now(UTC)
        stmt = (
            select(func.count())
            .select_from(Application)
            .where(
                Application.user_id == user_id,
                Application.deleted_at.is_(None),
                Application.follow_up_date.is_not(None),
                Application.follow_up_date <= now,
                Application.status.not_in(_TERMINAL_STATUSES),
            )
        )
        return int(db.execute(stmt).scalar_one() or 0)

    def applications_over_time(
        self, db: Session, user_id: UUID, start_date=None, end_date=None
    ) -> list[tuple]:
        day = func.date(Application.created_at)
        stmt = (
            select(day.label("day"), func.count())
            .where(*self._application_conditions(user_id, start_date, end_date))
            .group_by(day)
            .order_by(day.asc())
        )
        return [(row[0], int(row[1])) for row in db.execute(stmt)]

    def average_match_scores(
        self, db: Session, user_id: UUID, start_date=None, end_date=None
    ) -> dict:
        stmt = select(
            func.avg(JobMatch.overall_score),
            func.avg(JobMatch.skill_score),
            func.avg(JobMatch.title_score),
            func.avg(JobMatch.location_score),
            func.avg(JobMatch.experience_score),
        ).where(*self._match_conditions(user_id, start_date, end_date))
        row = db.execute(stmt).one()
        return {
            "overall": self._round_or_none(row[0]),
            "skill": self._round_or_none(row[1]),
            "title": self._round_or_none(row[2]),
            "location": self._round_or_none(row[3]),
            "experience": self._round_or_none(row[4]),
        }

    def ranked_matches(
        self,
        db: Session,
        user_id: UUID,
        descending: bool,
        limit: int,
        start_date=None,
        end_date=None,
    ) -> list[dict]:
        order = (
            JobMatch.overall_score.desc()
            if descending
            else JobMatch.overall_score.asc()
        )
        stmt = (
            select(
                Job.id,
                Job.title,
                Company.name,
                JobMatch.overall_score,
                JobMatch.skill_score,
                JobMatch.title_score,
                JobMatch.location_score,
                JobMatch.experience_score,
            )
            .join(Job, JobMatch.job_id == Job.id)
            .join(Company, Job.company_id == Company.id)
            .where(
                *self._match_conditions(user_id, start_date, end_date),
                Job.deleted_at.is_(None),
            )
            .order_by(order)
            .limit(limit)
        )
        return [
            {
                "job_id": row[0],
                "title": row[1],
                "company": row[2],
                "overall_score": float(row[3]),
                "skill_score": float(row[4]),
                "title_score": float(row[5]),
                "location_score": float(row[6]),
                "experience_score": float(row[7]),
            }
            for row in db.execute(stmt)
        ]

    def common_missing_skills(
        self, db: Session, user_id: UUID, limit: int, start_date=None, end_date=None
    ) -> list[tuple[str, int]]:
        stmt = select(JobMatch.missing_skills).where(
            *self._match_conditions(user_id, start_date, end_date),
            JobMatch.missing_skills.is_not(None),
        )
        counter: Counter[str] = Counter()
        for (skills,) in db.execute(stmt):
            for skill in skills or []:
                if isinstance(skill, str) and skill.strip():
                    counter[skill.strip()] += 1
        return counter.most_common(limit)

    def top_recommended_jobs(
        self, db: Session, user_id: UUID, limit: int, start_date=None, end_date=None
    ) -> list[dict]:
        stmt = (
            select(
                Job.id,
                Job.title,
                Company.name,
                JobRecommendation.final_score,
                JobRecommendation.semantic_score,
                JobRecommendation.match_score,
            )
            .join(Job, JobRecommendation.job_id == Job.id)
            .join(Company, Job.company_id == Company.id)
            .where(
                *self._recommendation_conditions(user_id, start_date, end_date),
                Job.deleted_at.is_(None),
            )
            .order_by(JobRecommendation.final_score.desc())
            .limit(limit)
        )
        return [
            {
                "job_id": row[0],
                "title": row[1],
                "company": row[2],
                "final_score": float(row[3]),
                "semantic_score": float(row[4]),
                "match_score": float(row[5]),
            }
            for row in db.execute(stmt)
        ]

    def recent_activity(
        self, db: Session, user_id: UUID, limit: int, start_date=None, end_date=None
    ) -> list[dict]:
        rows: list[dict] = []
        rows.extend(
            self._activity_rows(
                db,
                "application",
                select(Application.id, Application.updated_at, Application.status)
                .where(*self._application_conditions(user_id, start_date, end_date))
                .order_by(Application.updated_at.desc())
                .limit(limit),
                lambda status: f"Application {status.value}",
            )
        )
        rows.extend(
            self._activity_rows(
                db,
                "cover_letter",
                select(
                    CoverLetter.id,
                    CoverLetter.updated_at,
                    CoverLetter.generation_status,
                )
                .where(*self._cover_letter_conditions(user_id, start_date, end_date))
                .order_by(CoverLetter.updated_at.desc())
                .limit(limit),
                lambda status: f"Cover letter {status.value}",
            )
        )
        rows.extend(
            self._activity_rows(
                db,
                "interview_preparation",
                select(
                    InterviewPreparation.id,
                    InterviewPreparation.updated_at,
                    InterviewPreparation.generation_status,
                )
                .where(*self._interview_prep_conditions(user_id, start_date, end_date))
                .order_by(InterviewPreparation.updated_at.desc())
                .limit(limit),
                lambda status: f"Interview preparation {status.value}",
            )
        )
        rows.extend(
            self._activity_rows(
                db,
                "recommendation",
                select(
                    JobRecommendation.id,
                    JobRecommendation.updated_at,
                    literal("updated"),
                )
                .where(*self._recommendation_conditions(user_id, start_date, end_date))
                .order_by(JobRecommendation.updated_at.desc())
                .limit(limit),
                lambda status: f"Recommendation {status}",
            )
        )
        rows.sort(key=lambda row: row["occurred_at"], reverse=True)
        return rows[:limit]

    def ai_usage_counts(
        self, db: Session, user_id: UUID, start_date=None, end_date=None
    ) -> dict:
        return {
            "resume_profiles": self._count_model(
                db,
                ResumeProfile,
                self._resume_profile_conditions(user_id, start_date, end_date),
            ),
            "cover_letters": self._count_model(
                db,
                CoverLetter,
                self._cover_letter_conditions(user_id, start_date, end_date),
            ),
            "interview_preparations": self._count_model(
                db,
                InterviewPreparation,
                self._interview_prep_conditions(user_id, start_date, end_date),
            ),
            "job_embeddings": self._job_embedding_count(
                db, user_id, start_date, end_date, JobEmbeddingStatus.COMPLETED
            ),
            "recommendations": self._count_model(
                db,
                JobRecommendation,
                self._recommendation_conditions(user_id, start_date, end_date),
            ),
            "failed_resume_parses": self._count_model(
                db,
                ResumeProfile,
                self._resume_profile_conditions(user_id, start_date, end_date)
                + [ResumeProfile.parse_status == ResumeParseStatus.FAILED],
            ),
            "failed_cover_letters": self._count_model(
                db,
                CoverLetter,
                self._cover_letter_conditions(user_id, start_date, end_date)
                + [CoverLetter.generation_status == CoverLetterStatus.FAILED],
            ),
            "failed_interview_preparations": self._count_model(
                db,
                InterviewPreparation,
                self._interview_prep_conditions(user_id, start_date, end_date)
                + [
                    InterviewPreparation.generation_status
                    == InterviewPreparationStatus.FAILED
                ],
            ),
            "failed_job_embeddings": self._job_embedding_count(
                db, user_id, start_date, end_date, JobEmbeddingStatus.FAILED
            ),
        }

    # --- condition helpers -----------------------------------------------

    @staticmethod
    def _date_conditions(model, start_date, end_date):
        conditions = []
        if start_date is not None:
            conditions.append(model.created_at >= start_date)
        if end_date is not None:
            conditions.append(model.created_at <= end_date)
        return conditions

    def _application_conditions(self, user_id, start_date, end_date):
        return [
            Application.user_id == user_id,
            Application.deleted_at.is_(None),
            *self._date_conditions(Application, start_date, end_date),
        ]

    def _match_conditions(self, user_id, start_date, end_date):
        return [
            JobMatch.user_id == user_id,
            JobMatch.deleted_at.is_(None),
            *self._date_conditions(JobMatch, start_date, end_date),
        ]

    def _recommendation_conditions(self, user_id, start_date, end_date):
        return [
            JobRecommendation.user_id == user_id,
            JobRecommendation.deleted_at.is_(None),
            *self._date_conditions(JobRecommendation, start_date, end_date),
        ]

    def _cover_letter_conditions(self, user_id, start_date, end_date):
        return [
            CoverLetter.user_id == user_id,
            CoverLetter.deleted_at.is_(None),
            *self._date_conditions(CoverLetter, start_date, end_date),
        ]

    def _interview_prep_conditions(self, user_id, start_date, end_date):
        return [
            InterviewPreparation.user_id == user_id,
            InterviewPreparation.deleted_at.is_(None),
            *self._date_conditions(InterviewPreparation, start_date, end_date),
        ]

    def _resume_profile_conditions(self, user_id, start_date, end_date):
        return [
            ResumeProfile.user_id == user_id,
            ResumeProfile.deleted_at.is_(None),
            *self._date_conditions(ResumeProfile, start_date, end_date),
        ]

    def _job_embedding_count(self, db, user_id, start_date, end_date, status):
        job_ids = union(
            select(Application.job_id).where(
                *self._application_conditions(user_id, start_date, end_date)
            ),
            select(JobMatch.job_id).where(
                *self._match_conditions(user_id, start_date, end_date)
            ),
            select(JobRecommendation.job_id).where(
                *self._recommendation_conditions(user_id, start_date, end_date)
            ),
        ).subquery()
        stmt = select(func.count(func.distinct(Job.id))).where(
            Job.id.in_(select(job_ids.c.job_id)),
            Job.deleted_at.is_(None),
            Job.embedding_status == status,
        )
        return int(db.execute(stmt).scalar_one() or 0)

    @staticmethod
    def _count_model(db, model, conditions):
        stmt = select(func.count()).select_from(model).where(*conditions)
        return int(db.execute(stmt).scalar_one() or 0)

    @staticmethod
    def _round_or_none(value):
        if value is None:
            return None
        return round(float(value), 2)

    @staticmethod
    def _activity_rows(db, row_type, stmt, label_fn):
        rows = []
        for row_id, occurred_at, label_value in db.execute(stmt):
            if occurred_at is None:
                continue
            rows.append(
                {
                    "type": row_type,
                    "id": row_id,
                    "occurred_at": occurred_at,
                    "label": label_fn(label_value),
                }
            )
        return rows


APPLICATION_INTERVIEW_STATUSES = _INTERVIEW_STATUSES
APPLICATION_RESPONSE_STATUSES = _RESPONSE_STATUSES
APPLICATION_OFFER_STATUSES = {
    ApplicationStatus.OFFER,
    ApplicationStatus.ACCEPTED,
}
