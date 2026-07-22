import base64
import requests
import json
from django.db.models import Sum
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from django.http import JsonResponse
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.db import transaction

from django.db import transaction
from django.contrib import messages
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, ROUND_DOWN


from customers.models import Customer
from .models import MpesaTransaction, PendingAccountingTransaction
from logistics.models import PackageDispatch
from accounts.models import APIKey
from accounts.views import format_kenyan_phone_number



# Create your views here.


def process_dispatch_payment(
    *,
    dispatch,
    amount,
    payment_method,
    reference_code="",
    api_key=None,
    recorded_by=None,
    send_to_accounting=True,
    project_phone=None,
    skip_reference_check=False
):
    """
    Reusable payment processor for group orders.

    Works for:
    - Manual payments
    - Automated STK payments
    - Wallet payments
    """

    # ---------------------------------------
    # VALIDATE AMOUNT
    # ---------------------------------------
    try:

        amount = Decimal(str(amount)).quantize(
            Decimal("0.00"),
            rounding=ROUND_DOWN
        )

        if amount <= 0:
            raise InvalidOperation

    except:
        raise Exception("Invalid payment amount")

    # ---------------------------------------
    # VALIDATE REFERENCE
    # ---------------------------------------
    if payment_method in ['M-Pesa', 'Bank'] and not reference_code:
        raise Exception("Reference code required")

    with transaction.atomic():

        # ---------------------------------------
        # LOCK ORDER
        # ---------------------------------------
        orderdisp = (
            PackageDispatch.objects
            .select_for_update()
            .get(pk=dispatch.pk)
        )

        # ---------------------------------------
        # PREVENT DUPLICATE REFERENCE
        # ---------------------------------------
        if (
            not skip_reference_check
            and reference_code
            and payment_method in ["M-Pesa", "Bank"]
        ):

            exists = (
                PackageDispatch.objects
                .filter(payment_reference_code=reference_code)
                .exclude(pk=dispatch.pk)
                .exists()
            )

            if exists:
                raise Exception("Reference already used")

        # ---------------------------------------
        # PREVENT OVERPAYMENT
        # ---------------------------------------
        total_required = (
            orderdisp.total_transport_cost
        )

        total_already_paid = (
            orderdisp.amount_paid
        )

        total_after_payment = (
            total_already_paid
            + amount
        )

        if total_after_payment > total_required:

            raise Exception(
                "Amount paid exceeds required total"
            )

        # ---------------------------------------
        # ACCOUNT NUMBER
        # ---------------------------------------
        if payment_method == 'M-Pesa':

            account_number = (
                settings.PAYMENT_RECEIVING_MPESA_NUMBER
            )

        elif payment_method == 'Bank':

            account_number = (
                settings.PAYMENT_RECEIVING_BANK_ACCOUNT_NUMBER
            )

        else:

            account_number = "CASH"

        wallet_flow = (
            "purchase"
            if payment_method == "Wallet"
            else None
        )

        

        # ---------------------------------------
        # PROJECT PHONE
        # ---------------------------------------
        if project_phone:

            project_phone = format_kenyan_phone_number(
                project_phone
            )

        subcategory = (
            f"logistics sales"
        )

        # ---------------------------------------
        # ACCOUNTING
        # ---------------------------------------
        if send_to_accounting:

            if not api_key:
                raise Exception("API key required")
            pending_transaction = PendingAccountingTransaction.objects.create(

                transaction_type="IN",

                customer_phone=orderdisp.receiving_customer.phone_number,

                customer_name=str(orderdisp.receiving_customer),

                project_phone=project_phone,

                account_number=account_number,

                amount=amount,

                subcategory_name=subcategory,

                wallet_flow=wallet_flow,

                reference_code=reference_code,

                description=f"Group payment Order #{orderdisp.id}",
            )

            if wallet_flow:
                from payments.views import sync_accounting_transactions
                sync_accounting_transactions(id=pending_transaction.id)

            
        # ---------------------------------------
        # ALLOCATION Of Remaining amount
        # ---------------------------------------
        remaining_payment = amount

        # ---------------------------------------
        # 1) PAY PRODUCT FIRST
        # ---------------------------------------
        product_remaining = (
            total_required  - total_already_paid
        )

        pay_for_product = Decimal("0.00")

        if product_remaining > 0:

            pay_for_product = min(
                product_remaining,
                remaining_payment
            )

            orderdisp.amount_paid = (
                total_already_paid
                + pay_for_product
            )

            remaining_payment -= pay_for_product

        # ---------------------------------------
        # 3) CHECK FULLY PAID
        # ---------------------------------------
        orderdisp.fully_paid = (
            orderdisp.amount_paid >= total_required
        )


        # ---------------------------------------
        # SET FULLY PAID TIME
        # ONLY FIRST TIME
        # ---------------------------------------
        if (
            orderdisp.fully_paid
            and not orderdisp.fully_paid_at
        ):

            orderdisp.fully_paid_at = timezone.now()

        # ---------------------------------------
        # PAYMENT DETAILS
        # ---------------------------------------

        orderdisp.save()

        # ---------------------------------------
        # LOYALTY POINTS
        # ONLY FIRST FULL PAYMENT
        # ---------------------------------------
        # if (
        #     order.fully_paid
        #     and not order.points_awarded
        # ):

        #     purchase_value = total_price

        #     earned_points = int(

        #         Decimal('0.04')

        #         * purchase_value

        #         * 10
        #     )

        #     if product.promotion_multiple:

        #         earned_points *= int(
        #             product.promotion_multiple
        #         )

        #     loyalty_category, _ = (
        #         LoyaltyPointsCategory.objects.get_or_create(
        #             category='points on purchases made'
        #         )
        #     )

        #     added_by = (
        #         f'{recorded_by.first_name} '
        #         f'{recorded_by.last_name}'
        #         if (
        #             recorded_by
        #             and recorded_by.first_name
        #         )
        #         else (
        #             recorded_by.username
        #             if recorded_by
        #             else "system"
        #         )
        #     )

        #     LoyaltyPoint.objects.create(

        #         customer=order.member,

        #         business=product.business,

        #         category=loyalty_category,

        #         purchase_value=purchase_value,

        #         points_earned=earned_points,

        #         added_by=added_by,

        #         points_were='earned'
        #     )

            # ---------------------------------------
            # REFERRAL POINTS
            # ---------------------------------------
            # if (

            #     order.member.reffered_by

            #     and hasattr(
            #         order.member.reffered_by,
            #         'customer'
            #     )
            # ):

            #     referrer = (
            #         order.member.reffered_by.customer
            #     )

            #     ref_points = int(

            #         Decimal('0.01')

            #         * purchase_value

            #         * 10
            #     )

            #     ref_category, _ = (
            #         LoyaltyPointsCategory.objects.get_or_create(
            #             category='points from refferal sales'
            #         )
            #     )

            #     LoyaltyPoint.objects.create(

            #         customer=referrer,

            #         business=product.business,

            #         category=ref_category,

            #         points_earned=ref_points,

            #         added_by=added_by,

            #         points_were='earned'
            #     )

            # order.points_awarded = True

            # order.save(update_fields=['points_awarded'])

        return orderdisp
 
