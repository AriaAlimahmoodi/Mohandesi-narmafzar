from rest_framework import serializers

from apps.subscriptions.models import SubscriptionPlan
from .models import Payment


class PaymentCreateSerializer(serializers.Serializer):
    plan_id = serializers.PrimaryKeyRelatedField(
        source="plan",
        queryset=SubscriptionPlan.objects.filter(is_active=True),
    )

    def validate_plan_id(self, plan):
        if plan.price <= 0:
            raise serializers.ValidationError(
                "The selected plan cannot be paid through the test gateway."
            )
        return plan


class MockCompleteSerializer(serializers.Serializer):
    outcome = serializers.ChoiceField(choices=("success", "failed"))
    token = serializers.CharField()


class PaymentSerializer(serializers.ModelSerializer):
    plan_name = serializers.CharField(source="plan.name", read_only=True)
    subscription_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Payment
        fields = (
            "id",
            "authority",
            "plan",
            "plan_name",
            "amount",
            "duration_days",
            "status",
            "gateway_reference",
            "subscription_id",
            "created_at",
            "paid_at",
        )
        read_only_fields = fields
class PaymentCreateResponseSerializer(serializers.Serializer):
    payment = PaymentSerializer(read_only=True)
    mock_token = serializers.CharField(read_only=True)
    mock_complete_endpoint = serializers.CharField(read_only=True)
    message = serializers.CharField(read_only=True)