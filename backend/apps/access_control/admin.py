
from django.contrib import admin

from apps.access_control.models import (
    AccessGroup,
    AccessGroupMembership,
    AccessGrant,
    SubscriptionPlanResource,
)


@admin.register(AccessGroup)
class AccessGroupAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "created_at")
    search_fields = ("name",)
    list_filter = ("is_active",)


@admin.register(AccessGroupMembership)
class AccessGroupMembershipAdmin(admin.ModelAdmin):
    list_display = ("group", "user", "joined_at")
    search_fields = ("group__name", "user__username")


@admin.register(AccessGrant)
class AccessGrantAdmin(admin.ModelAdmin):
    list_display = (
        "resource",
        "user",
        "group",
        "operation",
        "valid_from",
        "valid_until",
    )
    list_filter = ("operation",)
    search_fields = (
        "resource__title",
        "user__username",
        "group__name",
    )


@admin.register(SubscriptionPlanResource)
class SubscriptionPlanResourceAdmin(admin.ModelAdmin):
    list_display = ("plan", "resource", "operation")
    list_filter = ("operation",)