def process_bulk_payment(payment, payment_method='', send_to_accounting=True):

    if payment.processed:
        return

    with transaction.atomic():

        api_key_value = APIKey.objects.filter(
            active=True
        ).first()
        if not api_key_value:
            raise ValueError("No active API key found")
        
        total_paid = Decimal(str(payment.amount_paid))
       
        amount_due= 0
        transport_balance = payment.dispatch.total_transport_cost
        amount_due += transport_balance

        amount_to_apply = min(amount_due, total_paid)

        if amount_to_apply > 0:
            process_dispatch_payment(
                dispatch=payment.dispatch,
                amount=amount_to_apply,
                reference_code=payment.mpesa_receipt if payment.mpesa_receipt else '',
                payment_method=payment_method,
                api_key=api_key_value,
                recorded_by=None,
                send_to_accounting=send_to_accounting,
                skip_reference_check=True
            )
            total_paid -= amount_to_apply
        if total_paid > 0:            
            payment.unallocated_amount = total_paid

        payment.processed = True
        payment.status = "EXTRA_PAID" if total_paid > 0 else  "PROCESSED"
        payment.paid_at = timezone.now()
        payment.save()

# ============================================
# MPESA STK PUSH
# ============================================


def generate_mpesa_access_token():

    consumer_key = settings.MPESA_CONSUMER_KEY
    consumer_secret = settings.MPESA_CONSUMER_SECRET

    url = (
        "https://api.safaricom.co.ke/oauth/v1/generate"
        "?grant_type=client_credentials"
    )

    response = requests.get(
        url,
        auth=(consumer_key, consumer_secret),
        timeout=30
    )

    data = response.json()

    return data["access_token"]



