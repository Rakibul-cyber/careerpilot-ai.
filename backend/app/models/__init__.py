# models package.
# SQLAlchemy ORM entities that map to PostgreSQL tables (the persistence layer).
# One module per aggregate/entity (e.g. user.py, resume.py, job_application.py).
# These represent database state only — kept separate from Pydantic schemas so the
# storage model and the API contract can evolve independently.

from app.models.base import BaseModel
from app.models.company import Company
from app.models.connector_run import ConnectorRun, ConnectorRunStatus
from app.models.job import Job, JobSource, JobStatus
from app.models.job_alert import JobAlert, JobAlertFrequency
from app.models.job_match import JobMatch
from app.models.resume import Resume, ResumeExtractionStatus, ResumeFileType
from app.models.resume_profile import ResumeParseStatus, ResumeProfile
from app.models.saved_search import SavedSearch
from app.models.user import User, UserRole

__all__ = [
    "BaseModel",
    "User",
    "UserRole",
    "Company",
    "Job",
    "JobSource",
    "JobStatus",
    "SavedSearch",
    "JobAlert",
    "JobAlertFrequency",
    "JobMatch",
    "ConnectorRun",
    "ConnectorRunStatus",
    "Resume",
    "ResumeFileType",
    "ResumeExtractionStatus",
    "ResumeProfile",
    "ResumeParseStatus",
]
