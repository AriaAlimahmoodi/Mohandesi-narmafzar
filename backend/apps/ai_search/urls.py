from django.urls import path

from apps.ai_search.views import (
    AISearchView,
    AISearchHistoryListView,
    AISearchHistoryDetailView,
)


urlpatterns = [
    path(
        "ai-search/",
        AISearchView.as_view(),
        name="ai-search",
    ),
    path(
        "ai-search/history/",
        AISearchHistoryListView.as_view(),
        name="ai-search-history",
    ),
    path(
        "ai-search/history/<int:pk>/",
        AISearchHistoryDetailView.as_view(),
        name="ai-search-history-detail",
    ),
]