from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.ai_search.services.vector_store import (
    COLLECTION_NAME,
    VECTOR_SIZE,
    QdrantService,
)


class QdrantServiceTests(SimpleTestCase):

    @patch("apps.ai_search.services.vector_store.QdrantClient")
    def test_ensure_collection_creates_missing_collection(
        self, mock_client_class
    ):
        client = mock_client_class.return_value
        client.get_collections.return_value = SimpleNamespace(
            collections=[]
        )
        expected = object()
        client.get_collection.return_value = expected

        service = QdrantService()
        result = service.ensure_collection()

        self.assertIs(result, expected)
        client.create_collection.assert_called_once()

        kwargs = client.create_collection.call_args.kwargs
        self.assertEqual(kwargs["collection_name"], COLLECTION_NAME)
        self.assertEqual(
            kwargs["vectors_config"].size,
            VECTOR_SIZE,
        )

    @patch("apps.ai_search.services.vector_store.QdrantClient")
    def test_ensure_collection_does_not_recreate_existing_collection(
        self, mock_client_class
    ):
        client = mock_client_class.return_value
        client.get_collections.return_value = SimpleNamespace(
            collections=[
                SimpleNamespace(name=COLLECTION_NAME)
            ]
        )

        service = QdrantService()
        service.ensure_collection()

        client.create_collection.assert_not_called()

    @patch("apps.ai_search.services.vector_store.QdrantClient")
    def test_upsert_point(self, mock_client_class):
        client = mock_client_class.return_value
        service = QdrantService()

        service.upsert_point(
            "test-point-id",
            [0.1, 0.2, 0.3],
            {"resource_id": 1},
        )

        client.upsert.assert_called_once()

    @patch("apps.ai_search.services.vector_store.QdrantClient")
    def test_search_returns_points(self, mock_client_class):
        client = mock_client_class.return_value
        expected_points = [SimpleNamespace(id="point-1")]
        client.query_points.return_value = SimpleNamespace(
            points=expected_points
        )

        service = QdrantService()
        result = service.search([0.1, 0.2, 0.3])

        self.assertEqual(result, expected_points)
        client.query_points.assert_called_once()

    @patch("apps.ai_search.services.vector_store.QdrantClient")
    def test_delete_point(self, mock_client_class):
        client = mock_client_class.return_value
        service = QdrantService()

        service.delete_point("test-point-id")

        client.delete.assert_called_once()

    @patch("apps.ai_search.services.vector_store.QdrantClient")
    def test_delete_resource_points(self, mock_client_class):
        client = mock_client_class.return_value
        service = QdrantService()

        service.delete_resource_points(42)

        client.delete.assert_called_once()

        kwargs = client.delete.call_args.kwargs
        self.assertEqual(kwargs["collection_name"], COLLECTION_NAME)

        selector = kwargs["points_selector"]
        conditions = selector.filter.must

        self.assertEqual(len(conditions), 1)
        self.assertEqual(conditions[0].key, "resource_file_id")
        self.assertEqual(conditions[0].match.value, 42)