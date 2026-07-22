from django.contrib import admin
from .models import MpesaTransaction


@admin.register(MpesaTransaction)
class MpesaTransactionAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "customer",
        "phone_number",
        "amount",
        "unallocated_amount",
        "status",
        "mpesa_receipt",
        "processed",
        "created_at",
        "paid_at",
    )

    list_filter = (
        "status",
        "processed",
        "created_at",
        "paid_at",
    )

    search_fields = (
        "checkout_request_id",
        "merchant_request_id",
        "mpesa_receipt",
        "phone_number",
        "customer__first_name",
        "customer__last_name",
        "customer__business_name",
    )

    readonly_fields = (
        "checkout_request_id",
        "merchant_request_id",
        "mpesa_receipt",
        "result_code",
        "result_desc",
        "raw_callback",
        "created_at",
        "paid_at",
    )

    ordering = ("-created_at",)

    list_per_page = 50

    date_hierarchy = "created_at"

    # autocomplete_fields = ("customer",)

    # fieldsets = (
    #     (
    #         "Payment Information",
    #         {
    #             "fields": (
    #                 "customer",
    #                 "phone_number",
    #                 "amount",
    #                 "status",
    #                 "processed",
    #             )
    #         },
    #     ),
    #     (
    #         "M-Pesa Details",
    #         {
    #             "fields": (
    #                 "checkout_request_id",
    #                 "merchant_request_id",
    #                 "mpesa_receipt",
    #                 "result_code",
    #                 "result_desc",
    #             )
    #         },
    #     ),
    #     (
    #         "Orders",
    #         {
    #             "fields": (
    #                 "selected_orders",
    #             )
    #         },
    #     ),
    #     (
    #         "Callback Data",
    #         {
    #             "classes": ("collapse",),
    #             "fields": (
    #                 "raw_callback",
    #             ),
    #         },
    #     ),
    #     (
    #         "Dates",
    #         {
    #             "fields": (
    #                 "created_at",
    #                 "paid_at",
    #             )
    #         },
    #     ),
    # )

    actions = [
        "mark_as_processed",
    ]

    @admin.action(description="Mark selected transactions as processed")
    def mark_as_processed(self, request, queryset):
        queryset.update(
            processed=True,
            status="PROCESSED"
        )



from .models import PendingAccountingTransaction


@admin.register(PendingAccountingTransaction)
class PendingAccountingTransactionAdmin(admin.ModelAdmin):
    # Compact table (mobile friendly)
    list_display = (
        "created_at",
        "amount",
        "transaction_type",
        "synced",
        "sync_attempts",
    )

    # Click customer name to open full details
    list_display_links = (
        "created_at",
        "amount",
        "transaction_type",
        "synced",
        "sync_attempts",
    )

    # Quick filtering
    list_filter = (
        "synced",
        "transaction_type",
        "wallet_flow",
        "created_at",
    )

    # Search by the fields you'll most likely need
    search_fields = (
        "customer_name",
        "customer_phone",
        "project_phone",
        "account_number",
        "reference_code",
        "subcategory_name",
        "description",
    )

    # Latest first
    ordering = ("-created_at",)

    # Faster navigation
    list_per_page = 25

    # Read-only fields
    readonly_fields = (
        "created_at",
        "sync_attempts",
    )

    # Organize the detail page
    fieldsets = (
        ("Transaction", {
            "fields": (
                "transaction_type",
                "amount",
                "subcategory_name",
                "description",
            )
        }),
        ("Customer", {
            "fields": (
                "customer_name",
                "customer_phone",
            )
        }),
        ("Project / Account", {
            "fields": (
                "project_phone",
                "account_number",
            )
        }),
        ("Sync", {
            "fields": (
                "synced",
                "sync_attempts",
                "reference_code",
                "wallet_flow",
                "last_error",
                "created_at",
            )
        }),
    )

    # Makes searching by ID possible from the search box
    search_help_text = (
        "Search by customer, phone, account, reference, "
        "subcategory, description, or transaction ID."
    )