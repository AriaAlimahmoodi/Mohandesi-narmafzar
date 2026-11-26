from django.urls import path

from .views import (
    PaymentCreateView,
    MyPaymentListView,
    PaymentDetailView,
    MockPaymentCompleteView,
)

urlpatterns = [
    path("payments/", PaymentCreateView.as_view(), name="payment-create"),
    path("my-payments/", MyPaymentListView.as_view(), name="my-payment-list"),
    path(
        "payments/<uuid:authority>/",
        PaymentDetailView.as_view(),
        name="payment-detail",
    ),
    path(
        "payments/<uuid:authority>/mock-complete/",
        MockPaymentCompleteView.as_view(),
        name="mock-payment-complete",
    ),
]
