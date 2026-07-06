# Pydantic v2 schemas for read-only analytics dashboard responses.

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel


class CountBucket(BaseModel):
    key: str
    count: int


class TimeCountBucket(BaseModel):
    date: date
    count: int


class RecommendedJobMetric(BaseModel):
    job_id: UUID
    title: str
    company: str | None
    final_score: float
    semantic_score: float
    match_score: float


class MatchMetric(BaseModel):
    job_id: UUID
    title: str
    company: str | None
    overall_score: float
    skill_score: float
    title_score: float
    location_score: float
    experience_score: float


class MissingSkillMetric(BaseModel):
    skill: str
    count: int


class ActivityMetric(BaseModel):
    type: str
    id: UUID
    occurred_at: datetime
    label: str


class AnalyticsOverview(BaseModel):
    total_applications: int
    applications_by_status: list[CountBucket]
    applications_by_source: list[CountBucket]
    active_applications: int
    offers: int
    rejections: int
    interviews: int
    upcoming_followups: int
    average_match_score: float | None
    top_recommended_jobs: list[RecommendedJobMetric]
    recent_activity: list[ActivityMetric]


class ApplicationAnalytics(BaseModel):
    status_counts: list[CountBucket]
    source_counts: list[CountBucket]
    applications_over_time: list[TimeCountBucket]
    response_rate: float
    offer_rate: float
    rejection_rate: float
    interview_rate: float
    follow_up_due_count: int


class MatchAnalytics(BaseModel):
    average_overall_score: float | None
    average_skill_score: float | None
    average_title_score: float | None
    average_location_score: float | None
    average_experience_score: float | None
    best_matches: list[MatchMetric]
    weak_matches: list[MatchMetric]
    common_missing_skills: list[MissingSkillMetric]


class AIUsageAnalytics(BaseModel):
    resume_profiles: int
    cover_letters: int
    interview_preparations: int
    job_embeddings: int
    recommendations: int
    failed_resume_parses: int
    failed_cover_letters: int
    failed_interview_preparations: int
    failed_job_embeddings: int
