
from decimal import Decimal
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.decorators import login_required,  user_passes_test
from django.db.models import Q
from decimal import Decimal
from django.db.models import Sum

from customers.models import Customer
from accounts.views import generate_unique_refferal_code

from agents.models import County, Location

from .models import  PackageDispatch, Package, DispatchNote, AgentDispatch
from agents.models import County, Location, Agent
from accounts.views import format_kenyan_phone_number

from django.db import transaction

from accounts.views import generate_unique_refferal_code
# pricing.py


@login_required
@transaction.atomic
def create_agent_dispatch(request):

    if request.method != "POST":
        return redirect("open_dispatches")

    agent_id = request.POST.get("agent")
    delivery_address = request.POST.get("delivery_address")
    delivery_phone = request.POST.get("delivery_phone")
    vehicle_used = request.POST.get("vehicle_used")
    vehicle_phone = request.POST.get("vehicle_used_phone_number")

    dispatch_ids = request.POST.getlist("dispatches")

    if not dispatch_ids:
        messages.error(request, "Please select at least one dispatch.")
        return redirect("open_dispatches")

    agent = get_object_or_404(
        Agent,
        pk=agent_id,
    )

    agent_dispatch = AgentDispatch.objects.create(
        agent=agent,
        delivery_address=delivery_address,
        delivery_phone=delivery_phone,
        vehicle_used=vehicle_used,
        vehicle_used_phone_number=vehicle_phone,
        updated_by=request.user,
    )

    total_cost = Decimal("0.00")

    dispatches = (
        PackageDispatch.objects
        .select_related("customer")
        .filter(
            id__in=dispatch_ids,
            agent_dispatch__isnull=True,
            status="OPEN",
        )
    )

    for dispatch in dispatches:

        dispatch.agent_dispatch = agent_dispatch
        dispatch.updated_by = request.user
        dispatch.save(
            update_fields=[
                "agent_dispatch",
                "updated_by",
            ]
        )

        total_cost += dispatch.total_transport_cost

    agent_dispatch.transport_cost = total_cost
    agent_dispatch.save(update_fields=["transport_cost"])

    messages.success(
        request,
        f"{dispatches.count()} dispatch(es) assigned successfully."
    )

    return redirect(
        "agent_dispatch_details",
        agent_dispatch.id,
    )


def calculate_package_cost(package):
    """
    Calculates transport cost for one package.

    Replace this logic with your own pricing engine.
    """

    cost = Decimal("100.00")

    # Weight surcharge
    weight_prices = {
        "2": Decimal("0"),
        "5": Decimal("50"),
        "10": Decimal("80"),
        "20": Decimal("130"),
        "50": Decimal("150"),
        "50+": Decimal("200"),
    }

    cost += weight_prices.get(package.weight, Decimal("0"))

    # Fragile
    if package.is_fragile:
        cost += Decimal("50")

    # Spill prone
    if package.is_spill_prone:
        cost += Decimal("50")

    # Quantity
    if package.quantity > 1:
        cost *= package.quantity

    return cost


def update_dispatch_total(dispatch):
    """
    Recalculate dispatch total.
    """

    total = (
        Package.objects.filter(dispatch=dispatch)
        .aggregate(total=Sum("transport_cost"))
        .get("total")
        or Decimal("0.00")
    )

    dispatch.total_transport_cost = total
    dispatch.save(update_fields=["total_transport_cost"])

    return total

