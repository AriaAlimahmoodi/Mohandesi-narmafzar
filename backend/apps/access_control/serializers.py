
from rest_framework import serializers

from apps.access_control.models import AccessGrant, AccessGroup
from apps.identity.models import User


class AccessGroupSerializer(serializers.ModelSerializer):
    members = serializers.PrimaryKeyRelatedField(
        many=True,
        read_only=True,
    )

    class Meta:
        model = AccessGroup
        fields = [
            "id",
            "name",
            "description",
            "is_active",
            "members",
            "created_at",
        ]
        read_only_fields = ["id", "created_at", "members"]


class AccessGrantSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        required=False,
        allow_null=True,
    )
    group = serializers.PrimaryKeyRelatedField(
        queryset=AccessGroup.objects.all(),
        required=False,
        allow_null=True,
    )
    validators = []

    class Meta:
        model = AccessGrant
        fields = [
            "id",
            "user",
            "group",
            "resource",
            "operation",
            "valid_from",
            "valid_until",
            "created_by",
            "created_at",
        ]
        read_only_fields = ["id", "created_by", "created_at"]
        validators = []

    def validate(self, attrs):
        user = attrs.get(
            "user",
            getattr(self.instance, "user", None),
        )
        group = attrs.get(
            "group",
            getattr(self.instance, "group", None),
        )

        if bool(user) == bool(group):
            raise serializers.ValidationError(
                "دقیقاً یکی از user یا group باید مشخص شود."
            )

        valid_from = attrs.get(
            "valid_from",
            getattr(self.instance, "valid_from", None),
        )
        valid_until = attrs.get(
            "valid_until",
            getattr(self.instance, "valid_until", None),
        )

        if valid_from and valid_until and valid_from >= valid_until:
            raise serializers.ValidationError(
                "زمان پایان اعتبار باید بعد از زمان شروع باشد."
            )

        resource = attrs.get(
            "resource",
            getattr(self.instance, "resource", None),
        )
        operation = attrs.get(
            "operation",
            getattr(self.instance, "operation", None),
        )

        existing = AccessGrant.objects.filter(
            resource=resource,
            operation=operation,
        )

        if user:
            existing = existing.filter(user=user)
        else:
            existing = existing.filter(group=group)

        if self.instance:
            existing = existing.exclude(pk=self.instance.pk)

        if existing.exists():
            raise serializers.ValidationError(
                "این مجوز قبلاً برای این کاربر یا گروه ثبت شده است."
            )

        return attrs
