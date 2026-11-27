from django.conf import settings
from django.db import models
from django.db.models import F, Q


class AccessGroup(models.Model):
    name = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="AccessGroupMembership",
        related_name="access_groups",
    )

    def __str__(self):
        return self.name


class AccessGroupMembership(models.Model):
    group = models.ForeignKey(
        AccessGroup,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="access_group_memberships",
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["group", "user"],
                name="unique_access_group_member",
            )
        ]

    def __str__(self):
        return f"{self.user} - {self.group}"


class AccessGrant(models.Model):

    class Operation(models.TextChoices):
        VIEW_METADATA = "VIEW_METADATA", "مشاهده اطلاعات"
        PREVIEW = "PREVIEW", "پیش‌نمایش"
        READ = "READ", "مطالعه آنلاین"
        DOWNLOAD = "DOWNLOAD", "دانلود"
        MANAGE_RESOURCE = "MANAGE_RESOURCE", "مدیریت و ویرایش منبع"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="access_grants",
    )
    group = models.ForeignKey(
        AccessGroup,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="access_grants",
    )
    resource = models.ForeignKey(
        "resources.Resource",
        on_delete=models.CASCADE,
        related_name="access_grants",
    )
    operation = models.CharField(
        max_length=30,
        choices=Operation.choices,
    )
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_until = models.DateTimeField(null=True, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_access_grants",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(user__isnull=False, group__isnull=True)
                    | Q(user__isnull=True, group__isnull=False)
                ),
                name="grant_has_exactly_one_target",
            ),
            models.UniqueConstraint(
                fields=["user", "resource", "operation"],
                condition=Q(user__isnull=False),
                name="unique_user_resource_operation_grant",
            ),
            models.UniqueConstraint(
                fields=["group", "resource", "operation"],
                condition=Q(group__isnull=False),
                name="unique_group_resource_operation_grant",
            ),
            models.CheckConstraint(
                condition=(
                  Q(valid_from__isnull=True)
                | Q(valid_until__isnull=True)
                | Q(valid_until__gt=F("valid_from"))
              ),
            name="grant_valid_until_after_valid_from",
            
         ),
        ]

    def __str__(self):
        target = self.user if self.user_id else self.group
        return f"{target} - {self.resource} - {self.operation}"


class SubscriptionPlanResource(models.Model):
    plan = models.ForeignKey(
        "subscriptions.SubscriptionPlan",
        on_delete=models.CASCADE,
        related_name="resource_permissions",
    )
    resource = models.ForeignKey(
        "resources.Resource",
        on_delete=models.CASCADE,
        related_name="subscription_permissions",
    )
    operation = models.CharField(
        max_length=30,
        choices=AccessGrant.Operation.choices,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["plan", "resource", "operation"],
                name="unique_plan_resource_operation",
            )
        ]

    def __str__(self):
        return f"{self.plan} - {self.resource} - {self.operation}"