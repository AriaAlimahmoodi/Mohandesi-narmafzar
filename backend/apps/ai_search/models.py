from django.conf import settings
from django.db import models


class ResourceChunk(models.Model):
    resource_file = models.ForeignKey(
        "resources.ResourceFile",
        on_delete=models.CASCADE,
        related_name="ai_chunks",
    )
    ocr_job = models.ForeignKey(
        "document_processing.OCRJob",
        on_delete=models.CASCADE,
        related_name="ai_chunks",
    )
    page_number = models.PositiveIntegerField()
    chunk_index = models.PositiveIntegerField()
    content = models.TextField()
    qdrant_point_id = models.UUIDField(
        null=True,
        blank=True,
        unique=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("resource_file", "page_number", "chunk_index")
        constraints = [
            models.UniqueConstraint(
                fields=("resource_file", "page_number", "chunk_index"),
                name="unique_resource_chunk_position",
            ),
        ]
        indexes = [
            models.Index(
                fields=("resource_file", "page_number"),
                name="ai_chunk_file_page_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.resource_file.resource.title} "
            f"- page {self.page_number} "
            f"- chunk {self.chunk_index}"
        )


class AISearchQuery(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ai_search_queries",
    )
    query = models.TextField()
    response = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        default="COMPLETED",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"AI Search {self.id} - {self.user}"


class AISearchCitation(models.Model):
    search_query = models.ForeignKey(
        AISearchQuery,
        on_delete=models.CASCADE,
        related_name="citations",
    )
    resource = models.ForeignKey(
        "resources.Resource",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="ai_search_citations",
    )
    resource_file = models.ForeignKey(
        "resources.ResourceFile",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="ai_search_citations",
    )
    chunk = models.ForeignKey(
        ResourceChunk,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="ai_search_citations",
    )

    # Historical snapshot: these values survive re-indexing and deletion.
    resource_title = models.CharField(max_length=500, blank=True)
    resource_file_version = models.PositiveIntegerField(
        null=True,
        blank=True,
    )
    excerpt = models.TextField(blank=True)

    page_number = models.PositiveIntegerField()
    relevance_score = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("id",)

    def __str__(self):
        return (
            f"Search {self.search_query_id} "
            f"- Resource {self.resource_id} "
            f"- Page {self.page_number}"
        )

    class Meta:
        ordering = ("id",)

    def __str__(self):
        return (
            f"Search {self.search_query_id} "
            f"- Resource {self.resource_id} "
            f"- Page {self.page_number}"
        )
