# Deterministic resume text extraction (no LLM, no OCR).
#
# Pulls plain text out of PDF/DOCX files using pypdf / python-docx and collapses
# excessive whitespace. Raises ValueError for unsupported types.

import re

from docx import Document
from pypdf import PdfReader

from app.models.resume import ResumeFileType

# Collapse runs of blank lines / spaces produced by page and paragraph breaks.
_MULTI_BLANK_LINES = re.compile(r"\n{3,}")
_TRAILING_SPACES = re.compile(r"[ \t]+\n")
_MULTI_SPACES = re.compile(r"[ \t]{2,}")


class ResumeTextExtractionService:
    def extract_text(self, file_path: str, file_type: ResumeFileType) -> str:
        """Extract text from a resume file, normalizing whitespace."""
        if file_type == ResumeFileType.PDF:
            raw = self._extract_pdf(file_path)
        elif file_type == ResumeFileType.DOCX:
            raw = self._extract_docx(file_path)
        else:
            raise ValueError(f"Unsupported resume file type: {file_type}")
        return self._normalize_whitespace(raw)

    def _extract_pdf(self, file_path: str) -> str:
        reader = PdfReader(file_path)
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n".join(pages)

    def _extract_docx(self, file_path: str) -> str:
        document = Document(file_path)
        paragraphs = [p.text for p in document.paragraphs]
        return "\n".join(paragraphs)

    def _normalize_whitespace(self, text: str) -> str:
        # Normalize line endings first (\r\n / \r -> \n).
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = _TRAILING_SPACES.sub("\n", text)
        text = _MULTI_SPACES.sub(" ", text)
        text = _MULTI_BLANK_LINES.sub("\n\n", text)
        return text.strip()
