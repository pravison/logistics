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


from customers.models import Customer, LoyaltyCard
from .models import MpesaTransaction, PendingAccountingTransaction
from logistics.models import PackageDispatch
from logistics.views import record_successful_parcel
from accounts.models import APIKey
from accounts.views import format_kenyan_phone_number

from transport_credit.models import TransportCredit, TransportCreditTransaction



# Create your views here.

from django.db import transaction

@transaction.atomic
def update_transport_credits(sender, receiver, amount_paid, transaction_type="credit"):
    """
    Give transport credit to both sender and receiver.

    sender: User/customer receiving sender credit
    receiver: User/customer receiving receiver credit
    amount_paid: Amount of transport paid
    transaction_type: "credit" or "debit"
    """

    credit = int((amount_paid * 0.05) / 2)
    sender_wallet, _ = TransportCredit.objects.get_or_create(
        customer=sender
    )

    receiver_wallet, _ = TransportCredit.objects.get_or_create(
        customer=receiver
    )

    # Update sender
    sender_wallet.balance += credit
    sender_wallet.save(update_fields=["balance"])

    TransportCreditTransaction.objects.create(
        wallet=sender_wallet,
        amount=credit,
        transaction_type=transaction_type,
        description="Sender transport credit"
    )

    # Update receiver
    receiver_wallet.balance += credit
    receiver_wallet.save(update_fields=["balance"])

    TransportCreditTransaction.objects.create(
        wallet=receiver_wallet,
        amount=credit,
        transaction_type=transaction_type,
        description="Receiver transport credit"
    )

    return sender_wallet, receiver_wallet

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
        # update loyalty card
        # ---------------------------------------
        if not orderdisp.loyalty_counted:

            record_successful_parcel(
                orderdisp.sending_customer
            )

            orderdisp.loyalty_counted = True
    
        orderdisp.save()

        # ---------------------------------------
        # transport credits
        # ONLY FIRST FULL PAYMENT
        # ---------------------------------------
        update_transport_credits(
            sender=orderdisp.sending_customer,
            receiver=orderdisp.receiving_customer,
            amount_paid=100,
            transaction_type="credit"
        )

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
        transport_balance = payment.dispatch.total_transport_cost - payment.dispatch.amount_paid
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


#using free transport,

@transaction.atomic
def use_free_transport(customer, dispatch):

    card = LoyaltyCard.objects.filter(
        customer=customer,
        is_open=True,
        reward_earned=True,
        reward_used=False
    ).first()

    if not card:
        return False

    # Create payment record
    remaining_transport_cost=dispatch.total_transport_cost - dispatch.amount_paid
    payment = MpesaTransaction.objects.create(
        amount= dispatch.total_transport_cost,
        amount_paid = remaining_transport_cost,
        customer=customer,
        phone_number=dispatch.sending_customer.phone_number,
        status="SUCCESS",
        result_code=0,
        result_desc="Transport paid by the company",
        dispatch=dispatch,
    )

    # Process accounting/payment
    process_bulk_payment(
        payment,
        send_to_accounting=False
    )

    card.reward_used = True
    card.is_open = False
    card.completed_at = timezone.now()
    card.save()

    # New card automatically becomes available
    LoyaltyCard.objects.create(
        customer=customer
    )

    return True


@require_POST
def use_free_reward(request):

    try:
        data = json.loads(request.body)

        customer_phone = data.get("customer_phone")
        dispatch_id = data.get("dispatch_id")

        if not customer_phone:
            return JsonResponse({
                "success": False,
                "message": "Customer phone number is required."
            })

        if not dispatch_id:
            return JsonResponse({
                "success": False,
                "message": "Dispatch is required."
            })

        customer = Customer.objects.filter(
            phone_number=customer_phone
        ).first()

        if not customer:
            return JsonResponse({
                "success": False,
                "message": "Customer not found."
            })

        dispatch = PackageDispatch.objects.filter(
            id=dispatch_id
        ).first()

        if not dispatch:
            return JsonResponse({
                "success": False,
                "message": "Parcel not found."
            })

        success = use_free_transport(
            customer=customer,
            dispatch=dispatch
        )

        if not success:
            return JsonResponse({
                "success": False,
                "message": "You do not have an available free transport reward."
            })

        return JsonResponse({
            "success": True,
            "message": "Congratulations! Your transport has been paid using your free reward."
        })

    except Exception as e:

        return JsonResponse({
            "success": False,
            "message": "Something went wrong while using your reward."
        }, status=500)


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
@require_POST
def get_customer_credits(request):

    phone = request.POST.get("phone")

    if not phone:
        return JsonResponse({
            "success": False,
            "error": "Customer phone number is required."
        })

    customer = Customer.objects.filter(
        phone_number=phone
    ).first()

    if not customer:
        return JsonResponse({
            "success": False,
            "error": "Customer not found."
        })

    credit_wallet = TransportCredit.objects.filter(
        customer=customer
    ).first()

    # Customer has no credit wallet yet
    if not credit_wallet:
        balance = Decimal("0")
    else:
        balance = credit_wallet.balance or Decimal("0")

    # 1  credits = KSh 1
    credit_value = balance / Decimal("1")

    return JsonResponse({
        "success": True,

        # Number of credits
        "available_points": float(balance),

        # KSh value of credits
        "value": float(credit_value),
    })