@transaction.atomic
def book_parcel(request):
    counties = County.objects.all()

    if request.method == "POST":

        # -----------------------------
        # Sender
        # -----------------------------

        sender_name = request.POST.get("sender_name")
        sender_phone = request.POST.get("sender_phone")
        from_agent_id = request.POST.get("from_agent")

        sender_customer, _ = Customer.objects.get_or_create(
            phone_number=sender_phone,
            defaults={
                "name": sender_name,
                "refferal_code": generate_unique_refferal_code(),
            },
        )

        if sender_customer.name != sender_name:
            sender_customer.name = sender_name
            sender_customer.save(update_fields=["name"])

        # -----------------------------
        # Receiver
        # -----------------------------

        receiver_name = request.POST.get("receiver_name")
        receiver_phone = request.POST.get("receiver_phone")
        to_agent_id = request.POST.get("to_agent")

        receiver_customer, _ = Customer.objects.get_or_create(
            phone_number=receiver_phone,
            defaults={
                "name": receiver_name,
                "refferal_code": generate_unique_refferal_code(),
            },
        )

        if receiver_customer.name != receiver_name:
            receiver_customer.name = receiver_name
            receiver_customer.save(update_fields=["name"])

        # -----------------------------
        # Agents
        # -----------------------------

        sending_agent = None
        receiving_agent = None

        if from_agent_id:
            sending_agent = Agent.objects.filter(id=from_agent_id).first()

        if to_agent_id:
            receiving_agent = Agent.objects.filter(id=to_agent_id).first()

        # -----------------------------
        # Dispatch
        # -----------------------------

        dispatch = PackageDispatch.objects.create(
            sending_customer=sender_customer,
            sending_agent=sending_agent,

            receiving_customer=receiver_customer,
            receiving_agent=receiving_agent,

            delivery_phone=receiver_phone,

            status="OPEN",
        )

        # Automatically receive if staff books it
        if request.user.is_authenticated and request.user.is_staff:

            dispatch.received_by = request.user
            dispatch.arrived_at_the_sending_agent = True
            dispatch.date_arrived_at_the_sending_agent = timezone.now()

            dispatch.save(
                update_fields=[
                    "received_by",
                    "arrived_at_the_sending_agent",
                    "date_arrived_at_the_sending_agent",
                ]
            )

        # -----------------------------
        # Package
        # -----------------------------

        package = Package.objects.create(

            dispatch=dispatch,

            package_type=request.POST.get("packaging_type"),

            weight=request.POST.get("package_weight"),

            contents=request.POST.get("whats_in_the_package"),

            quantity=int(request.POST.get("quantity") or 1),

            value=Decimal(
                request.POST.get("package_value") or "0"
            ),

            description=request.POST.get("package_details"),
        )

        # -----------------------------
        # Pricing
        # -----------------------------

        package.transport_cost = calculate_package_cost(package)

        package.save(update_fields=["transport_cost"])

        update_dispatch_total(dispatch)

        messages.success(
            request,
            "Parcel booked successfully."
        )

        return redirect(
            "parcel_summary_details",
            dispatch.id,
        )
    return render(
        request,
        "logistics/book_parcel.html",
        {
            "counties": counties,
        },
    )

def parcel_summary_details(request, dispatch_id):

    dispatch = get_object_or_404(
        PackageDispatch.objects.select_related(
            "sending_customer",
            "receiving_customer",
            "sending_agent__location__county",
            "receiving_agent__location__county",
        ).prefetch_related("packages"),
        id=dispatch_id,
    )

    package = dispatch.packages.first()

    return render(
        request,
        "logistics/parcel_summary.html",
        {
            "dispatch": dispatch,
            "package": package,
        },
    )

@login_required
@user_passes_test(lambda u: u.is_staff, login_url='login')  # Restricts access strictly to staff users
def parcel_receipt_view(request, pk):
    # Fetch the dispatch object or return a 404 error if it doesn't exist
    dispatch = get_object_or_404(PackageDispatch, pk=pk)
    
    # Fetch ALL packages linked to this dispatch using the related_name
    packages = dispatch.packages.all()
    
    context = {
        'dispatch': dispatch,
        'packages': packages,  # Passed as plural to handle multiple items
    }
    
    return render(request, 'logistics/parcel_receipt.html', context)

