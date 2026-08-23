
from django.contrib import admin
from .models import TransportCredit, TransportCreditTransaction


@admin.register(TransportCredit)
class TransportCreditAdmin(admin.ModelAdmin):
    list_display = (
        "customer",
        "balance",
    )

    search_fields = (
        "customer__name",
        "customer__phone",
        "customer__email",
    )

    list_filter = (
        "balance",
    )

    ordering = ("-balance",)

    list_per_page = 50


@admin.register(TransportCreditTransaction)
class TransportCreditTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "wallet",
        "customer",
        "amount",
        "transaction_type",
        "description",
        "created_at",
    )

    search_fields = (
        "wallet__customer__name",
        "wallet__customer__phone",
        "wallet__customer__email",
        "description",
    )

    list_filter = (
        "transaction_type",
        "created_at",
    )

    ordering = ("-created_at",)

    list_per_page = 50

    @admin.display(description="Customer")
    def customer(self, obj):
        return obj.wallet.customer