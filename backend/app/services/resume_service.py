# Business-logic layer for the Resume aggregate.
#
# Owns upload validation (type + size), local file storage, resume-row creation,
# text extraction, and the "primary resume" rule. All operations are scoped to
# a user. Physical files are NOT deleted on soft delete (kept for now).

import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.models.resume import (
    Resume,
    ResumeExtractionStatus,
    ResumeFileType,
)
from app.repositories.resume_repository import ResumeRepository
from app.services.resume_text_extraction_service import (
    ResumeTextExtractionService,
)

logger = get_logger(__name__)

# Upload extension -> stored file type.
_EXTENSION_TO_TYPE = {
    "pdf": ResumeFileType.PDF,
    "docx": ResumeFileType.DOCX,
}

# Canonical MIME type per file type (derived from our validated type, not from
# the client-supplied Content-Type header, which can't be trusted).
_TYPE_TO_MIME = {
    ResumeFileType.PDF: "application/pdf",
    ResumeFileType.DOCX: (
        "application/vnd.openxmlformats-officedocument"
        ".wordprocessingml.document"
    ),
}


class ResumeValidationError(Exception):
    """Base class for user-correctable upload problems."""


class UnsupportedFileTypeError(ResumeValidationError):
    """Raised for a non-PDF/DOCX upload (-> HTTP 400)."""


class FileTooLargeError(ResumeValidationError):
    """Raised when the file exceeds the configured size limit (-> HTTP 413)."""


class ResumeService:
    def __init__(
        self,
        resume_repository: ResumeRepository | None = None,
        text_extraction_service: ResumeTextExtractionService | None = None,
    ) -> None:
        self.resume_repository = resume_repository or ResumeRepository()
        self.text_extraction_service = (
            text_extraction_service or ResumeTextExtractionService()
        )

    def upload_resume(
        self, db: Session, user_id: uuid.UUID, upload_file, is_primary: bool = False
    ) -> Resume:
        """Validate, store, persist, and extract text for one uploaded resume."""
        file_type = self._resolve_file_type(upload_file.filename)
        content = upload_file.file.read()

        max_bytes = settings.MAX_RESUME_UPLOAD_MB * 1024 * 1024
        if len(content) > max_bytes:
            raise FileTooLargeError(
                f"Resume exceeds the {settings.MAX_RESUME_UPLOAD_MB} MB limit"
            )

        stored_filename = f"{uuid.uuid4()}.{file_type.value}"
        file_path = self._store_file(user_id, stored_filename, content)

        # First resume becomes primary automatically; explicit request wins too.
        has_existing = bool(
            self.resume_repository.list_by_user(db, user_id, limit=1)
        )
        make_primary = is_primary or not has_existing
        if make_primary:
            self.resume_repository.clear_primary_for_user(db, user_id)

        resume = Resume(
            user_id=user_id,
            original_filename=upload_file.filename,
            stored_filename=stored_filename,
            file_path=str(file_path),
            file_type=file_type,
            mime_type=_TYPE_TO_MIME[file_type],
            file_size_bytes=len(content),
            is_primary=make_primary,
            status=ResumeExtractionStatus.PENDING,
        )
        resume = self.resume_repository.create(db, resume)
        logger.info(
            "Resume uploaded resume_id=%s user_id=%s type=%s size=%d primary=%s",
            resume.id,
            user_id,
            file_type.value,
            len(content),
            make_primary,
        )

        # Extraction failure must not lose the upload — keep the row, mark it
        # FAILED with the reason so a future retry job can find and re-run it.
        try:
            text = self.text_extraction_service.extract_text(
                str(file_path), file_type
            )
            resume.extracted_text = text
            resume.status = ResumeExtractionStatus.COMPLETED
            resume.extraction_error = None
            resume.processed_at = datetime.now(timezone.utc)
            resume = self.resume_repository.update(db, resume)
            logger.info(
                "Resume text extracted resume_id=%s chars=%d",
                resume.id,
                len(text),
            )
        except Exception as exc:
            resume.status = ResumeExtractionStatus.FAILED
            resume.extraction_error = f"{type(exc).__name__}: {exc}"
            resume = self.resume_repository.update(db, resume)
            logger.exception(
                "Resume text extraction failed resume_id=%s", resume.id
            )

        return resume

    def list_resumes(
        self, db: Session, user_id: uuid.UUID, skip: int = 0, limit: int = 50
    ) -> list[Resume]:
        return self.resume_repository.list_by_user(
            db, user_id, skip=skip, limit=limit
        )

    def get_resume(
        self, db: Session, user_id: uuid.UUID, resume_id: uuid.UUID
    ) -> Resume | None:
        return self.resume_repository.get_by_id(db, resume_id, user_id)

    def get_resume_text(
        self, db: Session, user_id: uuid.UUID, resume_id: uuid.UUID
    ) -> Resume | None:
        return self.resume_repository.get_by_id(db, resume_id, user_id)

    def set_primary_resume(
        self, db: Session, user_id: uuid.UUID, resume_id: uuid.UUID
    ) -> Resume | None:
        resume = self.resume_repository.get_by_id(db, resume_id, user_id)
        if resume is None:
            return None
        self.resume_repository.clear_primary_for_user(db, user_id)
        resume.is_primary = True
        return self.resume_repository.update(db, resume)

    def delete_resume(
        self, db: Session, user_id: uuid.UUID, resume_id: uuid.UUID
    ) -> Resume | None:
        resume = self.resume_repository.get_by_id(db, resume_id, user_id)
        if resume is None:
            return None
        # Soft delete only — the physical file is intentionally left in place.
        return self.resume_repository.soft_delete(db, resume)

    def _resolve_file_type(self, filename: str | None) -> ResumeFileType:
        extension = ""
        if filename:
            extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        file_type = _EXTENSION_TO_TYPE.get(extension)
        if file_type is None:
            raise UnsupportedFileTypeError(
                "Only PDF and DOCX resumes are supported"
            )
        return file_type

    def _store_file(
        self, user_id: uuid.UUID, stored_filename: str, content: bytes
    ) -> Path:
        directory = Path(settings.UPLOAD_DIR) / "resumes" / str(user_id)
        directory.mkdir(parents=True, exist_ok=True)
        file_path = directory / stored_filename
        file_path.write_bytes(content)
        return file_path