@require_POST
def pay_using_credit(request):

    try:
        body = json.loads(request.body)

    except json.JSONDecodeError:
        return JsonResponse({
            "success": False,
            "message": "Invalid request."
        }, status=400)

    customer_phone = body.get("customer_phone")
    amount_raw = body.get("amount")
    dispatch_id = body.get("dispatch_id")

    if not customer_phone:
        return JsonResponse({
            "success": False,
            "message": "Customer phone number is required."
        }, status=400)

    if not amount_raw:
        return JsonResponse({
            "success": False,
            "message": "Payment amount is required."
        }, status=400)

    if not dispatch_id:
        return JsonResponse({
            "success": False,
            "message": "No dispatch selected."
        }, status=400)

    dispatch = PackageDispatch.objects.filter(id=dispatch_id).first()

    try:
        amount = Decimal(str(amount_raw))

    except (InvalidOperation, TypeError, ValueError):
        return JsonResponse({
            "success": False,
            "message": "Invalid payment amount."
        }, status=400)

    if amount <= 0:
        return JsonResponse({
            "success": False,
            "message": "Payment amount must be greater than zero."
        }, status=400)

    customer = Customer.objects.filter(
        phone_number=customer_phone
    ).first()

    if not customer:
        return JsonResponse({
            "success": False,
            "message": "Customer not found."
        }, status=404)

    with transaction.atomic():

        credit_wallet = TransportCredit.objects.select_for_update().filter(
            customer=customer
        ).first()

        if not credit_wallet:
            return JsonResponse({
                "success": False,
                "message": "Customer has no transport credit."
            })

        balance = credit_wallet.balance or Decimal("0")

        if balance <= 0:
            return JsonResponse({
                "success": False,
                "message": "Customer has no available credit."
            })

        remaining_transport_cost=dispatch.total_transport_cost - dispatch.amount_paid

        if remaining_transport_cost <= 0:
            return JsonResponse({
                "success": False,
                "message": "Not enough credit available."
            })

        # Convert KSh back to credits
        credits_to_use = balance * Decimal("1")

        # Make sure we never subtract more credits than available
        credits_to_use = min(
            credits_to_use,
            remaining_transport_cost
        )

        # Update wallet
        credit_wallet.balance -= credits_to_use

        credit_wallet.save(
            update_fields=["balance"]
        )

        # Create credit transaction
        TransportCreditTransaction.objects.create(
            wallet=credit_wallet,
            amount=credits_to_use,
            transaction_type="debit",
            description="Transport credit payment"
        )

        # Create payment record
        payment = MpesaTransaction.objects.create(
             amount= amount,
            amount_paid = credits_to_use,
            customer=customer,
            phone_number=customer_phone,
            status="SUCCESS",
            result_code=0,
            result_desc="Transport credit payment",
            dispatch=dispatch,
        )

        # Process accounting/payment
        process_bulk_payment(
            payment,
            send_to_accounting=False
        )

    return JsonResponse({
        "success": True,

        # Amount actually paid using credit
        "amount_paid": float(credits_to_use),

        # Credits actually used
        "credits_used": float(credits_to_use),

        # Remaining credits
        "remaining_credits": float(
            credit_wallet.balance
        ),

        # Remaining KSh value
        "remaining_value": float(
            credit_wallet.balance / Decimal("1")
        ),
    })