@login_required(login_url="/accounts/login-user/")
def dispatch_customer_orders(request, customer_id):
    customer = get_object_or_404(Customer, id=customer_id)
    previous_url = request.META.get("HTTP_REFERER")
    # Get or create OPEN dispatch
    if not request.user.is_staff and (
        not hasattr(request.user, "customer") or request.user.customer_id != customer.id
    ):
        messages.error(request, "Not authorized")
        return redirect(previous_url)
        
    dispatch, created = PackageDispatch.objects.get_or_create(
        customer=customer,
        status="OPEN"
    )

    dispatch_items = Package.objects.filter(
                        dispatch=dispatch,
                        is_available=True
                    ).select_related("product")
    
    agents = AgentDispatch.objects.filter(status="OPEN")
    
    if request.method == "POST":
        action = request.POST.get("action")
    
        # =========================================
        # ADD MANUAL PRODUCT
        # =========================================
        if action == "add_manual_product":
    
            manual_name = request.POST.get("manual_product_name")
            manual_qty = request.POST.get("manual_quantity")
            manual_price = request.POST.get("manual_price")
            sender = request.POST.get("sender")
            sender_phone = request.POST.get("sender_phone")
            sending_from = request.POST.get("sending_from")
            sender_phone=format_kenyan_phone_number(sender_phone)
    
            if manual_name and manual_qty:
    
                Package.objects.create(
                    dispatch=dispatch,
                    manual_product_name=manual_name,
                    manual_product_price=Decimal(manual_price or "0"),
                    is_manual_product=True,
                    quantity_paid_for=Decimal(manual_qty),
                    quantity_packed=Decimal(manual_qty),
                    ready_to_dispatch=True,
                    sender=sender,
                    sender_phone=sender_phone,
                    sending_from=sending_from,
                )
    
                messages.success(request, "Manual product added.")
    
            else:
                messages.error(request, "Product name and quantity required.")
    
            return redirect(
                "dispatch_customer_orders",
                customer_id=customer.id
            )
    
        # =========================================
        # ADD NOTE
        # =========================================
        elif action == "add_note":
    
            dispatch_note = request.POST.get("dispatch_note")
            dispatch_note_type = request.POST.get("dispatch_note_type")
    
            if dispatch_note:
    
                DispatchNote.objects.create(
                    dispatch=dispatch,
                    note=dispatch_note,
                    note_type=dispatch_note_type or "GENERAL",
                    added_by=request.user
                )
    
                messages.success(request, "Dispatch note added.")
    
            else:
                messages.error(request, "Note cannot be empty.")
    
            return redirect(
                "dispatch_customer_orders",
                customer_id=customer.id
            )
    
        # =========================================
        # UPDATE DISPATCH
        # =========================================
        elif action == "save_dispatch":
    
            dispatch.delivery_address = request.POST.get(
                "delivery_address",
                ""
            )
    
            dispatch.delivery_phone = request.POST.get(
                "delivery_phone",
                ""
            )
    
            dispatch.vehicle_used = request.POST.get(
                "vehicle_used",
                ""
            )
    
            dispatch.approx_transport_cost = Decimal(
                request.POST.get("approx_transport_cost") or "0"
            )
    
            dispatch.packaging_bag_cost = Decimal(
                request.POST.get("packaging_bag_cost") or "0"
            )
    
            dispatch.beba_cost = Decimal(
                request.POST.get("beba_cost") or "0"
            )
            agent_receiving = request.POST.get("agent_receiving")

            if agent_receiving and not dispatch.agent_dispatch:
                agent = AgentDispatch.objects.filter(id=agent_receiving).first()
                dispatch.agent_dispatch = agent
    
            dispatch.updated_by = request.user
    
            dispatch.save()
            
            if dispatch.delivery_address:
                if not dispatch.customer.delivery_address: 
                    dispatch.customer.delivery_address = dispatch.delivery_address
                    dispatch.customer.save()
                    
            if dispatch.vehicle_used:
                if not dispatch.customer.delivery_vehicle : 
                    dispatch.customer.delivery_vehicle  = dispatch.vehicle_used
                    dispatch.customer.save()
    
            for item in dispatch_items:
    
                packed_val = request.POST.get(
                    f"packed_{item.id}",
                    "0"
                )
    
                ready_val = request.POST.get(
                    f"ready_{item.id}",
                    None
                )
    
                item.quantity_packed = Decimal(
                    packed_val or "0"
                )
    
                item.ready_to_dispatch = (
                    True if ready_val == "on" else False
                )
    
                item.save()
    
            messages.success(request, "Dispatch updated.")
    
            return redirect(
                "dispatch_customer_orders",
                customer_id=customer.id
            )

   
    notes = dispatch.notes.select_related("added_by").order_by("-added_at")
    context = {
        "customer": customer,
        "dispatch": dispatch,
        "dispatch_items": dispatch_items,
        "previous_url": previous_url,
        "notes": notes,
        "agents": agents,
        "notes": dispatch.notes.select_related("added_by").order_by("-added_at")
    }
    return render(request, "logistics/dispatch_customer_orders.html", context)
    


