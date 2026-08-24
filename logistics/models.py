from django.db import models

# Create your models here.
from django.db import models
from django.conf import settings
from decimal import Decimal
from customers.models import Customer
from agents.models import Agent

# this deal with dispatches send to th receiving agent only  
class AgentDispatch(models.Model):
    STATUS_CHOICES = (
        ("OPEN", "Open"),
        ("SENT", "Sent"),
        ("ON_ROAD", "On Road"),
        ("ARRIVED", "Arrived"),
        ("PICKED", "All Picked"),
    )

    agent = models.ForeignKey(Agent, blank=True, null=True, on_delete=models.SET_NULL, related_name="agent_dispatches")

    delivery_address = models.TextField(blank=True, null=True)
    delivery_phone = models.CharField(max_length=20, blank=True, null=True)

    vehicle_used = models.CharField(max_length=100, blank=True, null=True)
    vehicle_used_phone_number = models.CharField(max_length=100, blank=True, null=True)

    transport_cost = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="OPEN")

    all_luggages_picked = models.BooleanField(default=False)

    arrived_at_the_receiving_agent = models.BooleanField(default=False)
    date_arrived_at_the_receiving_agent = models.DateTimeField( blank=True, null=True, help_text='date parcel arrived to the destination' )
    date_picked_by_the_receiving_agent = models.DateTimeField( blank=True, null=True, help_text='from the courior company' )

    dispatch_send = models.BooleanField(default=False, help_text='send by the sending agent')
    date_send = models.DateTimeField( blank=True, null=True, help_text='date send by the sending agent' )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="agent_dispatch_updates"
    )

    sent_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"#{self.agent} - {self.delivery_address} - ({self.status})"
    
class PackageDispatch(models.Model):
    STATUS_CHOICES = (
        ("OPEN", "Open"),
        ("PACKED", "Packed"),
        ("SENT", "Sent"),
        ("ON_ROAD", "On Road"),
        ("ARRIVED", "Arrived"),
        ("PICKED", "Picked"),
    )

    agent_dispatch = models.ForeignKey(AgentDispatch, blank=True, null=True, on_delete=models.SET_NULL, related_name="agent_dispatches")

    delivery_phone = models.CharField(max_length=20, blank=True, null=True)
    delivery_address = models.CharField(max_length=20, blank=True, null=True)

    sending_customer = models.ForeignKey(Customer, blank=True, null=True, on_delete=models.SET_NULL, related_name="sending_customer")
    sending_agent = models.ForeignKey(Agent, blank=True, null=True, on_delete=models.SET_NULL, related_name="sending_agent")

    receiving_customer = models.ForeignKey(Customer, blank=True, null=True, on_delete=models.SET_NULL, related_name="receiving_customer")
    receiver_identification_code = models.CharField()
    receiving_agent = models.ForeignKey(Agent, blank=True, null=True, on_delete=models.SET_NULL, related_name="receiving_agent")

    total_transport_cost = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    fully_paid = models.BooleanField(default=False)
    fully_paid_at= models.DateTimeField( blank=True, null=True)

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="OPEN")

    
    arrived_at_the_sending_agent = models.BooleanField(default=False)
    date_arrived_at_the_sending_agent = models.DateTimeField( blank=True, null=True)
    
    packed_as_individual_by_the_sending_agent = models.BooleanField(default=False)
    packed_as_combined_package_by_the_sending_agent = models.BooleanField(default=False, help_text='cobined together with other products heading to same agent')
    date_packed_by_the_sending_agent = models.DateTimeField( blank=True, null=True)

    picked_picked_by_receiving_agent = models.BooleanField(default=False, help_text="picked by the receiving agent")
    date_picked_picked_by_receiving_agent = models.DateTimeField( blank=True, null=True)
    
    picked_picked_by_receiving_customer = models.BooleanField(default=False, help_text="picked at the receiving agent")
    date_picked_picked_by_receiving_customer = models.DateTimeField( blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="receiving_staff",
        help_text='the person that received the package at the sending agent'
    )

    packed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="packing_staff",
        help_text='the person that packed the package at the sending agent'
    )

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dispatch_updates"
    )

    sent_at = models.DateTimeField(null=True, blank=True)
    loyalty_counted = models.BooleanField(default=False)

    def __str__(self):
        return f"Dispatch #{self.id} - {self.receiving_customer} ({self.status})"

