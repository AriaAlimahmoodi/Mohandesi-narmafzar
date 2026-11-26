from rest_framework import generics, permissions
from .models import Author, Category, Resource
from .permissions import ResourceAccessPermission
from .serializers import AuthorSerializer, CategorySerializer, ResourceSerializer
class AuthorListCreateView(generics.ListCreateAPIView):
    queryset=Author.objects.all().order_by("name"); serializer_class=AuthorSerializer; permission_classes=[permissions.IsAuthenticatedOrReadOnly]
    def perform_create(self,serializer):
        if not self.request.user.is_librarian(): self.permission_denied(self.request)
        serializer.save()
class CategoryListCreateView(generics.ListCreateAPIView):
    queryset=Category.objects.all().order_by("name"); serializer_class=CategorySerializer; permission_classes=[permissions.IsAuthenticatedOrReadOnly]
    def perform_create(self,serializer):
        if not self.request.user.is_librarian(): self.permission_denied(self.request)
        serializer.save()
class ResourceListCreateView(generics.ListCreateAPIView):
    serializer_class=ResourceSerializer; permission_classes=[ResourceAccessPermission]
    def get_queryset(self):
        qs=Resource.objects.prefetch_related("authors","files").select_related("category","created_by")
        u=self.request.user
        if u.is_authenticated and u.is_librarian(): return qs
        if u.is_authenticated: return qs.filter(status=Resource.Status.PUBLISHED,access_policy__in=[Resource.AccessPolicy.PUBLIC,Resource.AccessPolicy.REGISTERED_ONLY])
        return qs.filter(status=Resource.Status.PUBLISHED,access_policy=Resource.AccessPolicy.PUBLIC)
class ResourceDetailView(generics.RetrieveUpdateAPIView):
    queryset=Resource.objects.prefetch_related("authors","files").select_related("category","created_by"); serializer_class=ResourceSerializer; permission_classes=[ResourceAccessPermission]
