# schemas package.
# Pydantic models describing the API transport contract (request/response DTOs).
# One module per resource (e.g. user.py, resume.py). These define validation and
# serialization boundaries and are intentionally decoupled from ORM models.

from app.schemas.application import (
    ApplicationCreate,
    ApplicationFilter,
    ApplicationRead,
    ApplicationStatusUpdate,
    ApplicationUpdate,
)
from app.schemas.auth import Token, TokenPayload
from app.schemas.company import (
    CompanyBase,
    CompanyCreate,
    CompanyRead,
    CompanyUpdate,
)
from app.schemas.connector_run import ConnectorRunRead
from app.schemas.cover_letter import (
    CoverLetterAIOutput,
    CoverLetterCreate,
    CoverLetterRead,
)
from app.schemas.ingestion import RawJobInput
from app.schemas.job import JobBase, JobCreate, JobFilter, JobRead, JobUpdate
from app.schemas.job_match import JobMatchRead
from app.schemas.job_recommendation import JobRecommendationRead
from app.schemas.job_alert import (
    JobAlertBase,
    JobAlertCreate,
    JobAlertRead,
    JobAlertUpdate,
)
from app.schemas.resume import ResumeRead, ResumeTextRead
from app.schemas.resume_profile import (
    ResumeProfileAIOutput,
    ResumeProfileParseResponse,
    ResumeProfileRead,
)
from app.schemas.saved_search import (
    SavedSearchBase,
    SavedSearchCreate,
    SavedSearchRead,
    SavedSearchUpdate,
)
from app.schemas.semantic_search import (
    EmbeddingRebuildResponse,
    JobEmbeddingRead,
    SemanticSearchRequest,
    SemanticSearchResult,
)
from app.schemas.user import UserBase, UserCreate, UserRead, UserUpdate

__all__ = [
    "UserBase",
    "ApplicationCreate",
    "ApplicationUpdate",
    "ApplicationStatusUpdate",
    "ApplicationRead",
    "ApplicationFilter",
    "UserCreate",
    "UserUpdate",
    "UserRead",
    "Token",
    "TokenPayload",
    "CompanyBase",
    "CompanyCreate",
    "CompanyUpdate",
    "CompanyRead",
    "JobBase",
    "JobCreate",
    "JobUpdate",
    "JobRead",
    "JobFilter",
    "JobMatchRead",
    "JobRecommendationRead",
    "RawJobInput",
    "SavedSearchBase",
    "SavedSearchCreate",
    "SavedSearchUpdate",
    "SavedSearchRead",
    "JobAlertBase",
    "JobAlertCreate",
    "JobAlertUpdate",
    "JobAlertRead",
    "ConnectorRunRead",
    "CoverLetterCreate",
    "CoverLetterRead",
    "CoverLetterAIOutput",
    "JobEmbeddingRead",
    "SemanticSearchRequest",
    "SemanticSearchResult",
    "EmbeddingRebuildResponse",
    "ResumeRead",
    "ResumeTextRead",
    "ResumeProfileRead",
    "ResumeProfileParseResponse",
    "ResumeProfileAIOutput",
]