def mark_dispatch_sent(request, dispatch_id):
    dispatch = get_object_or_404(PackageDispatch, id=dispatch_id)

    # check ready items
    ready_items = dispatch.items.filter(ready_to_dispatch=True, is_available=True)

    if not ready_items.exists():
        messages.error(request, "No items marked as ready to dispatch.")
        return redirect("dispatch_customer_orders", customer_id=dispatch.customer.id)
    if dispatch.packaging_bag_cost <= 0:
        messages.error(request, "Packaging bag payment not confirmed.")
        return redirect("dispatch_customer_orders", customer_id=dispatch.customer.id)

    if dispatch.beba_cost <= 0:
        messages.error(request, "Beba payment not confirmed.")
        return redirect("dispatch_customer_orders", customer_id=dispatch.customer.id)
    # mark sent
    dispatch.status = "SENT"
    dispatch.sent_at = timezone.now()
    dispatch.updated_by = request.user
    dispatch.save()

    # update original orders status
    for item in ready_items:
        if item.ordinary_order:
            item.ordinary_order.order_status = "sent"
            item.ordinary_order.save()

        if item.group_order:
            item.group_order.sent = True
            item.group_order.save()

    messages.success(request, "Dispatch marked as SENT successfully.")
    return redirect("dispatch_customer_orders", customer_id=dispatch.customer.id)

@login_required(login_url="/accounts/login-user/")    
def all_dispatch_orders(request):
    previous_url = request.META.get("HTTP_REFERER")
    if not request.user.is_staff :
        messages.error(request, "Not authorized")
        return redirect(previous_url)
    dispatches = PackageDispatch.objects.filter(
        items__is_available=True
    ).distinct().select_related("customer").order_by("-updated_at")

    return render(request, "home/index.html", {
        "dispatches": dispatches
    })



@login_required(login_url="/accounts/login-user/")
def order_dispatch_detail(request, dispatch_id):

    previous_url = request.META.get("HTTP_REFERER")

    # Get dispatch
    dispatch = get_object_or_404(
        PackageDispatch.objects.select_related("customer"),
        id=dispatch_id
    )

    customer = dispatch.customer

    # Permission check
    if not request.user.is_staff:
        if not hasattr(request.user, "customer") or request.user.customer_id != customer.id:
            messages.error(request, "Not authorized")
            return redirect(previous_url or "/")

    # Dispatch items
    dispatch_items = dispatch.items.filter(is_available=True).select_related("product")

    context = {
        "customer": customer,
        "dispatch": dispatch,
        "dispatch_items": dispatch_items,
        "previous_url": previous_url,
    }

    return render(request, "logistics/order_dispatch_detail.html", context)




def agent_dispatch_list(request):
  dispatches = AgentDispatch.objects.select_related(
      'agent', 'agent__location', 'agent__location__county'
  ).all()

  # Search filter (searches agent shop name, delivery address, phone, or vehicle)
  search_query = request.GET.get('search', '')
  if search_query:
    dispatches = dispatches.filter(
        Q(agent__shop_name__icontains=search_query)
        | Q(delivery_address__icontains=search_query)
        | Q(delivery_phone__icontains=search_query)
        | Q(vehicle_used__icontains=search_query)
    )

  # County filter
  county_id = request.GET.get('county', '')
  if county_id:
    dispatches = dispatches.filter(agent__location__county_id=county_id)

  # Location filter
  location_id = request.GET.get('location', '')
  if location_id:
    dispatches = dispatches.filter(agent__location_id=location_id)

  # Status filter
  status = request.GET.get('status', '')
  if status:
    dispatches = dispatches.filter(status=status)

  # Boolean flag filters
  if request.GET.get('send') == '1':
    dispatches = dispatches.filter(dispatch_send=True)
  if request.GET.get('picked') == '1':
    dispatches = dispatches.filter(all_luggages_picked=True)
  if request.GET.get('arrived') == '1':
    dispatches = dispatches.filter(arrived_at_the_receiving_agent=True)

  counties = County.objects.all()
  locations = (
      Location.objects.filter(county_id=county_id) if county_id else []
  )

  context = {
      'dispatches': dispatches,
      'counties': counties,
      'locations': locations,
      'selected_county': county_id,
      'selected_location': location_id,
      'selected_status': status,
      'search_query': search_query,
  }
  return render(request, 'logistics/agent_dispatch_list.html', context)



