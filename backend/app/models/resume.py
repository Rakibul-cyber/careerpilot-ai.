# Resume entity — an uploaded resume file plus its extracted text.
#
# Files are stored on local disk (file_path); this row holds the metadata and
# the deterministically-extracted text. One resume per user may be primary.

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import BaseModel
from app.models.user import User  # noqa: F401  (registers "User" mapper)


class ResumeFileType(str, enum.Enum):
    PDF = "pdf"
    DOCX = "docx"


class ResumeExtractionStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Resume(BaseModel, Base):
    __tablename__ = "resumes"

    # Owning user; cascade so a user's resumes are removed with the user.
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Filename as uploaded by the user (display only).
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)

    # Unique on-disk filename (UUID-based) — the storage key.
    stored_filename: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )

    # Absolute/relative path to the stored file (not exposed in the API).
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)

    file_type: Mapped[ResumeFileType] = mapped_column(
        Enum(
            ResumeFileType,
            name="resume_file_type",
            values_callable=lambda enum_cls: [m.value for m in enum_cls],
        ),
        nullable=False,
        index=True,
    )
    # Canonical MIME type (e.g. application/pdf), derived from the validated
    # file_type — distinct from the extension enum above.
    mime_type: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)

    # Deterministically-extracted text; NULL until processed (or on failure).
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Explicit extraction lifecycle (pending -> completed/failed). Indexed so a
    # future retry job can find pending/failed rows cheaply.
    status: Mapped[ResumeExtractionStatus] = mapped_column(
        Enum(
            ResumeExtractionStatus,
            name="resume_extraction_status",
            values_callable=lambda enum_cls: [m.value for m in enum_cls],
        ),
        default=ResumeExtractionStatus.PENDING,
        server_default=ResumeExtractionStatus.PENDING.value,
        nullable=False,
        index=True,
    )
    # Failure reason when status == FAILED; NULL otherwise.
    extraction_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )

    # When text extraction completed successfully.
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user = relationship("User")
