from django.db import models
from customers.models import Customer
from decimal import Decimal
from logistics.models import PackageDispatch

class MpesaTransaction(models.Model):

    STATUS = (
        ("PENDING", "Pending"),
        ("STK_SENT", "STK Sent"),
        ("SUCCESS", "Success"),
        ("FAILED", "Failed"),
        ("PROCESSING", "Processing Orders"),
        ("PROCESSED", "Processed"),
        ("EXTRA_PAID", "Extra Paid"),
    )

    checkout_request_id = models.CharField(
        max_length=100,
        unique=True,
        null=True,
        blank=True
    )

    merchant_request_id = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    customer = models.ForeignKey(
        Customer,
        on_delete=models.SET_NULL,
        null=True
    )

    phone_number = models.CharField(max_length=20)

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )
    amount_paid = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )
    unallocated_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00")
    )

    mpesa_receipt = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        null=True
    )

    result_code = models.IntegerField(
        blank=True,
        null=True
    )

    result_desc = models.TextField(
        blank=True,
        null=True
    )

    raw_callback = models.JSONField(
        blank=True,
        null=True
    )

    dispatch = models.ForeignKey(PackageDispatch, null=True, blank=True, on_delete=models.SET_NULL)

    status = models.CharField(
        max_length=20,
        choices=STATUS,
        default="PENDING"
    )

    processed = models.BooleanField(
        default=False
    )
    failure_reason = models.TextField(null=True, blank=True)  # 👈 you use it but didn't define it

    updated_at = models.DateTimeField(auto_now=True)


    created_at = models.DateTimeField(
        auto_now_add=True
    )

    paid_at = models.DateTimeField(
        blank=True,
        null=True
    )

    def __str__(self):
        return f'{self.customer} {self.amount} {self.processed}'
    
class PendingAccountingTransaction(models.Model):

    created_at = models.DateTimeField(auto_now_add=True)

    transaction_type = models.CharField(max_length=10)

    customer_phone = models.CharField(max_length=20)

    customer_name = models.CharField(max_length=255)

    project_phone = models.CharField(max_length=20, blank=True, null=True)

    account_number = models.CharField(max_length=100, blank=True, null=True)

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    subcategory_name = models.CharField(
        max_length=255
    )

    wallet_flow = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )

    reference_code = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    description = models.TextField()

    synced = models.BooleanField(
        default=False
    )

    sync_attempts = models.PositiveIntegerField(
        default=0
    )

    last_error = models.TextField(
        blank=True,
        null=True
    )