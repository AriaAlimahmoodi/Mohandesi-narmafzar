
import uuid
from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase

from apps.access_control.models import AccessGrant
from apps.ai_search.models import ResourceChunk
from apps.ai_search.services.retrieval import RetrievalService
from apps.document_processing.models import OCRJob
from apps.identity.models import User
from apps.resources.models import Resource, ResourceFile


class RetrievalSecurityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="retrieval_user",
            password="test-password-123",
        )

        self.resource = Resource.objects.create(
            title="Retrieval Security Test",
            status=Resource.Status.PUBLISHED,
            created_by=self.user,
        )

        self.resource_file = ResourceFile.objects.create(
            resource=self.resource,
            file="resources/retrieval-test.pdf",
            file_type=ResourceFile.FileType.PDF,
            size_bytes=1000,
            sha256="c" * 64,
            is_active=True,
        )

        self.ocr_job = OCRJob.objects.create(
            resource_file=self.resource_file,
            status=OCRJob.Status.COMPLETED,
            extracted_text="Authorized database content.",
            created_by=self.user,
        )

        self.point_id = uuid.uuid4()

        self.chunk = ResourceChunk.objects.create(
            resource_file=self.resource_file,
            ocr_job=self.ocr_job,
            page_number=1,
            chunk_index=0,
            content="Authorized database content.",
            qdrant_point_id=self.point_id,
        )

        self.qdrant_point = SimpleNamespace(
            id=str(self.point_id),
            score=0.95,
            payload={
                "content": "UNAUTHORIZED QDRANT PAYLOAD",
            },
        )

    def grant_read_permission(self):
        return AccessGrant.objects.create(
            user=self.user,
            resource=self.resource,
            operation=AccessGrant.Operation.READ,
        )

    @patch("apps.ai_search.services.retrieval.QdrantService")
    @patch("apps.ai_search.services.retrieval.OllamaEmbeddingService")
    def test_user_with_read_permission_receives_chunk(
        self,
        embedding_class,
        qdrant_class,
    ):
        self.grant_read_permission()

        embedding_class.return_value.embed.return_value = [0.1] * 1024
        qdrant_class.return_value.search.return_value = [
            self.qdrant_point
        ]

        service = RetrievalService()
        results = service.search(self.user, "test query")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].chunk, self.chunk)
        self.assertEqual(
            results[0].chunk.content,
            "Authorized database content.",
        )
        self.assertEqual(results[0].score, 0.95)

        self.assertNotEqual(
            results[0].chunk.content,
            "UNAUTHORIZED QDRANT PAYLOAD",
        )

    @patch("apps.ai_search.services.retrieval.QdrantService")
    @patch("apps.ai_search.services.retrieval.OllamaEmbeddingService")
    def test_metadata_permission_does_not_allow_read(
        self,
        embedding_class,
        qdrant_class,
    ):
        AccessGrant.objects.create(
            user=self.user,
            resource=self.resource,
            operation=AccessGrant.Operation.VIEW_METADATA,
        )

        embedding_class.return_value.embed.return_value = [0.1] * 1024
        qdrant_class.return_value.search.return_value = [
            self.qdrant_point
        ]

        service = RetrievalService()
        results = service.search(self.user, "test query")

        self.assertEqual(results, [])

    @patch("apps.ai_search.services.retrieval.QdrantService")
    @patch("apps.ai_search.services.retrieval.OllamaEmbeddingService")
    def test_inactive_resource_file_is_not_retrieved(
        self,
        embedding_class,
        qdrant_class,
    ):
        self.grant_read_permission()

        self.resource_file.is_active = False
        self.resource_file.save()

        embedding_class.return_value.embed.return_value = [0.1] * 1024
        qdrant_class.return_value.search.return_value = [
            self.qdrant_point
        ]

        service = RetrievalService()
        results = service.search(self.user, "test query")

        self.assertEqual(results, [])

    @patch("apps.ai_search.services.retrieval.QdrantService")
    @patch("apps.ai_search.services.retrieval.OllamaEmbeddingService")
    def test_inactive_user_cannot_search(
        self,
        embedding_class,
        qdrant_class,
    ):
        self.user.is_active = False
        self.user.save()

        service = RetrievalService()
        results = service.search(self.user, "test query")

        self.assertEqual(results, [])
        embedding_class.assert_not_called()
        qdrant_class.assert_not_called()

    @patch("apps.ai_search.services.retrieval.QdrantService")
    @patch("apps.ai_search.services.retrieval.OllamaEmbeddingService")
    def test_anonymous_user_cannot_search(
        self,
        embedding_class,
        qdrant_class,
    ):
        from django.contrib.auth.models import AnonymousUser

        service = RetrievalService()
        results = service.search(AnonymousUser(), "test query")

        self.assertEqual(results, [])
        embedding_class.assert_not_called()
        qdrant_class.assert_not_called()

    def test_empty_query_is_rejected(self):
        service = RetrievalService()

        with self.assertRaises(ValueError):
            service.search(self.user, "   ")

    def test_invalid_limit_is_rejected(self):
        service = RetrievalService()

        with self.assertRaises(ValueError):
            service.search(self.user, "test query", limit=0)

        with self.assertRaises(ValueError):
            service.search(self.user, "test query", limit=21)
