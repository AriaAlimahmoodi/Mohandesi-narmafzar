from django.contrib import admin

from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "authority",
        "user",
        "plan",
        "amount",
        "status",
        "created_at",
        "paid_at",
    )

    list_filter = (
        "status",
        "created_at",
    )

    search_fields = (
        "authority",
        "user__username",
        "user__email",
        "gateway_reference",
    )

    readonly_fields = (
        "authority",
        "created_at",
        "paid_at",
    )

    ordering = ("-created_at",)