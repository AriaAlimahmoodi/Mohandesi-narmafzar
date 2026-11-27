
from django.urls import path

from apps.access_control.views import (
    AccessGroupListCreateView,
    AccessGroupDetailView,
    AccessGroupMembershipView,
    AccessGrantListCreateView,
    AccessGrantDetailView,
)

urlpatterns = [
    path(
        "access-control/groups/",
        AccessGroupListCreateView.as_view(),
        name="access-group-list",
    ),
    path(
        "access-control/groups/<int:pk>/",
        AccessGroupDetailView.as_view(),
        name="access-group-detail",
    ),
    path(
        "access-control/groups/<int:group_id>/members/<int:user_id>/",
        AccessGroupMembershipView.as_view(),
        name="access-group-membership",
    ),
    path(
        "access-control/grants/",
        AccessGrantListCreateView.as_view(),
        name="access-grant-list",
    ),
    path(
        "access-control/grants/<int:pk>/",
        AccessGrantDetailView.as_view(),
        name="access-grant-detail",
    ),
]
