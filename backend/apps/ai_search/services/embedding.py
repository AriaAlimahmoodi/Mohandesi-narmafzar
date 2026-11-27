import httpx
from django.conf import settings


class EmbeddingServiceError(Exception):
    pass


class OllamaEmbeddingService:
    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL.rstrip("/")
        self.model = settings.OLLAMA_EMBEDDING_MODEL

    def embed(self, text: str) -> list[float]:
        if not text or not text.strip():
            raise ValueError("Text cannot be empty.")

        try:
            response = httpx.post(
                f"{self.base_url}/api/embed",
                json={
                    "model": self.model,
                    "input": text,
                },
                timeout=60.0,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise EmbeddingServiceError(
                "Ollama embedding service is unavailable."
            ) from exc

        try:
            data = response.json()
            embeddings = data["embeddings"]
            vector = embeddings[0]
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise EmbeddingServiceError(
                "Invalid embedding response from Ollama."
            ) from exc

        if not isinstance(vector, list) or not vector:
            raise EmbeddingServiceError(
                "Ollama returned an invalid embedding vector."
            )

        return vector
