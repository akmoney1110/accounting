# account/signals.py
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Sum
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Batch, Expense, Ledger, Transaction

User = get_user_model()


# ==========================================
# 1. AUTO-CREATE LEDGER FOR VENDORS/CLIENTS
# ==========================================
@receiver(post_save, sender=User)
def create_user_ledger(sender, instance, created, **kwargs):
    if created and getattr(instance, 'role', None) in [User.Roles.VENDOR, User.Roles.CLIENT]:
        Ledger.objects.get_or_create(user=instance)


# ==========================================
# 2. RECALCULATE BATCH EXPENSES
# ==========================================
from decimal import Decimal
from django.db.models import Sum
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Expense, Batch


@receiver([post_save, post_delete], sender=Expense)
def update_batch_expenses(sender, instance, **kwargs):
    batch = instance.batch
    if not batch:
        return

    total_exp = Expense.objects.filter(batch=batch).aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0.00')

    # Queryset .update() works now that the model field isn't masked by @property
    Batch.objects.filter(pk=batch.pk).update(total_batch_expenses=total_exp)

# ==========================================
# 3. RECALCULATE USER LEDGERS & BATCH PAYMENTS
# ==========================================
@receiver([post_save, post_delete], sender=Batch)
@receiver([post_save, post_delete], sender=Transaction)
def sync_financial_ledgers(sender, instance, **kwargs):
    users_to_sync = set()

    # --- A. Handle Batch Changes ---
    if isinstance(instance, Batch):
        if instance.user:
            users_to_sync.add(instance.user)

    # --- B. Handle Transaction Changes ---
    elif isinstance(instance, Transaction):
        if instance.user:
            users_to_sync.add(instance.user)

        # Sync linked batch payment totals
        if instance.batch:
            total_paid = Transaction.objects.filter(batch=instance.batch).aggregate(
                total=Sum('amount')
            )['total'] or Decimal('0.00')

            Batch.objects.filter(pk=instance.batch.pk).update(amount_paid=total_paid)

    # --- C. Re-calculate Ledger Balances ---
    if not users_to_sync:
        return

    # Wrap balance updates in an atomic block for integrity
    with transaction.atomic():
        for user in users_to_sync:
            # Lock the row to handle concurrent accounting entries safely
            ledger, _ = Ledger.objects.select_for_update().get_or_create(user=user)

            if user.role == User.Roles.VENDOR:
                # Vendor: Sum of BUY batches vs DISBURSEMENT payments
                total_billed = Batch.objects.filter(
                    user=user, 
                    transaction_type='BUY'
                ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')

                total_paid = Transaction.objects.filter(
                    user=user, 
                    transaction_type=Transaction.TransactionType.DISBURSEMENT
                ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

            elif user.role == User.Roles.CLIENT:
                # Client: Sum of SELL batches vs RECEIPT payments
                total_billed = Batch.objects.filter(
                    user=user, 
                    transaction_type='SELL'
                ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')

                total_paid = Transaction.objects.filter(
                    user=user, 
                    transaction_type=Transaction.TransactionType.RECEIPT
                ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            else:
                continue

            ledger.total_due_or_billed = total_billed
            ledger.total_paid_or_received = total_paid
            ledger.balance = total_billed - total_paid
            ledger.save()





# account/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Batch, Transaction, Ledger

@receiver([post_save, post_delete], sender=Batch)
def sync_ledger_on_batch_change(sender, instance, **kwargs):
    if instance.user:
        ledger, _ = Ledger.objects.get_or_create(user=instance.user)
        ledger.update_totals()

@receiver([post_save, post_delete], sender=Transaction)
def sync_ledger_on_transaction_change(sender, instance, **kwargs):
    if instance.user:
        ledger, _ = Ledger.objects.get_or_create(user=instance.user)
        ledger.update_totals()


# account/signals.py
from decimal import Decimal
from django.db.models import Sum
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Transaction, Batch, Ledger


@receiver([post_save, post_delete], sender=Transaction)
def sync_batch_and_ledger_on_transaction(sender, instance, **kwargs):
    """
    When a payment transaction is recorded:
    1. Recalculate Batch.amount_paid and save the batch.
    2. Recalculate Ledger totals.
    """
    batch = instance.batch
    if batch:
        # Sum all payments linked to this specific batch
        total_paid_for_batch = Transaction.objects.filter(
            batch=batch
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        # Update batch amount_paid without triggering full save recursion
        batch.amount_paid = total_paid_for_batch
        batch.payment_status = batch.calculate_payment_status()
        batch.save()

    # Sync User Ledger
    if instance.user:
        ledger, _ = Ledger.objects.get_or_create(user=instance.user)
        ledger.update_totals()

