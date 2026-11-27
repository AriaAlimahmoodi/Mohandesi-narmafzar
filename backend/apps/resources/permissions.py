
from rest_framework.permissions import BasePermission, SAFE_METHODS

from apps.access_control.models import AccessGrant
from apps.access_control.services.permissions import can_access_resource


class ResourceAccessPermission(BasePermission):

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True

        return bool(
            request.user.is_authenticated
            and request.user.is_librarian()
        )

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return can_access_resource(
                request.user,
                obj,
                AccessGrant.Operation.VIEW_METADATA,
            )

        return can_access_resource(
            request.user,
            obj,
            AccessGrant.Operation.MANAGE_RESOURCE,
        )