def agent_dispatch_detail(request, pk):
  dispatch = get_object_or_404(
      AgentDispatch.objects.select_related(
          'agent', 'agent__location', 'agent__location__county', 'updated_by'
      ),
      pk=pk,
  )

  # Fetch package dispatches linked to this agent dispatch
  packages = PackageDispatch.objects.select_related(
      'sending_customer', 'receiving_customer', 'sending_agent', 'receiving_agent'
  ).filter(agent_dispatch=dispatch)

  # Handle status update button actions
  if request.method == 'POST':
    action = request.POST.get('action')
    user = request.user if request.user.is_authenticated else None

    if action == 'mark_sent':
      dispatch.dispatch_send = True
      dispatch.date_send = timezone.now()
      dispatch.sent_at = timezone.now()
      dispatch.status = 'SENT'
      dispatch.updated_by = user
      dispatch.save()

    elif action == 'mark_arrived':
      dispatch.arrived_at_the_receiving_agent = True
      dispatch.date_arrived_at_the_receiving_agent = timezone.now()
      dispatch.status = 'ARRIVED'
      dispatch.updated_by = user
      dispatch.save()

    elif action == 'mark_picked':
      dispatch.all_luggages_picked = True
      dispatch.date_picked_by_the_receiving_agent = timezone.now()
      dispatch.status = 'PICKED'
      dispatch.updated_by = user
      dispatch.save()

    return redirect('agent_dispatch_detail', pk=dispatch.pk)

  context = {
      'dispatch': dispatch,
      'packages': packages,
  }
  return render(request, 'logistics/agent_dispatch_detail.html', context)

from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from .models import PackageDispatch


def package_dispatch_detail(request, pk):
  package_dispatch = get_object_or_404(
      PackageDispatch.objects.select_related(
          'agent_dispatch',
          'sending_customer',
          'sending_agent',
          'receiving_customer',
          'receiving_agent',
          'received_by',
          'packed_by',
          'updated_by',
      ),
      pk=pk,
  )

  # Fetch all individual physical items/packages associated with this dispatch
  packages = package_dispatch.packages.all()

  # Handle action buttons for status confirmation
  if request.method == 'POST':
    action = request.POST.get('action')
    user = request.user if request.user.is_authenticated else None

    if action == 'mark_arrived_sending':
      package_dispatch.arrived_at_the_sending_agent = True
      package_dispatch.date_arrived_at_the_sending_agent = timezone.now()
      package_dispatch.received_by = user
      package_dispatch.updated_by = user
      package_dispatch.save()

    elif action == 'mark_packed':
      package_dispatch.packed_by_the_sending_agent = True
      package_dispatch.date_packed_by_the_sending_agent = timezone.now()
      package_dispatch.packed_by = user
      package_dispatch.status = 'SENT'  # Or appropriate workflow status update
      package_dispatch.updated_by = user
      package_dispatch.save()

    elif action == 'mark_picked_customer':
      package_dispatch.picked_picked_by_receiving_customer = True
      package_dispatch.date_picked_picked_by_receiving_customer = (
          timezone.now()
      )
      package_dispatch.status = 'PICKED'
      package_dispatch.updated_by = user
      package_dispatch.save()

    return redirect('package_dispatch_detail', pk=package_dispatch.pk)

  context = {
      'package_dispatch': package_dispatch,
      'packages': packages,
  }
  return render(request, 'logistics/package_dispatch_detail.html', context)


def package_dispatch_list(request):
  dispatches = PackageDispatch.objects.select_related(
      'sending_customer',
      'receiving_customer',
      'sending_agent',
      'receiving_agent',
      'agent_dispatch',
  ).all()

  # Search query (by delivery phone, package dispatch id, or customer/agent details)
  search_query = request.GET.get('search', '')
  if search_query:
    dispatches = dispatches.filter(
        Q(delivery_phone__icontains=search_query)
        | Q(id__icontains=search_query)
        | Q(sending_agent__shop_name__icontains=search_query)
        | Q(receiving_agent__shop_name__icontains=search_query)
    )

  # Filter by specific sending agent
  sending_agent_id = request.GET.get('sending_agent', '')
  if sending_agent_id:
    dispatches = dispatches.filter(sending_agent_id=sending_agent_id)

  # Filter by specific receiving agent
  receiving_agent_id = request.GET.get('receiving_agent', '')
  if receiving_agent_id:
    dispatches = dispatches.filter(receiving_agent_id=receiving_agent_id)

  # Filter by status
  status = request.GET.get('status', '')
  if status:
    dispatches = dispatches.filter(status=status)

  # Filter by payment status
  payment_filter = request.GET.get('payment', '')
  if payment_filter == 'paid':
    dispatches = dispatches.filter(fully_paid=True)
  elif payment_filter == 'pending':
    dispatches = dispatches.filter(fully_paid=False)

  # Get list of all agents for dropdown selection
  agents = Agent.objects.all()

  context = {
      'dispatches': dispatches,
      'agents': agents,
      'search_query': search_query,
      'selected_sending_agent': sending_agent_id,
      'selected_receiving_agent': receiving_agent_id,
      'selected_status': status,
      'selected_payment': payment_filter,
  }
  return render(request, 'logistics/package_dispatch_list.html', context)
