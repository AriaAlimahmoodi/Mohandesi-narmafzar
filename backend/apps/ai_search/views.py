import logging

from django.db import transaction
from django.db.models import Prefetch

from rest_framework import status
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ai_search.models import (
    AISearchQuery,
    AISearchCitation,
)
from apps.ai_search.serializers import (
    AISearchRequestSerializer,
    AISearchHistoryListSerializer,
    AISearchHistoryDetailSerializer,
)
from apps.ai_search.services.retrieval import RetrievalService


logger = logging.getLogger(__name__)


class AISearchView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = AISearchRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        query_text = serializer.validated_data["query"]
        limit = serializer.validated_data["limit"]

        try:
            retrieval_service = RetrievalService()
            results = retrieval_service.search(
                user=request.user,
                query=query_text,
                limit=limit,
            )
        except Exception:
            logger.exception("AI search retrieval failed.")

            return Response(
                {
                    "detail": (
                        "AI search is temporarily unavailable."
                    )
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        if results:
            answer = "\n\n".join(
                (
                    f"[Resource: {item.chunk.resource_file.resource_id}, "
                    f"Page: {item.chunk.page_number}]\n"
                    f"{item.chunk.content}"
                )
                for item in results
            )
        else:
            answer = "No accessible resources were found for this query."

        with transaction.atomic():
            search_query = AISearchQuery.objects.create(
                user=request.user,
                query=query_text,
                response=answer,
                status="COMPLETED",
            )

            citations = []

            for item in results:
                chunk = item.chunk
                resource = chunk.resource_file.resource
                resource_file = chunk.resource_file

                citations.append(
                    AISearchCitation(
                        search_query=search_query,
                        resource=resource,
                        resource_file=resource_file,
                        chunk=chunk,
                        resource_title=resource.title,
                        resource_file_version=resource_file.version,
                        excerpt=chunk.content,
                        page_number=chunk.page_number,
                        relevance_score=item.score,
                    )
                )

            AISearchCitation.objects.bulk_create(citations)

        citation_data = [
            {
                "resource_id": item.chunk.resource_file.resource_id,
                "resource_title": item.chunk.resource_file.resource.title,
                "resource_file_id": item.chunk.resource_file_id,
                "page_number": item.chunk.page_number,
                "chunk_id": item.chunk.id,
                "relevance_score": item.score,
                "excerpt": item.chunk.content,
            }
            for item in results
        ]

        return Response(
            {
                "search_id": search_query.id,
                "query": query_text,
                "answer": answer,
                "citations": citation_data,
                "results_count": len(citation_data),
            },
            status=status.HTTP_200_OK,
        )


class AISearchHistoryListView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AISearchHistoryListSerializer

    def get_queryset(self):
        return (
            AISearchQuery.objects
            .filter(user=self.request.user)
            .prefetch_related("citations")
            .order_by("-created_at")
        )


class AISearchHistoryDetailView(RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AISearchHistoryDetailSerializer

    def get_queryset(self):
        return (
            AISearchQuery.objects
            .filter(user=self.request.user)
            .prefetch_related(
                Prefetch(
                    "citations",
                    queryset=AISearchCitation.objects.order_by("id"),
                )
            )
        )