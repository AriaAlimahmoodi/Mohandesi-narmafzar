
import logging
import uuid

from django.db import transaction

from apps.ai_search.models import ResourceChunk
from apps.ai_search.services.chunking import build_resource_chunks
from apps.ai_search.services.embedding import (
    OllamaEmbeddingService,
)
from apps.ai_search.services.vector_store import QdrantService


logger = logging.getLogger(__name__)


class IndexingServiceError(Exception):
    pass


def index_ocr_job(ocr_job):
    if ocr_job.status != "COMPLETED":
        raise ValueError("Only completed OCR jobs can be indexed.")

    resource_file = ocr_job.resource_file

    chunks = build_resource_chunks(
        resource_file,
        ocr_job,
    )

    if not chunks:
        raise IndexingServiceError(
            "No text chunks were generated from the OCR result."
        )

    embedding_service = OllamaEmbeddingService()
    vector_store = QdrantService()

    vector_store.ensure_collection()

    new_point_ids = []

    for chunk in chunks:
        point_id = uuid.uuid4()

        try:
            vector = embedding_service.embed(chunk.content)

            vector_store.upsert_point(
                point_id=point_id,
                vector=vector,
                payload={
                    "resource_file_id": resource_file.id,
                    "resource_id": resource_file.resource_id,
                    "page_number": chunk.page_number,
                    "chunk_index": chunk.chunk_index,
                    "content": chunk.content,
                },
            )

            chunk.qdrant_point_id = point_id
            new_point_ids.append(point_id)

        except Exception as exc:
            for inserted_id in new_point_ids:
                try:
                    vector_store.delete_point(inserted_id)
                except Exception:
                    logger.exception(
                        "Failed to clean up Qdrant point %s",
                        inserted_id,
                    )

            raise IndexingServiceError(
                "Failed to generate or store resource embeddings."
            ) from exc

    old_chunks = list(
        ResourceChunk.objects.filter(
            resource_file=resource_file
        )
    )

    old_point_ids = [
        chunk.qdrant_point_id
        for chunk in old_chunks
        if chunk.qdrant_point_id
    ]

    try:
        with transaction.atomic():
            ResourceChunk.objects.filter(
                resource_file=resource_file
            ).delete()

            ResourceChunk.objects.bulk_create(chunks)

    except Exception as exc:
        for inserted_id in new_point_ids:
            try:
                vector_store.delete_point(inserted_id)
            except Exception:
                logger.exception(
                    "Failed to clean up Qdrant point %s",
                    inserted_id,
                )

        raise IndexingServiceError(
            "Failed to save indexed chunks in the database."
        ) from exc

    for old_point_id in old_point_ids:
        try:
            vector_store.delete_point(old_point_id)
        except Exception:
            logger.exception(
                "Failed to delete old Qdrant point %s",
                old_point_id,
            )

    return len(chunks)
