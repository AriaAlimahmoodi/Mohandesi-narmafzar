from unittest.mock import patch

from django.test import SimpleTestCase

from apps.ai_search.services.embedding import (
    EmbeddingServiceError,
    OllamaEmbeddingService,
)


class OllamaEmbeddingServiceTests(SimpleTestCase):
    @patch("apps.ai_search.services.embedding.httpx.post")
    def test_embed_returns_vector(self, mock_post):
        mock_post.return_value.json.return_value = {
            "embeddings": [
                [0.1, 0.2, 0.3, 0.4],
            ]
        }
        mock_post.return_value.raise_for_status.return_value = None

        service = OllamaEmbeddingService()

        result = service.embed("software engineering")

        self.assertEqual(
            result,
            [0.1, 0.2, 0.3, 0.4],
        )

        mock_post.assert_called_once()

    def test_empty_text_is_rejected(self):
        service = OllamaEmbeddingService()

        with self.assertRaises(ValueError):
            service.embed("")

    @patch("apps.ai_search.services.embedding.httpx.post")
    def test_invalid_response_raises_error(self, mock_post):
        mock_post.return_value.json.return_value = {}
        mock_post.return_value.raise_for_status.return_value = None

        service = OllamaEmbeddingService()

        with self.assertRaises(EmbeddingServiceError):
            service.embed("software engineering")