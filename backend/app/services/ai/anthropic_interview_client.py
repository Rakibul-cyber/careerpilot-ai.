# Anthropic-backed implementation of AIInterviewPreparationClient.

import json

from app.core.config import settings
from app.core.logging import get_logger
from app.services.ai.base_interview_client import (
    AIInterviewPreparationClient,
    InterviewPreparationAIError,
)

logger = get_logger(__name__)

_SYSTEM_PROMPT = (
    "You are an interview coach. Build a structured interview preparation "
    "package from the user's JSON payload.\n\n"
    "STRICT RULES:\n"
    "- Use ONLY the supplied application, job, resume profile, cover letter, "
    "and job match data.\n"
    "- Never invent experience, certifications, employers, degrees, dates, "
    "achievements, metrics, or skills.\n"
    "- If something is missing, recommend what the candidate should prepare "
    "instead of pretending it exists.\n"
    "- Questions must be specific to the supplied job and candidate data.\n"
    "- Return only valid JSON matching the provided schema."
)

_QUESTION_SCHEMA = {
    "type": "object",
    "properties": {
        "question": {"type": "string"},
        "reason": {"type": "string"},
        "difficulty": {"type": "string", "enum": ["easy", "medium", "hard"]},
    },
    "required": ["question", "reason", "difficulty"],
    "additionalProperties": False,
}

_POINT_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "reason": {"type": "string"},
    },
    "required": ["title", "reason"],
    "additionalProperties": False,
}

_TOPIC_SCHEMA = {
    "type": "object",
    "properties": {
        "topic": {"type": "string"},
        "reason": {"type": "string"},
        "priority": {"type": "string", "enum": ["easy", "medium", "hard"]},
    },
    "required": ["topic", "reason", "priority"],
    "additionalProperties": False,
}

_TIP_SCHEMA = {
    "type": "object",
    "properties": {
        "tip": {"type": "string"},
        "reason": {"type": "string"},
    },
    "required": ["tip", "reason"],
    "additionalProperties": False,
}

_INTERVIEW_PREPARATION_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "strengths": {"type": "array", "items": _POINT_SCHEMA},
        "weaknesses": {"type": "array", "items": _POINT_SCHEMA},
        "technical_questions": {"type": "array", "items": _QUESTION_SCHEMA},
        "behavioral_questions": {"type": "array", "items": _QUESTION_SCHEMA},
        "company_questions": {"type": "array", "items": _QUESTION_SCHEMA},
        "study_topics": {"type": "array", "items": _TOPIC_SCHEMA},
        "interview_tips": {"type": "array", "items": _TIP_SCHEMA},
        "estimated_difficulty": {
            "type": "string",
            "enum": ["easy", "medium", "hard"],
        },
    },
    "required": [
        "summary",
        "strengths",
        "weaknesses",
        "technical_questions",
        "behavioral_questions",
        "company_questions",
        "study_topics",
        "interview_tips",
        "estimated_difficulty",
    ],
    "additionalProperties": False,
}


class AnthropicInterviewPreparationClient(AIInterviewPreparationClient):
    """Generates interview preparation packages via Anthropic Claude."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        max_tokens: int | None = None,
    ) -> None:
        self._api_key = api_key or settings.ANTHROPIC_API_KEY
        self._model = model or settings.ANTHROPIC_MODEL
        self._max_tokens = max_tokens or settings.AI_INTERVIEW_PREPARATION_MAX_TOKENS
        self._client = None

    def _get_client(self):
        if self._client is None:
            if not self._api_key:
                raise InterviewPreparationAIError("ANTHROPIC_API_KEY is not configured")
            try:
                import anthropic
            except ImportError as exc:  # pragma: no cover - deploy misconfig
                raise InterviewPreparationAIError(
                    "anthropic SDK is not installed"
                ) from exc
            self._client = anthropic.Anthropic(api_key=self._api_key)
        return self._client

    def generate_interview_preparation(
        self,
        *,
        application: dict,
        job: dict,
        profile: dict,
        cover_letter: dict | None,
        match: dict | None,
    ) -> str:
        client = self._get_client()
        payload = {
            "application": application,
            "job": job,
            "resume_profile": profile,
            "cover_letter": cover_letter,
            "job_match": match,
        }
        user_message = (
            "Create an interview preparation package using only this data. "
            "If data is missing, recommend preparation areas rather than "
            "inventing facts.\n\n"
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
                        "schema": _INTERVIEW_PREPARATION_SCHEMA,
                    }
                },
                messages=[{"role": "user", "content": user_message}],
            )
        except Exception as exc:
            logger.exception("AI interview-preparation request failed")
            raise InterviewPreparationAIError(
                f"AI provider request failed: {type(exc).__name__}"
            ) from exc

        for block in response.content:
            if getattr(block, "type", None) == "text":
                return block.text
        raise InterviewPreparationAIError("AI response contained no text content")
