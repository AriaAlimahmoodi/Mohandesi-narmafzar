from django.conf import settings
from qdrant_client import QdrantClient, models  # type: ignore[reportMissingImports]


COLLECTION_NAME = "resource_chunks"
VECTOR_SIZE = 1024


class QdrantService:
    def __init__(self):
        self.client = QdrantClient(url=settings.QDRANT_URL)

    def ensure_collection(self):
        collections = self.client.get_collections().collections

        exists = any(
            collection.name == COLLECTION_NAME
            for collection in collections
        )

        if not exists:
            self.client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=models.VectorParams(
                    size=VECTOR_SIZE,
                    distance=models.Distance.COSINE,
                ),
            )

        return self.client.get_collection(COLLECTION_NAME)

    def upsert_point(self, point_id, vector, payload):
        return self.client.upsert(
            collection_name=COLLECTION_NAME,
            points=[
                models.PointStruct(
                    id=str(point_id),
                    vector=vector,
                    payload=payload,
                )
            ],
        )

    def search(self, vector, limit=5, query_filter=None):
        return self.client.query_points(
            collection_name=COLLECTION_NAME,
            query=vector,
            limit=limit,
            query_filter=query_filter,
            with_payload=True,
        ).points

    def delete_point(self, point_id):
        return self.client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=models.PointIdsList(
                points=[str(point_id)]
            ),
        )
    def delete_resource_points(self, resource_file_id):
        return self.client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="resource_file_id",
                            match=models.MatchValue(
                                value=resource_file_id
                            ),
                        )
                    ]
                )
            ),
        )