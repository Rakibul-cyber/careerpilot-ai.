# Abstraction for the AI cover-letter generator.
#
# Deliberately separate from the resume parser client (AIResumeParserClient) —
# different task, different prompt, different failure surface. The service
# depends on this interface, not on any provider SDK, and passes plain dict
# context (no ORM objects) so the client stays decoupled from the data layer.

from abc import ABC, abstractmethod


class CoverLetterAIError(Exception):
    """Raised when the cover-letter client cannot produce a usable response.

    Wraps provider/transport failures so callers never see raw SDK exceptions.
    """


class AICoverLetterClient(ABC):
    """Generates a tailored cover letter as a raw structured-JSON string."""

    @abstractmethod
    def generate_cover_letter(
        self,
        *,
        profile: dict,
        job: dict,
        match: dict | None,
        language: str,
        tone: str,
    ) -> str:
        """Return the model's raw response (expected JSON) for the inputs.

        Args:
            profile: serialized ResumeProfile fields (contact, skills, ...).
            job: serialized Job fields (title, company, description, ...).
            match: optional serialized JobMatch highlights, or None.
            language: target language code (e.g. "en", "de").
            tone: desired tone (e.g. "professional", "enthusiastic").

        Raises:
            CoverLetterAIError: if the provider request fails or returns no
                usable content. Validation of the JSON is the caller's job.
        """
        raise NotImplementedError
