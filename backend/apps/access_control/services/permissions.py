
from django.db.models import Q
from django.utils import timezone

from apps.access_control.models import AccessGrant, AccessGroupMembership
from apps.resources.models import Resource
from apps.subscriptions.models import UserSubscription


def _has_valid_grant(user, resource, operation, now):
    if not getattr(user, "is_authenticated", False):
        return False

    grants = AccessGrant.objects.filter(
        resource=resource,
        operation=operation,
    ).filter(
        Q(valid_from__isnull=True) | Q(valid_from__lte=now),
        Q(valid_until__isnull=True) | Q(valid_until__gt=now),
    )

    if grants.filter(user=user).exists():
        return True

    active_groups = AccessGroupMembership.objects.filter(
        user=user,
        group__is_active=True,
    ).values_list("group_id", flat=True)

    return grants.filter(group_id__in=active_groups).exists()


def can_access_resource(user, resource, operation):
    if operation not in AccessGrant.Operation.values:
        return False

    authenticated = getattr(user, "is_authenticated", False)

    if authenticated and not user.is_active:
        return False

    is_admin = (
        authenticated
        and getattr(user, "is_super_admin", lambda: False)()
    )

    if is_admin:
        return True

    now = timezone.now()


    # Management is always an explicit permission.
    if operation == AccessGrant.Operation.MANAGE_RESOURCE:
        return _has_valid_grant(user, resource, operation, now)

    # Unpublished resources are restricted to preview and management.
    if resource.status != Resource.Status.PUBLISHED:
        if operation != AccessGrant.Operation.PREVIEW:
            return False
        return _has_valid_grant(user, resource, operation, now)

    policy = resource.access_policy

    if (
        policy == Resource.AccessPolicy.PUBLIC
        and operation == AccessGrant.Operation.VIEW_METADATA
    ):
        return True

    if (
        policy == Resource.AccessPolicy.REGISTERED_ONLY
        and authenticated
        and operation == AccessGrant.Operation.VIEW_METADATA
    ):
        return True

    if _has_valid_grant(user, resource, operation, now):
        return True

    if (
        authenticated
        and policy == Resource.AccessPolicy.SUBSCRIPTION_LIMITED
    ):
        return UserSubscription.objects.filter(
            user=user,
            status=UserSubscription.Status.ACTIVE,
            start_date__lte=now,
            end_date__gt=now,
            plan__is_active=True,
            plan__resource_permissions__resource=resource,
            plan__resource_permissions__operation=operation,
        ).exists()

    return False