def stk_push(phone_number, amount, account_reference, call_back_url):

    access_token = generate_mpesa_access_token()

    timestamp = timezone.now().strftime(
        "%Y%m%d%H%M%S"
    )

    password = base64.b64encode(
        (
            settings.MPESA_SHORTCODE
            + settings.MPESA_PASSKEY
            + timestamp
        ).encode()
    ).decode()

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    payload = {
        "BusinessShortCode": settings.MPESA_SHORTCODE,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": int(amount),
        "PartyA": phone_number,
        "PartyB": settings.MPESA_SHORTCODE,
        "PhoneNumber": phone_number,
        "CallBackURL": call_back_url,
        "AccountReference": account_reference,
        "TransactionDesc": "Order Payment"
    }

    response = requests.post(
        settings.MPESA_STK_URL,
        json=payload,
        headers=headers,
        timeout=60
    )

    return response.json()

@csrf_exempt
# ============================================
# MAIN VIEW
# ============================================



@csrf_exempt
def mpesa_stk_push(request):

    if request.method != "POST":
        return JsonResponse({
            "success": False,
            "message": "Invalid request method"
        }, status=405)

    try:
        data = json.loads(request.body)

        phone_number = data.get("customer_phone")
        paying_phone_number = data.get("paying_phone_number")
        frontend_amount = Decimal(str(data.get("amount", "0")))
        dispatch_id = data.get("dispatch_id")

        if not phone_number:
            return JsonResponse({
                "success": False,
                "message": "Phone number required"
            })
        
        phone_number = format_kenyan_phone_number(phone_number)
        paying_phone_number = format_kenyan_phone_number(paying_phone_number)

        if not dispatch_id:
            return JsonResponse({
                "success": False,
                "message": "No orders selected"
            })
        dispatch = PackageDispatch.objects.filter(id=dispatch_id).first()

        backend_amount = dispatch.total_transport_cost
        
        if backend_amount >= 10 and frontend_amount > backend_amount:
            return JsonResponse({
                "success": False,
                "message": (
                    f"Amount you want to pay is greater than required amount. "
                    f"Frontend={frontend_amount}, "
                    f"Backend={backend_amount}"
                )
            })
        if frontend_amount < Decimal(str(10)) : 
            return JsonResponse({
                "success": False,
                "message": (
                    f"amount paid must exceed 10ksh"
                    f"Frontend={frontend_amount}, "
                    f"Backend={backend_amount}"
                )
            })
        amount = frontend_amount  

        customer, created = Customer.objects.get_or_create(
            phone_number=phone_number,
            defaults={
                "name": "Customer",
            }
        ) 
        payment = MpesaTransaction.objects.create(
            phone_number=phone_number,
            customer=customer,
            amount=amount,
            dispatch=dispatch,
            status="PENDING"
        )

        response = stk_push(
            phone_number=paying_phone_number,
            amount=amount,
            account_reference=f"Your-order-#{payment.id}",
            call_back_url = f"{request.scheme}://{request.get_host()}/payments/payment_callback/"
        )

        if response.get("ResponseCode") == "0":

            payment.checkout_request_id = response.get(
                "CheckoutRequestID"
            )

            payment.merchant_request_id = response.get(
                "MerchantRequestID"
            )

            payment.status = "STK_SENT"
            payment.save()

            return JsonResponse({
                "success": True,
                "checkout_request_id": payment.checkout_request_id
            })

        payment.status = "FAILED"
        payment.failure_reason = response.get(
            "errorMessage",
            response.get("ResponseDescription", "STK failed")
        )
        payment.save()

        return JsonResponse({
            "success": False,
            "message": payment.failure_reason
        })

    except Exception as e:
        return JsonResponse({
            "success": False,
            "message": str(e)
        })


