
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient

from apps.access_control.models import (
    AccessGrant,
    AccessGroup,
    AccessGroupMembership,
)
from apps.resources.models import Resource


User = get_user_model()


class AccessControlAPITests(TestCase):

    def setUp(self):
        self.client = APIClient()

        self.admin = User.objects.create_user(
            username="access_api_admin",
            password="test12345",
            role=User.Role.ADMIN,
        )

        self.user = User.objects.create_user(
            username="access_api_user",
            password="test12345",
            role=User.Role.USER,
        )

        self.resource = Resource.objects.create(
            title="API Test Resource",
            status=Resource.Status.PUBLISHED,
            access_policy=Resource.AccessPolicy.PUBLIC,
            created_by=self.admin,
        )

        self.group = AccessGroup.objects.create(
            name="API Researchers",
        )

    def test_normal_user_cannot_create_group(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            reverse("access-group-list"),
            {"name": "Unauthorized Group"},
        )

        self.assertEqual(response.status_code, 403)

    def test_admin_can_create_group(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            reverse("access-group-list"),
            {
                "name": "New Research Group",
                "description": "Research members",
            },
        )

        self.assertEqual(response.status_code, 201, response.data)
        self.assertTrue(
            AccessGroup.objects.filter(
                name="New Research Group"
            ).exists()
        )

    def test_admin_can_add_group_member(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            reverse(
                "access-group-membership",
                kwargs={
                    "group_id": self.group.id,
                    "user_id": self.user.id,
                },
            )
        )

        self.assertEqual(response.status_code, 201, response.data)
        self.assertTrue(
            AccessGroupMembership.objects.filter(
                group=self.group,
                user=self.user,
            ).exists()
        )

    def test_admin_can_remove_group_member(self):
        AccessGroupMembership.objects.create(
            group=self.group,
            user=self.user,
        )

        self.client.force_authenticate(user=self.admin)

        response = self.client.delete(
            reverse(
                "access-group-membership",
                kwargs={
                    "group_id": self.group.id,
                    "user_id": self.user.id,
                },
            )
        )

        self.assertEqual(response.status_code, 204)
        self.assertFalse(
            AccessGroupMembership.objects.filter(
                group=self.group,
                user=self.user,
            ).exists()
        )

    def test_admin_can_create_direct_grant(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            reverse("access-grant-list"),
            {
                "user": self.user.id,
                "resource": self.resource.id,
                "operation": AccessGrant.Operation.DOWNLOAD,
            },
        )

        self.assertEqual(response.status_code, 201, response.data)
        self.assertTrue(
            AccessGrant.objects.filter(
                user=self.user,
                resource=self.resource,
                operation=AccessGrant.Operation.DOWNLOAD,
            ).exists()
        )

    def test_admin_can_create_group_grant(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            reverse("access-grant-list"),
            {
                "group": self.group.id,
                "resource": self.resource.id,
                "operation": AccessGrant.Operation.READ,
            },
        )

        self.assertEqual(response.status_code, 201, response.data)

    def test_grant_requires_exactly_one_target(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            reverse("access-grant-list"),
            {
                "user": self.user.id,
                "group": self.group.id,
                "resource": self.resource.id,
                "operation": AccessGrant.Operation.DOWNLOAD,
            },
        )

        self.assertEqual(response.status_code, 400)

    def test_admin_can_revoke_grant(self):
        grant = AccessGrant.objects.create(
            user=self.user,
            resource=self.resource,
            operation=AccessGrant.Operation.DOWNLOAD,
            created_by=self.admin,
        )

        self.client.force_authenticate(user=self.admin)

        response = self.client.delete(
            reverse(
                "access-grant-detail",
                kwargs={"pk": grant.id},
            )
        )

        self.assertEqual(response.status_code, 204)
        self.assertFalse(
            AccessGrant.objects.filter(pk=grant.id).exists()
        )

    def test_normal_user_cannot_create_grant(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            reverse("access-grant-list"),
            {
                "user": self.user.id,
                "resource": self.resource.id,
                "operation": AccessGrant.Operation.DOWNLOAD,
            },
        )

        self.assertEqual(response.status_code, 403)
