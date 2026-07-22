import requests
from accounts.models import APIKey
from payments.models import PendingAccountingTransaction

def sync_accounting_transactions():
    api_key = APIKey.objects.filter(active=True).first()

    if not api_key:
        raise Exception("No active API key found")

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
            data = response.json()

            if not data.get("success"):
                raise Exception(data.get("error") or "Unknown accounting error")

            tx.synced = True
            tx.last_error = ""

        except Exception as e:
            tx.sync_attempts += 1
            tx.last_error = str(e)

        tx.save(update_fields=["synced", "last_error", "sync_attempts"])