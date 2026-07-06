# repositories package.
# Data-access layer. Wraps all persistence operations (CRUD/queries) behind a
# stable interface so services never touch SQLAlchemy directly. This keeps the
# storage engine swappable and makes the business layer trivially unit-testable.

from app.repositories.application_repository import ApplicationRepository
from app.repositories.analytics_repository import AnalyticsRepository
from app.repositories.company_repository import CompanyRepository
from app.repositories.connector_run_repository import ConnectorRunRepository
from app.repositories.cover_letter_repository import CoverLetterRepository
from app.repositories.job_alert_repository import JobAlertRepository
from app.repositories.job_embedding_repository import JobEmbeddingRepository
from app.repositories.job_match_repository import JobMatchRepository
from app.repositories.job_recommendation_repository import (
    JobRecommendationRepository,
)
from app.repositories.interview_preparation_repository import (
    InterviewPreparationRepository,
)
from app.repositories.job_repository import JobRepository
from app.repositories.resume_profile_repository import (
    ResumeProfileRepository,
)
from app.repositories.resume_repository import ResumeRepository
from app.repositories.saved_search_repository import SavedSearchRepository
from app.repositories.user_repository import UserRepository

__all__ = [
    "UserRepository",
    "ApplicationRepository",
    "AnalyticsRepository",
    "CompanyRepository",
    "JobRepository",
    "SavedSearchRepository",
    "JobAlertRepository",
    "ConnectorRunRepository",
    "ResumeRepository",
    "ResumeProfileRepository",
    "JobMatchRepository",
    "CoverLetterRepository",
    "JobEmbeddingRepository",
    "JobRecommendationRepository",
    "InterviewPreparationRepository",
]
