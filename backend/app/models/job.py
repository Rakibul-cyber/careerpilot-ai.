# Job entity — a normalized job listing tied to a Company.
#
# Dedup strategy (v1): a unique (source, external_id) pair prevents re-ingesting
# the same listing from the same source. external_id stays nullable so manually
# entered jobs (no external id) are allowed; NULLs are not deduped by that
# constraint. Smarter dedup (normalized_title + company + location) comes later.

import enum
import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import BaseModel
from app.models.company import Company  # noqa: F401  (registers "Company" mapper)

# Embedding dimension. Fixed to the chosen model (OpenAI text-embedding-3-small
# -> 1536). Must stay in sync with settings.EMBEDDING_DIMENSIONS and the
# migration; changing it requires a re-embed + migration.
JOB_EMBEDDING_DIM = 1536


class JobSource(str, enum.Enum):
    LINKEDIN = "linkedin"
    INDEED = "indeed"
    STEPSTONE = "stepstone"
    COMPANY_WEBSITE = "company_website"
    MANUAL = "manual"
    OTHER = "other"


class JobStatus(str, enum.Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    DUPLICATE = "duplicate"
    ARCHIVED = "archived"


class JobEmbeddingStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class Job(BaseModel, Base):
    __tablename__ = "jobs"
    __table_args__ = (
        UniqueConstraint("source", "external_id", name="uq_jobs_source_external_id"),
        # GIN trigram indexes backing the ILIKE '%...%' matches in
        # JobRepository.search (created via migration 8c18594ccbc3).
        Index(
            "ix_jobs_normalized_title_trgm",
            "normalized_title",
            postgresql_using="gin",
            postgresql_ops={"normalized_title": "gin_trgm_ops"},
        ),
        Index(
            "ix_jobs_description_trgm",
            "description",
            postgresql_using="gin",
            postgresql_ops={"description": "gin_trgm_ops"},
        ),
        Index(
            "ix_jobs_requirements_trgm",
            "requirements",
            postgresql_using="gin",
            postgresql_ops={"requirements": "gin_trgm_ops"},
        ),
        Index(
            "ix_jobs_location_trgm",
            "location",
            postgresql_using="gin",
            postgresql_ops={"location": "gin_trgm_ops"},
        ),
        # Full-text search index over the trigger-maintained search_vector
        # (created via migration a3d134ee3d15).
        Index(
            "ix_jobs_search_vector_gin",
            "search_vector",
            postgresql_using="gin",
        ),
        # HNSW index over the embedding for cosine-distance semantic search
        # (created via migration a1c47f9e2d38). A single, simple index — no
        # tuning beyond defaults.
        Index(
            "ix_jobs_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    normalized_title: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True
    )

    # Owning company; RESTRICT so a company can't be deleted while jobs exist.
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    location: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    # e.g. onsite, hybrid, remote
    remote_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # e.g. full_time, part_time, working_student, internship
    employment_type: Mapped[str | None] = mapped_column(String(50), nullable=True)

    source: Mapped[JobSource] = mapped_column(
        Enum(
            JobSource,
            name="job_source",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        default=JobSource.OTHER,
        server_default=JobSource.OTHER.value,
        nullable=False,
        index=True,
    )
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    external_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )

    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    requirements: Mapped[str | None] = mapped_column(Text, nullable=True)

    salary_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)

    status: Mapped[JobStatus] = mapped_column(
        Enum(
            JobStatus,
            name="job_status",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        default=JobStatus.ACTIVE,
        server_default=JobStatus.ACTIVE.value,
        nullable=False,
        index=True,
    )

    posted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Full-text search vector, maintained entirely by a DB trigger — never set
    # from application code, and never exposed in API schemas.
    search_vector: Mapped[str | None] = mapped_column(TSVECTOR, nullable=True)

    # --- Semantic search (M31) ---
    # Vector embedding of the normalized job text; NULL until embedded. Never
    # exposed in API schemas (1536 floats).
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(JOB_EMBEDDING_DIM), nullable=True
    )
    # Which embedding model produced `embedding` (e.g. text-embedding-3-small).
    embedding_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    embedding_status: Mapped[JobEmbeddingStatus] = mapped_column(
        Enum(
            JobEmbeddingStatus,
            name="job_embedding_status",
            values_callable=lambda enum_cls: [m.value for m in enum_cls],
        ),
        default=JobEmbeddingStatus.PENDING,
        server_default=JobEmbeddingStatus.PENDING.value,
        nullable=False,
        index=True,
    )
    # Failure reason when embedding_status == FAILED; NULL otherwise.
    embedding_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    embedded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    company = relationship("Company")
