from datetime import timedelta
from pathlib import Path
from tempfile import NamedTemporaryFile

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.access_control.models import AccessGrant
from apps.resources.models import Resource, ResourceFile


User = get_user_model()


class ResourceAccessTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.admin = User.objects.create_user(
            username="admin",
            password="password123",
            role=User.Role.ADMIN,
            is_active=True,
        )

        self.user = User.objects.create_user(
            username="user",
            password="password123",
            role=User.Role.USER,
            is_active=True,
        )

        self.resource = Resource.objects.create(
            title="Test Resource",
            status=Resource.Status.PUBLISHED,
            access_policy=Resource.AccessPolicy.REGISTERED_ONLY,
            created_by=self.admin,
        )

        self.resource_file = ResourceFile.objects.create(
            resource=self.resource,
            file=ContentFile(b"test file content", name="test.pdf"),
            file_type=ResourceFile.FileType.PDF,
            size_bytes=17,
            sha256="a" * 64,
            version=1,
            is_active=True,
        )

    def test_user_without_download_permission_gets_404(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            f"/api/v1/resources/{self.resource.id}/files/{self.resource_file.id}/download/"
        )

        self.assertEqual(response.status_code, 404)

    def test_user_with_download_grant_can_download(self):
        AccessGrant.objects.create(
            user=self.user,
            resource=self.resource,
            operation=AccessGrant.Operation.DOWNLOAD,
            created_by=self.admin,
        )

        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            f"/api/v1/resources/{self.resource.id}/files/{self.resource_file.id}/download/"
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment", response["Content-Disposition"])

    def test_super_admin_can_download(self):
        super_admin = User.objects.create_superuser(
            username="superadmin",
            password="password123",
            email="super@example.com",
        )

        self.client.force_authenticate(user=super_admin)

        response = self.client.get(
            f"/api/v1/resources/{self.resource.id}/files/{self.resource_file.id}/download/"
        )

        self.assertEqual(response.status_code, 200)


class ResourceListAccessTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.admin = User.objects.create_user(
            username="admin",
            password="password123",
            role=User.Role.ADMIN,
            is_active=True,
        )

        self.user = User.objects.create_user(
            username="user",
            password="password123",
            role=User.Role.USER,
            is_active=True,
        )

        self.public_resource = Resource.objects.create(
            title="Public Resource",
            status=Resource.Status.PUBLISHED,
            access_policy=Resource.AccessPolicy.PUBLIC,
            created_by=self.admin,
        )

        self.private_resource = Resource.objects.create(
            title="Private Resource",
            status=Resource.Status.DRAFT,
            access_policy=Resource.AccessPolicy.CONFIDENTIAL,
            created_by=self.admin,
        )

    def test_active_super_admin_can_list_all_resources(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.get("/api/v1/resources/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)

    def test_inactive_super_admin_gets_empty_list(self):
        self.admin.is_active = False
        self.admin.save(update_fields=["is_active"])

        self.client.force_authenticate(user=self.admin)

        response = self.client.get("/api/v1/resources/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)

    def test_anonymous_user_sees_public_resources(self):
        response = self.client.get("/api/v1/resources/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], "Public Resource")

    def test_authenticated_user_sees_public_resources(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get("/api/v1/resources/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], "Public Resource")


    def test_manage_grant_does_not_allow_metadata_visibility(self):
        managed_resource = Resource.objects.create(
            title="Managed Confidential Resource",
            status=Resource.Status.PUBLISHED,
            access_policy=Resource.AccessPolicy.CONFIDENTIAL,
            created_by=self.admin,
        )

        AccessGrant.objects.create(
            user=self.user,
            resource=managed_resource,
            operation=AccessGrant.Operation.MANAGE_RESOURCE,
            created_by=self.admin,
        )

        self.client.force_authenticate(user=self.user)

        response = self.client.get("/api/v1/resources/")

        self.assertEqual(response.status_code, 200)

        resource_titles = [item["title"] for item in response.data]

        self.assertNotIn(
            "Managed Confidential Resource",
            resource_titles,
        )
