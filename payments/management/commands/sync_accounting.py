from django.core.management.base import BaseCommand
from payments.services.accounting import sync_accounting_transactions

class Command(BaseCommand):
    help = "Sync accounting transactions"

    def handle(self, *args, **kwargs):
        self.stdout.write("Starting sync...")

        sync_accounting_transactions()

        self.stdout.write("Sync completed.")