@csrf_exempt
def mpesa_payment_callback(request):

    try:
        data = json.loads(request.body)

        callback = data["Body"]["stkCallback"]

        checkout_id = callback["CheckoutRequestID"]
        result_code = callback["ResultCode"]
        result_desc = callback["ResultDesc"]

        payment = MpesaTransaction.objects.get(
            checkout_request_id=checkout_id
        )

        if payment.status == "SUCCESS":
            return JsonResponse({"ResultCode": 0})

        if result_code != 0:

            payment.status = "FAILED"
            payment.failure_reason = result_desc
            payment.save()

            return JsonResponse({"ResultCode": 0})

        metadata = {}

        for item in callback["CallbackMetadata"]["Item"]:
            metadata[item["Name"]] = item.get("Value")

        payment.mpesa_receipt = metadata.get("MpesaReceiptNumber")
        payment.phone_number = str(
            metadata.get("PhoneNumber", payment.phone_number)
        )

        payment.amount_paid = Decimal(
            str(metadata.get("Amount", payment.amount))
        )
        payment.result_code = result_code
        payment.result_desc = result_desc
        payment.raw_callback = callback
        payment.status = "SUCCESS"
        payment.save()

        process_bulk_payment(payment, payment_method='M-pesa')

        return JsonResponse({
            "ResultCode": 0,
            "ResultDesc": "Accepted"
        })

    except Exception as e:

        print("CALLBACK ERROR:", str(e))

        return JsonResponse({
            "ResultCode": 0,
            "ResultDesc": "Accepted"
        })

def mpesa_payment_status(request, checkout_id):

    try:
        tx = MpesaTransaction.objects.get(
            checkout_request_id=checkout_id
        )

        status_messages = {
            "PENDING": {
                "message": "⏳ Your payment request is being prepared. Please wait..."
            },

            "STK_SENT": {
                "message": "📱 We have sent an M-Pesa prompt to your phone. Please check your device and enter your M-Pesa PIN to complete the payment."
            },

            "SUCCESS": {
                "message": "✅ Payment received successfully. We are now updating your order. Please do not leave this page."
            },

            "PROCESSING": {
                "message": "🔄 Your payment has been received and is being processed. This may take a little longer than usual. Please be patient and do not leave this page while we update your order."
            },

            "PROCESSED": {
                "message": "🎉 Everything has been updated successfully. Your payment and order have been processed."
            },

            "FAILED": {
                "message": f"❌ Payment failed. {tx.result_desc or 'Please try again or contact customer care.'}"
            },

            "EXTRA_PAID": {
                "message": "⚠️ Your payment was received, but the amount paid exceeds the required amount. Please contact customer care for assistance."
            }
        }

        return JsonResponse({
            "success": True,
            "status": tx.status,
            "receipt": tx.mpesa_receipt,
            "message": status_messages.get(
                tx.status,
                {"message": "Processing payment..."}
            )["message"]
        })

    except MpesaTransaction.DoesNotExist:

        return JsonResponse({
            "success": False,
            "status": "NOT_FOUND",
            "message": "Payment record not found."
        })






@require_POST
@transaction.atomic
def wallet_payment(request):

    try:

        body = json.loads(request.body)

        customer_phone = body["customer_phone"]
        amount = Decimal(str(body["amount"]))
        dispatch_id = body["dispatch_id"]
        
        if not dispatch_id:
            return JsonResponse({
                "success": False,
                "message": "No orders selected"
            })
        dispatch = PackageDispatch.filter(id=dispatch_id).first()

        # ----------------------------------
        # Check wallet balance
        # ----------------------------------
        api_key_value = APIKey.objects.filter(active=True).first()


        form_data = {
            "phone": customer_phone,
            "api_key": api_key_value.key
        }

        response = requests.post(
            "https://accounts.garantiimall.shop/ajax/get-or-create-wallet/",
            data=form_data,
            timeout=20
        )

        if response.status_code != 200:
            return JsonResponse({
                "success": False,
                "message": "failed to contact wallet server."
            })

        wallet = response.json()

        if not wallet.get("success"):
            return JsonResponse({
                "success": False,
                "message": wallet.get(
                    "error",
                    "Wallet not found."
                )
            })

        wallet_balance = Decimal(
            str(wallet["wallet_balance"])
        )

        amount_to_apply = min(wallet_balance, amount)

        # ----------------------------------
        # Create local payment
        # ----------------------------------
        customer, created = Customer.objects.get_or_create(
            phone_number=customer_phone,
            defaults={
                "name": "Customer",
            }
        ) 

        payment = MpesaTransaction.objects.create(

            amount=amount_to_apply,
            customer=customer,
            phone_number=customer_phone,
            status="SUCCESS",
            result_code=0,
            result_desc="Wallet Payment",
            dispatch=dispatch

        )

        # ----------------------------------
        # Process payment
        # ----------------------------------

        process_bulk_payment(
            payment,
            payment_method="Wallet"
        )

        return JsonResponse({

            "success": True,

            "message": "Payment completed."

        })

    except Exception as e:

        return JsonResponse({

            "success": False,

            "message": str(e)

        })
    

