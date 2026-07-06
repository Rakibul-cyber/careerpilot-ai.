# Anthropic-backed implementation of AICoverLetterClient.
#
# Calls the Claude Messages API with a strict "use only provided data" system
# prompt and a structured-output JSON schema ({content}), then returns that raw
# text for the service to validate. The SDK is imported lazily and the client
# built on first use, so importing this module never requires the SDK or a key.

import json

from app.core.config import settings
from app.core.logging import get_logger
from app.services.ai.base_cover_letter_client import (
    AICoverLetterClient,
    CoverLetterAIError,
)

logger = get_logger(__name__)

# The anti-fabrication rule is load-bearing — state it explicitly and up front.
_SYSTEM_PROMPT = (
    "You are a professional cover-letter writer. Write a tailored cover letter "
    "for the candidate and job described in the user's JSON payload.\n\n"
    "STRICT RULES:\n"
    "- Use ONLY the provided resume/profile and job data.\n"
    "- Do NOT invent degrees, employers, job titles, skills, dates, years of "
    "experience, achievements, or metrics that are not in the data.\n"
    "- If information is missing, write generally rather than fabricating "
    "specifics.\n"
    "- Write in the requested language and tone.\n"
    "- Return the letter body only, as plain text in the JSON 'content' field "
    "(no markdown, no placeholders like [Your Name] unless the name is "
    "genuinely absent)."
)

_COVER_LETTER_SCHEMA = {
    "type": "object",
    "properties": {"content": {"type": "string"}},
    "required": ["content"],
    "additionalProperties": False,
}


class AnthropicCoverLetterClient(AICoverLetterClient):
    """Generates cover letters via the Anthropic Claude API."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        max_tokens: int | None = None,
    ) -> None:
        self._api_key = api_key or settings.ANTHROPIC_API_KEY
        self._model = model or settings.ANTHROPIC_MODEL
        self._max_tokens = max_tokens or settings.AI_COVER_LETTER_MAX_TOKENS
        self._client = None  # built lazily on first use

    def _get_client(self):
        if self._client is None:
            if not self._api_key:
                raise CoverLetterAIError("ANTHROPIC_API_KEY is not configured")
            try:
                import anthropic
            except ImportError as exc:  # pragma: no cover - deploy misconfig
                raise CoverLetterAIError(
                    "anthropic SDK is not installed"
                ) from exc
            self._client = anthropic.Anthropic(api_key=self._api_key)
        return self._client

    def generate_cover_letter(
        self,
        *,
        profile: dict,
        job: dict,
        match: dict | None,
        language: str,
        tone: str,
    ) -> str:
        client = self._get_client()
        payload = {
            "language": language,
            "tone": tone,
            "candidate": profile,
            "job": job,
            "match": match,
        }
        user_message = (
            "Write a cover letter using only the following data. "
            "Do not invent anything not present here.\n\n"
            + json.dumps(payload, ensure_ascii=False, default=str)
        )
        try:
            response = client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                system=_SYSTEM_PROMPT,
                output_config={
                    "format": {
                        "type": "json_schema",
                        "schema": _COVER_LETTER_SCHEMA,
                    }
                },
                messages=[{"role": "user", "content": user_message}],
            )
        except Exception as exc:
            logger.exception("AI cover-letter request failed")
            raise CoverLetterAIError(
                f"AI provider request failed: {type(exc).__name__}"
            ) from exc

        for block in response.content:
            if getattr(block, "type", None) == "text":
                return block.text
        raise CoverLetterAIError("AI response contained no text content")
