from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import serializers

from apps.access_control.models import AccessGrant, AccessGroupMembership
from apps.subscriptions.models import UserSubscription
from .models import Resource, ResourceFile
from .validators import validate_resource_file, sha256

@transaction.atomic
def register_resource(*, user, resource_data, uploaded_file):
    file_type=validate_resource_file(uploaded_file); fingerprint=sha256(uploaded_file)
    if ResourceFile.objects.filter(sha256=fingerprint).exists():
        raise serializers.ValidationError({"file":"A resource with the same file content already exists."})
    resource=Resource.objects.create(created_by=user,**resource_data)
    ResourceFile.objects.create(resource=resource,file=uploaded_file,file_type=file_type,size_bytes=uploaded_file.size,sha256=fingerprint,version=1,is_active=True)
    return resource



def get_accessible_resources(user):
    queryset = (
        Resource.objects
        .prefetch_related("authors", "files")
        .select_related("category", "created_by")
    )

    authenticated = getattr(user, "is_authenticated", False)

    # Inactive accounts must never access resources,
    # including super administrators.
    if authenticated and not user.is_active:
        return queryset.none()

    # Active super administrators can see all resources.
    if authenticated and user.is_super_admin():
        return queryset

    queryset = queryset.filter(status=Resource.Status.PUBLISHED)

    # Anonymous users can only see public metadata.
    if not authenticated:
        return queryset.filter(
            access_policy=Resource.AccessPolicy.PUBLIC
        )

    now = timezone.now()

    active_groups = AccessGroupMembership.objects.filter(
        user=user,
        group__is_active=True,
    ).values("group_id")

    valid_grants = AccessGrant.objects.filter(
        operation=AccessGrant.Operation.VIEW_METADATA
    ).filter(
        Q(valid_from__isnull=True) | Q(valid_from__lte=now),
        Q(valid_until__isnull=True) | Q(valid_until__gt=now),
    )

    grant_access = (
        Q(access_grants__in=valid_grants.filter(user=user))
        | Q(
            access_grants__in=valid_grants.filter(
                group_id__in=active_groups
            )
        )
    )

    subscription_plan_ids = UserSubscription.objects.filter(
        user=user,
        status=UserSubscription.Status.ACTIVE,
        start_date__lte=now,
        end_date__gt=now,
        plan__is_active=True,
    ).values("plan_id")

    subscription_access = Q(
        access_policy=Resource.AccessPolicy.SUBSCRIPTION_LIMITED,
        subscription_permissions__plan_id__in=subscription_plan_ids,
        subscription_permissions__operation=AccessGrant.Operation.VIEW_METADATA,
    )

    return (
        queryset.filter(
            Q(access_policy=Resource.AccessPolicy.PUBLIC)
            | Q(access_policy=Resource.AccessPolicy.REGISTERED_ONLY)
            | grant_access
            | subscription_access
        )
        .distinct()
    )
