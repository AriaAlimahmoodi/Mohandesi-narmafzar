from rest_framework import generics, permissions

from .models import Author, Category, Resource
from .permissions import ResourceAccessPermission
from .serializers import (
    AuthorSerializer,
    CategorySerializer,
    ResourceSerializer,
)


def get_accessible_resources(user):
    queryset = (
        Resource.objects
        .prefetch_related("authors", "files")
        .select_related("category", "created_by")
    )

    if user.is_authenticated and user.is_librarian():
        return queryset

    queryset = queryset.filter(status=Resource.Status.PUBLISHED)

    if user.is_authenticated:
        return queryset.filter(
            access_policy__in=[
                Resource.AccessPolicy.PUBLIC,
                Resource.AccessPolicy.REGISTERED_ONLY,
            ]
        )

    return queryset.filter(
        access_policy=Resource.AccessPolicy.PUBLIC
    )


class AuthorListCreateView(generics.ListCreateAPIView):
    queryset = Author.objects.all().order_by("name")
    serializer_class = AuthorSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def perform_create(self, serializer):
        if not self.request.user.is_librarian():
            self.permission_denied(self.request)

        serializer.save()


class CategoryListCreateView(generics.ListCreateAPIView):
    queryset = Category.objects.all().order_by("name")
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def perform_create(self, serializer):
        if not self.request.user.is_librarian():
            self.permission_denied(self.request)

        serializer.save()


class ResourceListCreateView(generics.ListCreateAPIView):
    serializer_class = ResourceSerializer
    permission_classes = [ResourceAccessPermission]

    def get_queryset(self):
        return get_accessible_resources(self.request.user)


class ResourceDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = ResourceSerializer
    permission_classes = [ResourceAccessPermission]

    def get_queryset(self):
        return get_accessible_resources(self.request.user)
