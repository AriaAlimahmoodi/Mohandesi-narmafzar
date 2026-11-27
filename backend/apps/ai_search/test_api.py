from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.ai_search.models import (
    AISearchCitation,
    AISearchQuery,
    ResourceChunk,
)
from apps.document_processing.models import OCRJob
from apps.identity.models import User
from apps.resources.models import Resource, ResourceFile


class AISearchAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.user = User.objects.create_user(
            username="ai_search_user",
            password="test-password-123",
        )

        self.resource = Resource.objects.create(
            title="AI Search Test Resource",
            status=Resource.Status.PUBLISHED,
            created_by=self.user,
        )

        self.resource_file = ResourceFile.objects.create(
            resource=self.resource,
            file="resources/ai-search-test.pdf",
            file_type=ResourceFile.FileType.PDF,
            size_bytes=1000,
            sha256="d" * 64,
            is_active=True,
        )

        self.ocr_job = OCRJob.objects.create(
            resource_file=self.resource_file,
            status=OCRJob.Status.COMPLETED,
            extracted_text="Test content for AI search.",
            created_by=self.user,
        )

        self.chunk = ResourceChunk.objects.create(
            resource_file=self.resource_file,
            ocr_job=self.ocr_job,
            page_number=3,
            chunk_index=0,
            content="This is an example of retrieved content.",
        )

        self.retrieved_result = SimpleNamespace(
            chunk=self.chunk,
            score=0.95,
        )

        self.url = "/api/v1/ai-search/"

    def authenticate(self):
        self.client.force_authenticate(user=self.user)

    def test_anonymous_user_cannot_search(self):
        response = self.client.post(
            self.url,
            {"query": "database"},
            format="json",
        )

        self.assertIn(
            response.status_code,
            [
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_403_FORBIDDEN,
            ],
        )

        self.assertEqual(AISearchQuery.objects.count(), 0)

    def test_empty_query_is_rejected(self):
        self.authenticate()

        response = self.client.post(
            self.url,
            {"query": "   "},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertEqual(AISearchQuery.objects.count(), 0)

    def test_invalid_limit_is_rejected(self):
        self.authenticate()

        response = self.client.post(
            self.url,
            {
                "query": "database",
                "limit": 25,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertEqual(AISearchQuery.objects.count(), 0)

    @patch("apps.ai_search.views.RetrievalService")
    def test_successful_search_saves_query_and_citation(
        self,
        retrieval_class,
    ):
        self.authenticate()

        retrieval_class.return_value.search.return_value = [
            self.retrieved_result
        ]

        response = self.client.post(
            self.url,
            {
                "query": "database",
                "limit": 5,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(response.data["query"], "database")
        self.assertEqual(response.data["results_count"], 1)
        self.assertEqual(len(response.data["citations"]), 1)

        citation = response.data["citations"][0]

        self.assertEqual(
            citation["resource_id"],
            self.resource.id,
        )
        self.assertEqual(
            citation["resource_title"],
            self.resource.title,
        )
        self.assertEqual(citation["page_number"], 3)
        self.assertEqual(citation["chunk_id"], self.chunk.id)
        self.assertEqual(citation["relevance_score"], 0.95)

        search_query = AISearchQuery.objects.get(
            id=response.data["search_id"]
        )

        self.assertEqual(search_query.user, self.user)
        self.assertEqual(search_query.query, "database")
        self.assertEqual(search_query.status, "COMPLETED")

        self.assertEqual(AISearchCitation.objects.count(), 1)

        saved_citation = AISearchCitation.objects.get(
            search_query=search_query
        )

        self.assertEqual(saved_citation.resource, self.resource)
        self.assertEqual(saved_citation.resource_file, self.resource_file)
        self.assertEqual(saved_citation.chunk, self.chunk)
        self.assertEqual(saved_citation.page_number, 3)

        retrieval_class.return_value.search.assert_called_once_with(
            user=self.user,
            query="database",
            limit=5,
        )

    @patch("apps.ai_search.views.RetrievalService")
    def test_search_without_results_returns_empty_citations(
        self,
        retrieval_class,
    ):
        self.authenticate()

        retrieval_class.return_value.search.return_value = []

        response = self.client.post(
            self.url,
            {"query": "unknown topic"},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(response.data["results_count"], 0)
        self.assertEqual(response.data["citations"], [])

        self.assertEqual(
            response.data["answer"],
            "No accessible resources were found for this query.",
        )

        self.assertEqual(AISearchQuery.objects.count(), 1)
        self.assertEqual(AISearchCitation.objects.count(), 0)

    @patch("apps.ai_search.views.RetrievalService")
    def test_retrieval_failure_returns_503(
        self,
        retrieval_class,
    ):
        self.authenticate()

        retrieval_class.return_value.search.side_effect = RuntimeError(
            "Retrieval service unavailable"
        )

        response = self.client.post(
            self.url,
            {"query": "database"},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )

        self.assertEqual(
            response.data["detail"],
            "AI search is temporarily unavailable.",
        )

        self.assertEqual(AISearchQuery.objects.count(), 0)
        self.assertEqual(AISearchCitation.objects.count(), 0)
            
    def test_history_list_returns_only_current_users_searches(self):
        self.authenticate()

        own_search = AISearchQuery.objects.create(
            user=self.user,
            query="My private search",
            response="My response",
            status="COMPLETED",
        )

        other_user = User.objects.create_user(
            username="another_ai_user",
            password="test-password-123",
        )

        AISearchQuery.objects.create(
            user=other_user,
            query="Another user's search",
            response="Private response",
            status="COMPLETED",
        )

        response = self.client.get(
            "/api/v1/ai-search/history/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], own_search.id)
        self.assertEqual(
            response.data[0]["query"],
            "My private search",
        )
        self.assertEqual(response.data[0]["results_count"], 0)

    def test_history_detail_returns_search_and_citations(self):
        self.authenticate()

        search_query = AISearchQuery.objects.create(
            user=self.user,
            query="Database search",
            response="Database response",
            status="COMPLETED",
        )

        citation = AISearchCitation.objects.create(
            search_query=search_query,
            resource=self.resource,
            resource_file=self.resource_file,
            chunk=self.chunk,
            resource_title=self.resource.title,
            resource_file_version=self.resource_file.version,
            excerpt=self.chunk.content,
            page_number=self.chunk.page_number,
            relevance_score=0.95,
        )

        response = self.client.get(
            f"/api/v1/ai-search/history/{search_query.id}/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["query"],
            "Database search",
        )
        self.assertEqual(
            response.data["response"],
            "Database response",
        )
        self.assertEqual(len(response.data["citations"]), 1)

        returned_citation = response.data["citations"][0]

        self.assertEqual(returned_citation["id"], citation.id)
        self.assertEqual(
            returned_citation["resource_title"],
            self.resource.title,
        )
        self.assertEqual(
            returned_citation["excerpt"],
            self.chunk.content,
        )
        self.assertEqual(returned_citation["page_number"], 3)
        self.assertEqual(returned_citation["relevance_score"], 0.95)

    def test_user_cannot_access_another_users_search_detail(self):
        self.authenticate()

        other_user = User.objects.create_user(
            username="private_search_owner",
            password="test-password-123",
        )

        other_search = AISearchQuery.objects.create(
            user=other_user,
            query="Private search",
            response="Private response",
            status="COMPLETED",
        )

        response = self.client.get(
            f"/api/v1/ai-search/history/{other_search.id}/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_anonymous_user_cannot_access_history(self):
        response = self.client.get(
            "/api/v1/ai-search/history/"
        )

        self.assertIn(
            response.status_code,
            [
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_403_FORBIDDEN,
            ],
        )

    def test_history_citation_survives_chunk_deletion(self):
        self.authenticate()

        search_query = AISearchQuery.objects.create(
            user=self.user,
            query="Historical content search",
            response="Historical response",
            status="COMPLETED",
        )

        citation = AISearchCitation.objects.create(
            search_query=search_query,
            resource=self.resource,
            resource_file=self.resource_file,
            chunk=self.chunk,
            resource_title=self.resource.title,
            resource_file_version=self.resource_file.version,
            excerpt=self.chunk.content,
            page_number=self.chunk.page_number,
            relevance_score=0.95,
        )

        self.chunk.delete()

        citation.refresh_from_db()

        self.assertIsNone(citation.chunk)
        self.assertEqual(
            citation.excerpt,
            "This is an example of retrieved content.",
        )

        response = self.client.get(
            f"/api/v1/ai-search/history/{search_query.id}/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(len(response.data["citations"]), 1)
        self.assertIsNone(
            response.data["citations"][0]["chunk_id"]
        )
        self.assertEqual(
            response.data["citations"][0]["excerpt"],
            "This is an example of retrieved content.",
        )