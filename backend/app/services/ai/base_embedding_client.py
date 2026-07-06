# Abstraction for text embedding providers.
#
# Separate from the resume-parser and cover-letter clients — different task
# (vectorization), different provider. The embedding/search services depend on
# this interface, never on a provider SDK directly. Anthropic has no first-party
# embeddings API, so the shipped implementation is OpenAI-backed; the
# abstraction keeps that swappable.

from abc import ABC, abstractmethod


class EmbeddingAIError(Exception):
    """Raised when the embedding client cannot produce a vector.

    Wraps provider/transport failures so callers never see raw SDK exceptions.
    """


class AIEmbeddingClient(ABC):
    """Turns text into a fixed-dimension embedding vector."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Identifier of the underlying model (stored on the row)."""
        raise NotImplementedError

    @abstractmethod
    def embed_text(self, text: str) -> list[float]:
        """Return the embedding vector for ``text``.

        Raises:
            EmbeddingAIError: if the provider request fails or returns no usable
                vector.
        """
        raise NotImplementedError
