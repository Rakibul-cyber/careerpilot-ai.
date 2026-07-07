# OpenAI-backed implementation of AIEmbeddingClient.
#
# Uses the OpenAI embeddings endpoint (default: text-embedding-3-small, 1536
# dims). The SDK is imported lazily and the client built on first use, so
# importing this module never requires the SDK or an API key — the app boots
# regardless, and embedding ops fail cleanly if the key is missing.

from app.core.config import settings
from app.core.logging import get_logger
from app.services.ai.base_embedding_client import (
    AIEmbeddingClient,
    EmbeddingAIError,
)

logger = get_logger(__name__)


class OpenAIEmbeddingClient(AIEmbeddingClient):
    """Generates embeddings via the OpenAI API."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        dimensions: int | None = None,
    ) -> None:
        self._api_key = api_key or settings.OPENAI_API_KEY
        self._model = model or settings.EMBEDDING_MODEL
        self._dimensions = dimensions or settings.EMBEDDING_DIMENSIONS
        self._client = None  # built lazily on first use

    @property
    def model_name(self) -> str:
        return self._model

    def _get_client(self):
        if self._client is None:
            if not self._api_key:
                raise EmbeddingAIError("OPENAI_API_KEY is not configured")
            try:
                import openai
            except ImportError as exc:  # pragma: no cover - deploy misconfig
                raise EmbeddingAIError("openai SDK is not installed") from exc
            self._client = openai.OpenAI(api_key=self._api_key)
        return self._client

    def embed_text(self, text: str) -> list[float]:
        client = self._get_client()
        try:
            response = client.embeddings.create(
                model=self._model,
                input=text,
                dimensions=self._dimensions,
            )
        except Exception as exc:
            logger.exception("OpenAI embedding request failed")
            raise EmbeddingAIError(
                f"Embedding provider request failed: {type(exc).__name__}"
            ) from exc

        vector = response.data[0].embedding
        if len(vector) != self._dimensions:
            raise EmbeddingAIError(
                f"Embedding dimension mismatch: got {len(vector)}, "
                f"expected {self._dimensions}"
            )
        return list(vector)
