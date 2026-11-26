from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Payment
from .serializers import (
    MockCompleteSerializer,
    PaymentCreateSerializer,
    PaymentCreateResponseSerializer,
    PaymentSerializer,
)
from .services import create_mock_token, complete_mock_payment


class PaymentCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request=PaymentCreateSerializer,
        responses={201: PaymentCreateResponseSerializer},
    )

    def post(self, request):
        serializer = PaymentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        plan = serializer.validated_data["plan"]

        payment = Payment.objects.create(
            user=request.user,
            plan=plan,
            amount=plan.price,
            duration_days=plan.duration_days,
        )

        return Response(
            {
                "payment": PaymentSerializer(payment).data,
                "mock_token": create_mock_token(payment),
                "mock_complete_endpoint": (
                    f"/api/v1/payments/{payment.authority}/mock-complete/"
                ),
                "message": "Test payment created. No real money was charged.",
            },
            status=status.HTTP_201_CREATED,
        )


class MyPaymentListView(generics.ListAPIView):
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Payment.objects.filter(
            user=self.request.user
        ).select_related("plan")


class PaymentDetailView(generics.RetrieveAPIView):
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "authority"

    def get_queryset(self):
        return Payment.objects.filter(
            user=self.request.user
        ).select_related("plan")


class MockPaymentCompleteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request=MockCompleteSerializer,
        responses={200: PaymentSerializer},
    )


    def post(self, request, authority):
        payment = get_object_or_404(
            Payment,
            authority=authority,
            user=request.user,
        )

        serializer = MockCompleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        payment = complete_mock_payment(
            payment_id=payment.id,
            user_id=request.user.id,
            token=serializer.validated_data["token"],
            outcome=serializer.validated_data["outcome"],
        )

        return Response(PaymentSerializer(payment).data)
