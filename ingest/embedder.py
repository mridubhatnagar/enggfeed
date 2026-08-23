"""Embedder — generates vector(1536) embeddings via the OpenAI SDK.

Model: text-embedding-3-small (1536-dimensional output).
Used at ingest time to embed article chunks, tag names, and prerequisite
topic names.
"""

import openai

from config import settings
from constants import EMBEDDING_MODEL
from exceptions import LLMUnreachableError


class Embedder:
    """Generates embeddings using text-embedding-3-small.

    Usage:
        embedder = Embedder()
        vector: list[float] = embedder.embed("some text")
    """

    def __init__(self) -> None:
        self._client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)

    def embed(
        self, text: str, return_usage: bool = False
    ) -> list[float] | tuple[list[float], dict]:
        """Embed a single text string and return a list[float] of length 1536.

        Raises LLMUnreachableError on any API failure.

        If return_usage is True, returns (vector, usage) where usage is
        {"total_tokens": int}.
        """
        try:
            response = self._client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=text,
            )
            vector = response.data[0].embedding
        except Exception as exc:
            raise LLMUnreachableError(f"Failed to embed text: {exc}") from exc

        if not return_usage:
            return vector
        return vector, {"total_tokens": response.usage.total_tokens}
