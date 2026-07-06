# Abstraction for AI interview-preparation generation.

from abc import ABC, abstractmethod


class InterviewPreparationAIError(Exception):
    """Raised when the interview-preparation client cannot return usable text."""


class AIInterviewPreparationClient(ABC):
    """Generates a raw structured-JSON interview preparation package."""

    @abstractmethod
    def generate_interview_preparation(
        self,
        *,
        application: dict,
        job: dict,
        profile: dict,
        cover_letter: dict | None,
        match: dict | None,
    ) -> str:
        """Return the model's raw JSON response for caller-side validation."""
        raise NotImplementedError
