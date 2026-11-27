
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth.models import AnonymousUser

from apps.access_control.models import (
    AccessGrant,
    AccessGroup,
    AccessGroupMembership,
    SubscriptionPlanResource,
)
from apps.access_control.services.permissions import can_access_resource
from apps.resources.models import Resource
from apps.subscriptions.models import SubscriptionPlan, UserSubscription


User = get_user_model()


class ResourceAccessTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="normal_user",
            password="test12345",
            role=User.Role.USER,
        )

        self.admin = User.objects.create_user(
            username="admin_user",
            password="test12345",
            role=User.Role.ADMIN,
        )

        self.resource = Resource.objects.create(
            title="Test Resource",
            status=Resource.Status.PUBLISHED,
            access_policy=Resource.AccessPolicy.PUBLIC,
            created_by=self.admin,
        )

    def create_grant(self, **kwargs):
        return AccessGrant.objects.create(
            resource=self.resource,
            operation=AccessGrant.Operation.DOWNLOAD,
            created_by=self.admin,
            **kwargs,
        )

    def test_anonymous_can_view_public_metadata(self):
        self.assertTrue(
            can_access_resource(
                AnonymousUser(),
                self.resource,
                AccessGrant.Operation.VIEW_METADATA,
            )
        )

    def test_anonymous_cannot_download_public_resource(self):
        self.assertFalse(
            can_access_resource(
                AnonymousUser(),
                self.resource,
                AccessGrant.Operation.DOWNLOAD,
            )
        )

    def test_user_can_download_with_direct_grant(self):
        self.create_grant(user=self.user)

        self.assertTrue(
            can_access_resource(
                self.user,
                self.resource,
                AccessGrant.Operation.DOWNLOAD,
            )
        )

    def test_user_without_grant_cannot_download(self):
        self.assertFalse(
            can_access_resource(
                self.user,
                self.resource,
                AccessGrant.Operation.DOWNLOAD,
            )
        )

    def test_group_member_can_access_group_grant(self):
        group = AccessGroup.objects.create(name="Researchers")

        AccessGroupMembership.objects.create(
            group=group,
            user=self.user,
        )

        self.create_grant(group=group)

        self.assertTrue(
            can_access_resource(
                self.user,
                self.resource,
                AccessGrant.Operation.DOWNLOAD,
            )
        )

    def test_inactive_group_grant_is_denied(self):
        group = AccessGroup.objects.create(
            name="Inactive Researchers",
            is_active=False,
        )

        AccessGroupMembership.objects.create(
            group=group,
            user=self.user,
        )

        self.create_grant(group=group)

        self.assertFalse(
            can_access_resource(
                self.user,
                self.resource,
                AccessGrant.Operation.DOWNLOAD,
            )
        )

    def test_expired_direct_grant_is_denied(self):
        self.create_grant(
            user=self.user,
            valid_until=timezone.now() - timedelta(days=1),
        )

        self.assertFalse(
            can_access_resource(
                self.user,
                self.resource,
                AccessGrant.Operation.DOWNLOAD,
            )
        )

    def test_valid_subscription_allows_configured_operation(self):
        self.resource.access_policy = Resource.AccessPolicy.SUBSCRIPTION_LIMITED
        self.resource.save()

        plan = SubscriptionPlan.objects.create(
            name="Research Plan",
            duration_days=30,
            price=1000,
        )

        SubscriptionPlanResource.objects.create(
            plan=plan,
            resource=self.resource,
            operation=AccessGrant.Operation.DOWNLOAD,
        )

        now = timezone.now()

        UserSubscription.objects.create(
            user=self.user,
            plan=plan,
            start_date=now - timedelta(days=1),
            end_date=now + timedelta(days=10),
            status=UserSubscription.Status.ACTIVE,
        )

        self.assertTrue(
            can_access_resource(
                self.user,
                self.resource,
                AccessGrant.Operation.DOWNLOAD,
            )
        )

    def test_expired_subscription_is_denied(self):
        self.resource.access_policy = Resource.AccessPolicy.SUBSCRIPTION_LIMITED
        self.resource.save()

        plan = SubscriptionPlan.objects.create(
            name="Expired Plan",
            duration_days=30,
        )

        SubscriptionPlanResource.objects.create(
            plan=plan,
            resource=self.resource,
            operation=AccessGrant.Operation.DOWNLOAD,
        )

        now = timezone.now()

        UserSubscription.objects.create(
            user=self.user,
            plan=plan,
            start_date=now - timedelta(days=10),
            end_date=now - timedelta(days=1),
            status=UserSubscription.Status.ACTIVE,
        )

        self.assertFalse(
            can_access_resource(
                self.user,
                self.resource,
                AccessGrant.Operation.DOWNLOAD,
            )
        )

    def test_inactive_user_cannot_access_resource(self):
        self.user.is_active = False
        self.user.save()

        self.create_grant(user=self.user)

        self.assertFalse(
            can_access_resource(
                self.user,
                self.resource,
                AccessGrant.Operation.DOWNLOAD,
            )
        )

    def test_super_admin_can_access_resource(self):
        self.assertTrue(
            can_access_resource(
                self.admin,
                self.resource,
                AccessGrant.Operation.DOWNLOAD,
            )
        )

    def test_super_admin_cannot_access_with_inactive_account(self):
        self.admin.is_active = False
        self.admin.save()

        self.assertFalse(
            can_access_resource(
                self.admin,
                self.resource,
                AccessGrant.Operation.DOWNLOAD,
            )
        )

    def test_unpublished_resource_is_denied_to_normal_user(self):
        self.resource.status = Resource.Status.DRAFT
        self.resource.save()

        self.assertFalse(
            can_access_resource(
                self.user,
                self.resource,
                AccessGrant.Operation.VIEW_METADATA,
            )
        )
