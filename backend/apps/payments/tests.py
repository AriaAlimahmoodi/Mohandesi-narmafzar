from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.subscriptions.models import SubscriptionPlan, UserSubscription
from .models import Payment


User = get_user_model()


class PaymentAPITests(TestCase):

    def setUp(self):
        self.client = APIClient()

        self.user = User.objects.create_user(
            username="payment_user",
            password="TestPassword123",
        )

        self.other_user = User.objects.create_user(
            username="other_payment_user",
            password="TestPassword123",
        )

        self.active_plan = SubscriptionPlan.objects.create(
            name="Payment Monthly Plan",
            description="Monthly paid plan",
            duration_days=30,
            price=100000,
            is_active=True,
        )

        self.inactive_plan = SubscriptionPlan.objects.create(
            name="Inactive Payment Plan",
            duration_days=30,
            price=50000,
            is_active=False,
        )

        self.free_plan = SubscriptionPlan.objects.create(
            name="Free Payment Plan",
            duration_days=30,
            price=0,
            is_active=True,
        )

        self.client.force_authenticate(user=self.user)

    def create_payment(self):
        response = self.client.post(
            "/api/v1/payments/",
            {"plan_id": self.active_plan.id},
            format="json",
            HTTP_HOST="localhost",
        )

        self.assertEqual(response.status_code, 201)

        return response.data

    def complete_payment(self, payment_data, outcome="success", token=None):
        authority = payment_data["payment"]["authority"]

        response = self.client.post(
            f"/api/v1/payments/{authority}/mock-complete/",
            {
                "outcome": outcome,
                "token": token or payment_data["mock_token"],
            },
            format="json",
            HTTP_HOST="localhost",
        )

        return response

    def test_anonymous_user_cannot_create_payment(self):
        self.client.force_authenticate(user=None)

        response = self.client.post(
            "/api/v1/payments/",
            {"plan_id": self.active_plan.id},
            format="json",
            HTTP_HOST="localhost",
        )

        self.assertEqual(response.status_code, 401)

    def test_payment_uses_server_side_plan_price(self):
        response = self.client.post(
            "/api/v1/payments/",
            {
                "plan_id": self.active_plan.id,
                "amount": 1,
                "duration_days": 1,
            },
            format="json",
            HTTP_HOST="localhost",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["payment"]["amount"], 100000)
        self.assertEqual(response.data["payment"]["duration_days"], 30)

    def test_inactive_plan_cannot_be_purchased(self):
        response = self.client.post(
            "/api/v1/payments/",
            {"plan_id": self.inactive_plan.id},
            format="json",
            HTTP_HOST="localhost",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Payment.objects.count(), 0)

    def test_free_plan_cannot_use_payment_gateway(self):
        response = self.client.post(
            "/api/v1/payments/",
            {"plan_id": self.free_plan.id},
            format="json",
            HTTP_HOST="localhost",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Payment.objects.count(), 0)

    def test_successful_payment_activates_subscription(self):
        payment_data = self.create_payment()

        response = self.complete_payment(payment_data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], Payment.Status.SUCCESS)

        payment = Payment.objects.get(
            authority=payment_data["payment"]["authority"]
        )

        self.assertEqual(payment.amount, self.active_plan.price)
        self.assertIsNotNone(payment.paid_at)
        self.assertIsNotNone(payment.subscription)

        subscription = payment.subscription

        self.assertEqual(subscription.user, self.user)
        self.assertEqual(subscription.plan, self.active_plan)
        self.assertEqual(
            subscription.status,
            UserSubscription.Status.ACTIVE,
        )

        self.assertEqual(UserSubscription.objects.count(), 1)

    def test_failed_payment_does_not_activate_subscription(self):
        payment_data = self.create_payment()

        response = self.complete_payment(
            payment_data,
            outcome="failed",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], Payment.Status.FAILED)

        payment = Payment.objects.get(
            authority=payment_data["payment"]["authority"]
        )

        self.assertIsNone(payment.subscription)
        self.assertEqual(UserSubscription.objects.count(), 0)

    def test_repeated_success_callback_does_not_create_duplicate_subscription(self):
        payment_data = self.create_payment()

        first_response = self.complete_payment(payment_data)
        second_response = self.complete_payment(payment_data)

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 200)

        self.assertEqual(UserSubscription.objects.count(), 1)

        payment = Payment.objects.get(
            authority=payment_data["payment"]["authority"]
        )

        self.assertEqual(payment.status, Payment.Status.SUCCESS)
        self.assertIsNotNone(payment.subscription)

    def test_invalid_gateway_token_is_rejected(self):
        payment_data = self.create_payment()

        response = self.complete_payment(
            payment_data,
            token="invalid-token",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(UserSubscription.objects.count(), 0)

    def test_user_cannot_view_another_users_payment(self):
        self.client.force_authenticate(user=self.user)
        payment_data = self.create_payment()

        payment = Payment.objects.get(
            authority=payment_data["payment"]["authority"]
        )

        self.client.force_authenticate(user=self.other_user)

        response = self.client.get(
            f"/api/v1/payments/{payment.authority}/",
            HTTP_HOST="localhost",
        )

        self.assertEqual(response.status_code, 404)

    def test_user_cannot_complete_another_users_payment(self):
        self.client.force_authenticate(user=self.user)
        payment_data = self.create_payment()

        authority = payment_data["payment"]["authority"]

        self.client.force_authenticate(user=self.other_user)

        response = self.client.post(
            f"/api/v1/payments/{authority}/mock-complete/",
            {
                "outcome": "success",
                "token": payment_data["mock_token"],
            },
            format="json",
            HTTP_HOST="localhost",
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(UserSubscription.objects.count(), 0)