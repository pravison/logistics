# accounting/tasks.py

from celery import shared_task
from payments.services.accounting import sync_accounting_transactions


@shared_task
def sync_accounting_task():
    sync_accounting_transactions()