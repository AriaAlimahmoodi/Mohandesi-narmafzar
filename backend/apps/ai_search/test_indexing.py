
from unittest.mock import MagicMock, patch

from django.test import TestCase

from apps.ai_search.models import (
    AISearchCitation,
    AISearchQuery,
    ResourceChunk,
)
from apps.ai_search.services.indexing import (
    IndexingServiceError,
    index_ocr_job,
)
from apps.document_processing.models import OCRJob
from apps.identity.models import User
from apps.resources.models import Resource, ResourceFile


class IndexOCRJobTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="index_test_user",
            password="test-password-123",
        )

        self.resource = Resource.objects.create(
            title="Indexing Test Resource",
            created_by=self.user,
        )

        self.resource_file = ResourceFile.objects.create(
            resource=self.resource,
            file="resources/index-test.pdf",
            file_type=ResourceFile.FileType.PDF,
            size_bytes=1000,
            sha256="b" * 64,
        )

        self.ocr_job = OCRJob.objects.create(
            resource_file=self.resource_file,
            status=OCRJob.Status.COMPLETED,
            extracted_text=(
                "--- Page 1 ---\n"
                "First page content.\n"
                "--- Page 2 ---\n"
                "Second page content."
            ),
            created_by=self.user,
        )

    @patch("apps.ai_search.services.indexing.QdrantService")
    @patch("apps.ai_search.services.indexing.OllamaEmbeddingService")
    def test_index_ocr_job_saves_chunks_and_vectors(
        self,
        embedding_class,
        qdrant_class,
    ):
        embedding = embedding_class.return_value
        vector_store = qdrant_class.return_value

        embedding.embed.return_value = [0.1] * 1024

        result = index_ocr_job(self.ocr_job)

        self.assertEqual(result, 2)
        self.assertEqual(ResourceChunk.objects.count(), 2)
        self.assertEqual(embedding.embed.call_count, 2)
        self.assertEqual(vector_store.upsert_point.call_count, 2)
        vector_store.ensure_collection.assert_called_once()

        chunks = list(
            ResourceChunk.objects.order_by("page_number")
        )

        self.assertEqual(
            [chunk.page_number for chunk in chunks],
            [1, 2],
        )

        self.assertTrue(
            all(chunk.qdrant_point_id for chunk in chunks)
        )

    @patch("apps.ai_search.services.indexing.QdrantService")
    @patch("apps.ai_search.services.indexing.OllamaEmbeddingService")
    def test_incomplete_ocr_job_is_rejected(
        self,
        embedding_class,
        qdrant_class,
    ):
        self.ocr_job.status = OCRJob.Status.PENDING
        self.ocr_job.save()

        with self.assertRaises(ValueError):
            index_ocr_job(self.ocr_job)

        embedding_class.assert_not_called()
        qdrant_class.assert_not_called()

    @patch("apps.ai_search.services.indexing.QdrantService")
    @patch("apps.ai_search.services.indexing.OllamaEmbeddingService")
    def test_failed_embedding_does_not_save_chunks(
        self,
        embedding_class,
        qdrant_class,
    ):
        embedding = embedding_class.return_value
        vector_store = qdrant_class.return_value

        embedding.embed.side_effect = RuntimeError(
            "Ollama is unavailable"
        )

        with self.assertRaises(IndexingServiceError):
            index_ocr_job(self.ocr_job)

        self.assertEqual(ResourceChunk.objects.count(), 0)
        vector_store.upsert_point.assert_not_called()

    @patch("apps.ai_search.services.indexing.QdrantService")
    @patch("apps.ai_search.services.indexing.OllamaEmbeddingService")
    def test_empty_ocr_result_is_rejected(
        self,
        embedding_class,
        qdrant_class,
    ):
        self.ocr_job.extracted_text = ""
        self.ocr_job.save()

        with self.assertRaises(IndexingServiceError):
            index_ocr_job(self.ocr_job)

        embedding_class.assert_not_called()
        qdrant_class.assert_not_called()

    @patch("apps.ai_search.services.indexing.QdrantService")
    @patch("apps.ai_search.services.indexing.OllamaEmbeddingService")
    def test_existing_chunks_are_replaced(
        self,
        embedding_class,
        qdrant_class,
    ):
        old_chunk = ResourceChunk.objects.create(
            resource_file=self.resource_file,
            ocr_job=self.ocr_job,
            page_number=9,
            chunk_index=0,
            content="Old indexed content",
        )

        old_point_id = old_chunk.qdrant_point_id

        embedding = embedding_class.return_value
        vector_store = qdrant_class.return_value

        embedding.embed.return_value = [0.2] * 1024

        result = index_ocr_job(self.ocr_job)

        self.assertEqual(result, 2)

        self.assertFalse(
            ResourceChunk.objects.filter(
                pk=old_chunk.pk
            ).exists()
        )

        self.assertEqual(ResourceChunk.objects.count(), 2)

        if old_point_id:
            vector_store.delete_point.assert_any_call(
                old_point_id
            )
    @patch("apps.ai_search.services.indexing.QdrantService")
    @patch("apps.ai_search.services.indexing.OllamaEmbeddingService")
    def test_reindexing_preserves_historical_citations(
        self,
        embedding_class,
        qdrant_class,
    ):
        old_chunk = ResourceChunk.objects.create(
            resource_file=self.resource_file,
            ocr_job=self.ocr_job,
            page_number=9,
            chunk_index=0,
            content="Historical citation content",
        )

        search_query = AISearchQuery.objects.create(
            user=self.user,
            query="Test historical search",
            response="Historical response",
        )

        citation = AISearchCitation.objects.create(
            search_query=search_query,
            resource=self.resource,
            resource_file=self.resource_file,
            chunk=old_chunk,
            resource_title=self.resource.title,
            resource_file_version=self.resource_file.version,
            excerpt=old_chunk.content,
            page_number=old_chunk.page_number,
            relevance_score=0.95,
        )

        embedding = embedding_class.return_value
        embedding.embed.return_value = [0.2] * 1024

        index_ocr_job(self.ocr_job)

        citation.refresh_from_db()

        self.assertIsNone(citation.chunk)
        self.assertEqual(
            citation.resource_title,
            self.resource.title,
        )
        self.assertEqual(
            citation.resource_file_version,
            self.resource_file.version,
        )
        self.assertEqual(
            citation.excerpt,
            "Historical citation content",
        )
        self.assertEqual(citation.page_number, 9)
        self.assertEqual(citation.relevance_score, 0.95)

        self.assertIsNotNone(citation.resource)
        self.assertIsNotNone(citation.resource_file)