def sync_accounting_transactions(id=None):

    api_key = APIKey.objects.filter(
        active=True
    ).first()

    if not api_key:
        raise Exception(
            "No active API key found"
        )

    if id:
        pending = (
        PendingAccountingTransaction.objects
        .filter(id=id, synced=False)
    )
    else:
        pending = (
            PendingAccountingTransaction.objects
            .filter(synced=False)
            .order_by("id")[:20]
        )

    for tx in pending:

        try:

            response = requests.post(
                "https://accounts.garantiimall.shop/add-transaction/",
                data={
                    "api_key": api_key.key,
                    "customer_phone": tx.customer_phone,
                    "customer_name": tx.customer_name,
                    "transaction_type": tx.transaction_type,
                    "project_phone": tx.project_phone,
                    "account_number": tx.account_number,
                    "amount": str(tx.amount),
                    "subcategory_name": tx.subcategory_name,
                    "wallet_flow": tx.wallet_flow,
                    "reference_code": tx.reference_code,
                    "description": tx.description,
                },
                timeout=(5, 40)
            )

            response.raise_for_status()

            try:
                data = response.json()
            except Exception:
                raise Exception(
                    "Accounting server returned invalid JSON"
                )

            if not data.get("success"):
                raise Exception(
                    data.get("error")
                    or "Unknown accounting error"
                )

            tx.synced = True
            tx.last_error = ""

            tx.save(
                update_fields=[
                    "synced",
                    "last_error"
                ]
            )

        except Exception as e:

            tx.sync_attempts += 1
            tx.last_error = str(e)

            tx.save(
                update_fields=[
                    "sync_attempts",
                    "last_error"
                ]
            )

# cron tasks for updating accounting

from django.http import JsonResponse

def sync_accounting_view(request):
    try:
        sync_accounting_transactions()
        return JsonResponse({
            "success": True
        })
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": str(e)
        }, status=500)
    
@csrf_exempt
def get_customer_points(request):

    phone = request.POST.get("phone")

    customer = Customer.objects.filter(
        phone_number=phone
    ).first()

    if not customer:
        return JsonResponse({
            "success":False,
            "error":"Customer not found."
        })

    # earned = (
    #     LoyaltyPoint.objects.filter(
    #         customer=customer,
    #         status="approved"
    #     ).aggregate(
    #         total=Sum("points_earned")
    #     )["total"] or 0
    # )

    # redeemed = (
    #     LoyaltyPoint.objects.filter(
    #         customer=customer,
    #         status="approved"
    #     ).aggregate(
    #         total=Sum("points_redeemed")
    #     )["total"] or 0
    # )

    # balance = earned - redeemed
    balance = 0
    value = balance/100

    return JsonResponse({

        "success":True,

        "available_points":balance,

        "value":value,   # 100 point = 1 shilling

    })

@require_POST
def pay_using_points(request):

    body=json.loads(request.body)

    customer=Customer.objects.get(
        phone_number=body["customer_phone"]
    )

    amount=Decimal(str(body["amount"]))

    # earned=(
    #     LoyaltyPoint.objects.filter(
    #         customer=customer,
    #         status="approved"
    #     ).aggregate(
    #         total=Sum("points_earned")
    #     )["total"] or 0
    # )

    # redeemed=(
    #     LoyaltyPoint.objects.filter(
    #         customer=customer,
    #         status="approved"
    #     ).aggregate(
    #         total=Sum("points_redeemed")
    #     )["total"] or 0
    # )

    balance= 0 #earned-redeemed

    value = balance/100
  

    amount_to_apply = min(balance, value)

    with transaction.atomic():

        # LoyaltyPoint.objects.create(

        #     customer=customer,

        #     points_redeemed=int(amount_to_apply*100),

        #     added_by="Customer",

        #     points_were="redeemed",

        #     status="approved"

        # )
        payment = MpesaTransaction.objects.create(

            amount=amount_to_apply,
            customer=customer,
            phone_number=body["customer_phone"],
            status="SUCCESS",
            result_code=0,
            result_desc="points Payment",
            selected_orders=body["orders"]

        )

        process_bulk_payment(
            payment,
            send_to_accounting=False
        )

    return JsonResponse({

        "success":True

    })