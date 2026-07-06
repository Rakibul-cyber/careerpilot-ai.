# Anthropic-backed implementation of AIResumeParserClient.
#
# Calls the Claude Messages API with a structured-output JSON schema so the
# response is always valid JSON, then returns that raw text for the service to
# validate. The Anthropic SDK is imported lazily and the client is built on
# first use, so importing this module (and booting the app) never requires the
# SDK to be installed or an API key to be present.

from app.core.config import settings
from app.core.logging import get_logger
from app.services.ai.resume_parser_client import (
    AIParserError,
    AIResumeParserClient,
)

logger = get_logger(__name__)

# System prompt: extract, don't invent. The JSON shape is enforced separately
# by the output schema below, so the prompt focuses on extraction fidelity.
_SYSTEM_PROMPT = (
    "You are a precise resume parser. Extract structured information from the "
    "resume text the user provides. Only use information present in the text — "
    "never invent, infer, or embellish. If a field is absent, leave it null or "
    "as an empty list. Preserve the wording of the resume where practical."
)

# JSON schema handed to output_config.format so the model returns valid JSON
# matching ResumeProfileAIOutput. All properties are required with nullable
# scalars, per structured-output rules.
_RESUME_PROFILE_SCHEMA = {
    "type": "object",
    "properties": {
        "full_name": {"type": ["string", "null"]},
        "email": {"type": ["string", "null"]},
        "phone": {"type": ["string", "null"]},
        "location": {"type": ["string", "null"]},
        "summary": {"type": ["string", "null"]},
        "skills": {"type": "array", "items": {"type": "string"}},
        "work_experience": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "company": {"type": ["string", "null"]},
                    "title": {"type": ["string", "null"]},
                    "start_date": {"type": ["string", "null"]},
                    "end_date": {"type": ["string", "null"]},
                    "description": {"type": ["string", "null"]},
                },
                "required": [
                    "company",
                    "title",
                    "start_date",
                    "end_date",
                    "description",
                ],
                "additionalProperties": False,
            },
        },
        "education": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "institution": {"type": ["string", "null"]},
                    "degree": {"type": ["string", "null"]},
                    "field_of_study": {"type": ["string", "null"]},
                    "start_date": {"type": ["string", "null"]},
                    "end_date": {"type": ["string", "null"]},
                },
                "required": [
                    "institution",
                    "degree",
                    "field_of_study",
                    "start_date",
                    "end_date",
                ],
                "additionalProperties": False,
            },
        },
        "projects": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": ["string", "null"]},
                    "description": {"type": ["string", "null"]},
                    "technologies": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": ["name", "description", "technologies"],
                "additionalProperties": False,
            },
        },
        "certifications": {"type": "array", "items": {"type": "string"}},
        "languages": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "full_name",
        "email",
        "phone",
        "location",
        "summary",
        "skills",
        "work_experience",
        "education",
        "projects",
        "certifications",
        "languages",
    ],
    "additionalProperties": False,
}


class AnthropicResumeParserClient(AIResumeParserClient):
    """Parses resume text into raw JSON via the Anthropic Claude API."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        max_tokens: int | None = None,
    ) -> None:
        self._api_key = api_key or settings.ANTHROPIC_API_KEY
        self._model = model or settings.ANTHROPIC_MODEL
        self._max_tokens = max_tokens or settings.AI_PARSER_MAX_TOKENS
        self._client = None  # built lazily on first use

    def _get_client(self):
        if self._client is None:
            if not self._api_key:
                raise AIParserError("ANTHROPIC_API_KEY is not configured")
            try:
                import anthropic
            except ImportError as exc:  # pragma: no cover - deploy misconfig
                raise AIParserError(
                    "anthropic SDK is not installed"
                ) from exc
            self._client = anthropic.Anthropic(api_key=self._api_key)
        return self._client

    def parse_resume_text(self, resume_text: str) -> str:
        client = self._get_client()
        try:
            response = client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                system=_SYSTEM_PROMPT,
                output_config={
                    "format": {
                        "type": "json_schema",
                        "schema": _RESUME_PROFILE_SCHEMA,
                    }
                },
                messages=[{"role": "user", "content": resume_text}],
            )
        except Exception as exc:
            # Never leak the raw provider exception to callers.
            logger.exception("AI resume parse request failed")
            raise AIParserError(
                f"AI provider request failed: {type(exc).__name__}"
            ) from exc

        for block in response.content:
            if getattr(block, "type", None) == "text":
                return block.text
        raise AIParserError("AI response contained no text content")
