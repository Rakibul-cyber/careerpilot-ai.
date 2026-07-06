# Abstraction for the AI resume parser.
#
# The service layer depends on this interface, not on any provider SDK. A
# concrete implementation (e.g. AnthropicResumeParserClient) turns extracted
# resume text into a raw JSON string; validation happens in the service. This
# keeps the AI boundary swappable and testable (inject a fake in tests).

from abc import ABC, abstractmethod


class AIParserError(Exception):
    """Raised when the AI parser client cannot produce a usable response.

    Wraps provider/transport failures so callers never see raw SDK exceptions.
    """


class AIResumeParserClient(ABC):
    """Turns extracted resume text into a raw structured-JSON string."""

    @abstractmethod
    def parse_resume_text(self, resume_text: str) -> str:
        """Return the model's raw response (expected to be JSON) for the text.

        Raises:
            AIParserError: if the provider request fails or returns no usable
                content. Validation of the JSON is the caller's responsibility.
        """
        raise NotImplementedError
