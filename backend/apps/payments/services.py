from datetime import timedelta

from django.conf import settings
from django.core import signing
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.subscriptions.models import UserSubscription
from .models import Payment


MOCK_GATEWAY_SALT = "digital-library.mock-gateway"
MOCK_TOKEN_MAX_AGE = 15 * 60


def create_mock_token(payment):
    return signing.dumps(
        {
            "authority": str(payment.authority),
            "user_id": payment.user_id,
        },
        key=settings.SECRET_KEY,
        salt=MOCK_GATEWAY_SALT,
    )


def complete_mock_payment(payment_id, user_id, token, outcome):
    try:
        payload = signing.loads(
            token,
            key=settings.SECRET_KEY,
            salt=MOCK_GATEWAY_SALT,
            max_age=MOCK_TOKEN_MAX_AGE,
        )
    except signing.BadSignature:
        raise ValidationError("Invalid or expired mock gateway token.")

    with transaction.atomic():
        payment = (
            Payment.objects.select_for_update()
            .select_related("plan")
            .get(pk=payment_id, user_id=user_id)
        )

        if (
            payload.get("authority") != str(payment.authority)
            or payload.get("user_id") != payment.user_id
        ):
            raise ValidationError("Gateway token does not match this payment.")

        # A completed payment must never be processed again.
        if payment.status != Payment.Status.PENDING:
            return payment

        if outcome == "failed":
            payment.status = Payment.Status.FAILED
            payment.gateway_reference = (
                f"MOCK-FAILED-{payment.authority.hex[:12]}"
            )
            payment.save(
                update_fields=("status", "gateway_reference")
            )
            return payment

        now = timezone.now()

        subscription = UserSubscription.objects.create(
            user=payment.user,
            plan=payment.plan,
            start_date=now,
            end_date=now + timedelta(days=payment.duration_days),
            status=UserSubscription.Status.ACTIVE,
        )

        payment.status = Payment.Status.SUCCESS
        payment.gateway_reference = (
            f"MOCK-{payment.authority.hex[:12]}"
        )
        payment.subscription = subscription
        payment.paid_at = now
        payment.save(
            update_fields=(
                "status",
                "gateway_reference",
                "subscription",
                "paid_at",
            )
        )

        return payment
