# Read-only analytics use cases for dashboard endpoints.

from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.repositories.analytics_repository import (
    APPLICATION_INTERVIEW_STATUSES,
    APPLICATION_OFFER_STATUSES,
    APPLICATION_RESPONSE_STATUSES,
    AnalyticsRepository,
)
from app.models.application import ApplicationStatus
from app.schemas.analytics import (
    AIUsageAnalytics,
    AnalyticsOverview,
    ApplicationAnalytics,
    CountBucket,
    MatchAnalytics,
    MissingSkillMetric,
    TimeCountBucket,
)


class AnalyticsService:
    def __init__(
        self, analytics_repository: AnalyticsRepository | None = None
    ) -> None:
        self.analytics_repository = analytics_repository or AnalyticsRepository()

    def overview(
        self,
        db: Session,
        user_id: UUID,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 5,
    ) -> AnalyticsOverview:
        total = self.analytics_repository.application_count(
            db, user_id, start_date, end_date
        )
        match_averages = self.analytics_repository.average_match_scores(
            db, user_id, start_date, end_date
        )
        return AnalyticsOverview(
            total_applications=total,
            applications_by_status=self._count_buckets(
                self.analytics_repository.application_counts_by_status(
                    db, user_id, start_date, end_date
                )
            ),
            applications_by_source=self._count_buckets(
                self.analytics_repository.application_counts_by_source(
                    db, user_id, start_date, end_date
                )
            ),
            active_applications=(
                self.analytics_repository.active_application_count(
                    db, user_id, start_date, end_date
                )
            ),
            offers=self.analytics_repository.status_group_count(
                db,
                user_id,
                APPLICATION_OFFER_STATUSES,
                start_date,
                end_date,
            ),
            rejections=self.analytics_repository.status_group_count(
                db,
                user_id,
                {ApplicationStatus.REJECTED},
                start_date,
                end_date,
            ),
            interviews=self.analytics_repository.status_group_count(
                db,
                user_id,
                APPLICATION_INTERVIEW_STATUSES,
                start_date,
                end_date,
            ),
            upcoming_followups=(
                self.analytics_repository.upcoming_followup_count(db, user_id)
            ),
            average_match_score=match_averages["overall"],
            top_recommended_jobs=(
                self.analytics_repository.top_recommended_jobs(
                    db, user_id, limit, start_date, end_date
                )
            ),
            recent_activity=self.analytics_repository.recent_activity(
                db, user_id, limit, start_date, end_date
            ),
        )

    def applications(
        self,
        db: Session,
        user_id: UUID,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> ApplicationAnalytics:
        total = self.analytics_repository.application_count(
            db, user_id, start_date, end_date
        )
        responses = self.analytics_repository.status_group_count(
            db,
            user_id,
            APPLICATION_RESPONSE_STATUSES,
            start_date,
            end_date,
        )
        offers = self.analytics_repository.status_group_count(
            db,
            user_id,
            APPLICATION_OFFER_STATUSES,
            start_date,
            end_date,
        )
        rejections = self.analytics_repository.status_group_count(
            db, user_id, {ApplicationStatus.REJECTED}, start_date, end_date
        )
        interviews = self.analytics_repository.status_group_count(
            db, user_id, APPLICATION_INTERVIEW_STATUSES, start_date, end_date
        )
        return ApplicationAnalytics(
            status_counts=self._count_buckets(
                self.analytics_repository.application_counts_by_status(
                    db, user_id, start_date, end_date
                )
            ),
            source_counts=self._count_buckets(
                self.analytics_repository.application_counts_by_source(
                    db, user_id, start_date, end_date
                )
            ),
            applications_over_time=[
                TimeCountBucket(date=day, count=count)
                for day, count in self.analytics_repository.applications_over_time(
                    db, user_id, start_date, end_date
                )
            ],
            response_rate=self._rate(responses, total),
            offer_rate=self._rate(offers, total),
            rejection_rate=self._rate(rejections, total),
            interview_rate=self._rate(interviews, total),
            follow_up_due_count=self.analytics_repository.due_followup_count(
                db, user_id
            ),
        )

    def matches(
        self,
        db: Session,
        user_id: UUID,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 10,
    ) -> MatchAnalytics:
        averages = self.analytics_repository.average_match_scores(
            db, user_id, start_date, end_date
        )
        return MatchAnalytics(
            average_overall_score=averages["overall"],
            average_skill_score=averages["skill"],
            average_title_score=averages["title"],
            average_location_score=averages["location"],
            average_experience_score=averages["experience"],
            best_matches=self.analytics_repository.ranked_matches(
                db, user_id, descending=True, limit=limit,
                start_date=start_date, end_date=end_date,
            ),
            weak_matches=self.analytics_repository.ranked_matches(
                db, user_id, descending=False, limit=limit,
                start_date=start_date, end_date=end_date,
            ),
            common_missing_skills=[
                MissingSkillMetric(skill=skill, count=count)
                for skill, count in self.analytics_repository.common_missing_skills(
                    db, user_id, limit, start_date, end_date
                )
            ],
        )

    def ai_usage(
        self,
        db: Session,
        user_id: UUID,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> AIUsageAnalytics:
        return AIUsageAnalytics(
            **self.analytics_repository.ai_usage_counts(
                db, user_id, start_date, end_date
            )
        )

    @staticmethod
    def _count_buckets(rows: list[tuple[str, int]]) -> list[CountBucket]:
        return [CountBucket(key=key, count=count) for key, count in rows]

    @staticmethod
    def _rate(numerator: int, denominator: int) -> float:
        if denominator <= 0:
            return 0.0
        return round(numerator / denominator, 4)
