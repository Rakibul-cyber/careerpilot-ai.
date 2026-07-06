# models package.
# SQLAlchemy ORM entities that map to PostgreSQL tables (the persistence layer).
# One module per aggregate/entity (e.g. user.py, resume.py, job_application.py).
# These represent database state only — kept separate from Pydantic schemas so the
# storage model and the API contract can evolve independently.

from app.models.base import BaseModel
from app.models.company import Company
from app.models.connector_run import ConnectorRun, ConnectorRunStatus
from app.models.cover_letter import CoverLetter, CoverLetterStatus
from app.models.job import Job, JobEmbeddingStatus, JobSource, JobStatus
from app.models.job_alert import JobAlert, JobAlertFrequency
from app.models.job_match import JobMatch
from app.models.job_recommendation import JobRecommendation
from app.models.resume import Resume, ResumeExtractionStatus, ResumeFileType
from app.models.resume_profile import ResumeParseStatus, ResumeProfile
from app.models.saved_search import SavedSearch
from app.models.user import User, UserRole
from app.models.application import Application, ApplicationSource, ApplicationStatus

__all__ = [
    "BaseModel",
    "Application",
    "ApplicationStatus",
    "ApplicationSource",
    "User",
    "UserRole",
    "Company",
    "Job",
    "JobSource",
    "JobStatus",
    "JobEmbeddingStatus",
    "SavedSearch",
    "JobAlert",
    "JobAlertFrequency",
    "JobMatch",
    "JobRecommendation",
    "ConnectorRun",
    "ConnectorRunStatus",
    "CoverLetter",
    "CoverLetterStatus",
    "Resume",
    "ResumeFileType",
    "ResumeExtractionStatus",
    "ResumeProfile",
    "ResumeParseStatus",
]