class Package(models.Model):
    PACKAGE_TYPES = [
        ("envelope", "Envelope"),
        ("box", "Box"),
        ("sack", "Sack"),
        ("uhuru_bag", "Uhuru Bag"),
        ("cylinder", "Cylinder"),
        ("other", "Other"),
    ]

    PACKAGE_COLORS = [
        ("black", "Black"),
        ("white", "White"),
        ("blue", "Blue"),
        ("green", "Green"),
        ("brown", "Brown"),
        ("grey", "Grey"),
        ("maroon", "Maroon"),
        ("orange", "Orange"),
        ("pink", "Pink"),
        ("purple", "Purple"),
        ("red", "Red"),
        ("yellow", "Yellow"),
        ("branded", "Branded"),
    ]

    WEIGHT_RANGES = [
        ("2", "0 - 2 Kg"),
        ("5", "1 - 5 Kg"),
        ("10", "5 - 10 Kg"),
        ("20", "10 - 20 Kg"),
        ("50", "20 - 50 Kg"),
        ("50+", "Above 50 Kg"),
    ]

    VOLUME_RANGES = [
        ("0.05", "0 - 0.05 m³"),
        ("0.1", "0.05 - 0.1 m³"),
        ("0.25", "0.1 - 0.25 m³"),
        ("0.5", "0.25 - 0.5 m³"),
        ("1", "0.5 - 1 m³"),
        ("1+", "Above 1 m³"),
    ]

    dispatch = models.ForeignKey(
        PackageDispatch,
        on_delete=models.CASCADE,
        related_name="packages",
    )
    sending_customer = models.ForeignKey(Customer, blank=True, null=True, on_delete=models.SET_NULL, related_name="package_sending_customer")

    package_type = models.CharField(
        max_length=20,
        choices=PACKAGE_TYPES,
    )

    package_color = models.CharField(
        max_length=20,
        choices=PACKAGE_COLORS,
        blank=True,
        null=True,
    )

    weight = models.CharField(
        max_length=20,
        choices=WEIGHT_RANGES,
    )

    volume = models.CharField(
        max_length=20,
        choices=VOLUME_RANGES,
        blank=True,
        null=True,
    )

    contents = models.CharField(
        max_length=255,
        help_text="E.g. Shoes, Clothes, Electronics",
    )

    value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    quantity = models.IntegerField(
        default=1,
    )

    is_fragile = models.BooleanField(default=False)

    is_spill_prone = models.BooleanField(default=False)

    to_big = models.BooleanField(default=False, help_text='to big to be combined with other packages in one sack')

    description = models.TextField(
        blank=True,
        null=True,
        help_text="Additional package details, quantities, variations, etc.",
    )

    transport_cost = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    packed = models.BooleanField(default=False)
    packed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="product_packing_staff",
        help_text='the person that packed the package at the sending agent'
    )


    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.contents} ({self.dispatch})"
    

        
class DispatchNote(models.Model):

    NOTE_TYPES = (
        ("GENERAL", "General"),
        ("PACKING", "Packing"),
        ("TRANSPORT", "Transport"),
        ("DELIVERY", "Delivery"),
        ("PAYMENT", "Payment"),
    )

    dispatch = models.ForeignKey(
        PackageDispatch,
        on_delete=models.CASCADE,
        related_name="notes"
    )

    note_type = models.CharField(
        max_length=20,
        choices=NOTE_TYPES,
        default="GENERAL"
    )

    note = models.TextField()

    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    added_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.dispatch} - {self.note_type}"
