
from django.shortcuts import get_object_or_404

from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.access_control.models import (
    AccessGrant,
    AccessGroup,
    AccessGroupMembership,
)
from apps.access_control.serializers import (
    AccessGrantSerializer,
    AccessGroupSerializer,
)
from apps.access_control.api_permissions import IsSuperAdmin
from apps.identity.models import User


class AccessGroupListCreateView(generics.ListCreateAPIView):
    queryset = AccessGroup.objects.all().order_by("name")
    serializer_class = AccessGroupSerializer
    permission_classes = [IsSuperAdmin]


class AccessGroupDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = AccessGroup.objects.all()
    serializer_class = AccessGroupSerializer
    permission_classes = [IsSuperAdmin]


class AccessGroupMembershipView(APIView):
    permission_classes = [IsSuperAdmin]

    def post(self, request, group_id, user_id):
        group = get_object_or_404(AccessGroup, pk=group_id)
        user = get_object_or_404(User, pk=user_id)

        membership, created = AccessGroupMembership.objects.get_or_create(
            group=group,
            user=user,
        )

        return Response(
            {
                "detail": (
                    "عضویت ایجاد شد."
                    if created
                    else "این کاربر از قبل عضو گروه است."
                ),
                "group_id": group.id,
                "user_id": user.id,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    def delete(self, request, group_id, user_id):
        membership = get_object_or_404(
            AccessGroupMembership,
            group_id=group_id,
            user_id=user_id,
        )

        membership.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)


class AccessGrantListCreateView(generics.ListCreateAPIView):
    serializer_class = AccessGrantSerializer
    permission_classes = [IsSuperAdmin]

    def get_queryset(self):
        queryset = (
            AccessGrant.objects
            .select_related("user", "group", "resource", "created_by")
            .order_by("-created_at")
        )

        user_id = self.request.query_params.get("user")
        group_id = self.request.query_params.get("group")
        resource_id = self.request.query_params.get("resource")

        if user_id:
            queryset = queryset.filter(user_id=user_id)

        if group_id:
            queryset = queryset.filter(group_id=group_id)

        if resource_id:
            queryset = queryset.filter(resource_id=resource_id)

        return queryset

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class AccessGrantDetailView(generics.RetrieveDestroyAPIView):
    queryset = AccessGrant.objects.select_related(
        "user",
        "group",
        "resource",
        "created_by",
    )
    serializer_class = AccessGrantSerializer
    permission_classes = [IsSuperAdmin]
