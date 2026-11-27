
from dataclasses import dataclass
from uuid import UUID

from apps.access_control.models import AccessGrant
from apps.access_control.services.permissions import can_access_resource
from apps.ai_search.models import ResourceChunk
from apps.ai_search.services.embedding import OllamaEmbeddingService
from apps.ai_search.services.vector_store import QdrantService


@dataclass
class RetrievedChunk:
    chunk: ResourceChunk
    score: float | None


class RetrievalService:
    def __init__(self):
        self.embedding_service = None
        self.vector_store = None

    def search(self, user, query, limit=5):
        if not getattr(user, "is_authenticated", False):
            return []

        if not user.is_active:
            return []

        query = query.strip()

        if not query:
            raise ValueError("Search query cannot be empty.")

        if limit < 1 or limit > 20:
            raise ValueError("Limit must be between 1 and 20.")

        self.embedding_service = OllamaEmbeddingService()
        self.vector_store = QdrantService()

        query_vector = self.embedding_service.embed(query)

        candidate_limit = min(max(limit * 5, 20), 100)

        points = self.vector_store.search(
            vector=query_vector,
            limit=candidate_limit,
        )

        point_ids = []

        for point in points:
            try:
                point_ids.append(UUID(str(point.id)))
            except (ValueError, TypeError, AttributeError):
                continue

        if not point_ids:
            return []

        chunks = ResourceChunk.objects.filter(
            qdrant_point_id__in=point_ids,
            resource_file__is_active=True,
        ).select_related(
            "resource_file",
            "resource_file__resource",
            "ocr_job",
        )

        chunks_by_point_id = {
            chunk.qdrant_point_id: chunk
            for chunk in chunks
        }

        results = []

        for point in points:
            try:
                point_id = UUID(str(point.id))
            except (ValueError, TypeError, AttributeError):
                continue

            chunk = chunks_by_point_id.get(point_id)

            if chunk is None:
                continue

            resource = chunk.resource_file.resource

            if not can_access_resource(
                user,
                resource,
                AccessGrant.Operation.READ,
            ):
                continue

            results.append(
                RetrievedChunk(
                    chunk=chunk,
                    score=getattr(point, "score", None),
                )
            )

            if len(results) >= limit:
                break

        return results
