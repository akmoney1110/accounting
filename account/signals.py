# account/signals.py
import threading
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import transaction as db_transaction
from django.db.models import F, Q, Sum, DecimalField
from django.db.models.functions import Coalesce
from django.db.models.signals import post_delete, post_save, pre_delete
from django.dispatch import receiver

from .models import Batch, Expense, Ledger, PaymentAllocation, Transaction

User = get_user_model()

# Thread-local flag to suppress reallocation signals during batch deletion
_deletion_context = threading.local()


def batch_deletion_in_progress():
    return getattr(_deletion_context, 'batch_deletion', False)


def set_batch_deletion(value):
    _deletion_context.batch_deletion = value


# ==========================================
# CORE ALLOCATION ENGINE
# ==========================================
def _batch_exists(batch):
    """Check if a batch still exists in the database."""
    if not batch or not batch.pk:
        return False
    return Batch.objects.filter(pk=batch.pk).exists()


def _allocate_transaction(txn, priority_batch=None):
    """
    Allocate a transaction's unallocated amount to outstanding batches.

    Rules:
      1. If priority_batch is provided (e.g. a brand-new batch), pay it FIRST.
      2. Then pay the transaction's linked batch (if any and still outstanding).
      3. Then cascade to other outstanding batches (oldest first / FIFO).
      4. Finally sync the user's ledger.

    This is idempotent — calling it multiple times only allocates what remains.
    """
    txn.refresh_from_db()

    if (txn.amount or Decimal('0.00')) <= Decimal('0.00'):
        return

    # Determine matching batch type
    if txn.transaction_type == Transaction.TransactionType.DISBURSEMENT:
        batch_type = Batch.TransactionType.BUY
    else:
        batch_type = Batch.TransactionType.SELL

    remaining = txn.unallocated_amount
    if remaining <= Decimal('0.00'):
        return

    with db_transaction.atomic():
        # Lock the transaction row to prevent race conditions
        txn = Transaction.objects.select_for_update().get(pk=txn.pk)
        remaining = txn.unallocated_amount
        if remaining <= Decimal('0.00'):
            return

        # --- 1. Pay priority batch first (if provided & still exists & applicable) ---
        if priority_batch and _batch_exists(priority_batch) and priority_batch.transaction_type == batch_type:
            priority_batch.refresh_from_db()
            bal = priority_batch.balance_due
            if bal > Decimal('0.00'):
                alloc = min(remaining, bal)
                PaymentAllocation.objects.create(
                    transaction=txn,
                    batch=priority_batch,
                    amount=alloc,
                    allocated_by=None
                )
                remaining = txn.unallocated_amount

        # --- 2. Pay linked batch (if different from priority & still exists & has balance) ---
        if remaining > Decimal('0.00'):
            linked = txn.batch
            if linked and linked != priority_batch and _batch_exists(linked):
                linked.refresh_from_db()
                if linked.transaction_type == batch_type:
                    bal = linked.balance_due
                    if bal > Decimal('0.00'):
                        alloc = min(remaining, bal)
                        PaymentAllocation.objects.create(
                            transaction=txn,
                            batch=linked,
                            amount=alloc,
                            allocated_by=None
                        )
                        remaining = txn.unallocated_amount

        # --- 3. Cascade to other outstanding batches (oldest first / FIFO) ---
        if remaining > Decimal('0.00'):
            exclude_pks = []
            if priority_batch and priority_batch.pk:
                exclude_pks.append(priority_batch.pk)
            if linked and linked.pk:
                exclude_pks.append(linked.pk)

            qs = Batch.objects.select_for_update().filter(
                user=txn.user,
                transaction_type=batch_type
            )
            if exclude_pks:
                qs = qs.exclude(pk__in=exclude_pks)

            outstanding = qs.annotate(
                due=F('total_amount') - Coalesce(F('amount_paid'), Decimal('0.00'), output_field=DecimalField())
            ).filter(due__gt=Decimal('0.00')).order_by('transaction_date', 'created_at')

            for batch in outstanding:
                if remaining <= Decimal('0.00'):
                    break
                batch.refresh_from_db()
                bal = batch.balance_due
                if bal <= Decimal('0.00'):
                    continue
                alloc = min(remaining, bal)
                PaymentAllocation.objects.create(
                    transaction=txn,
                    batch=batch,
                    amount=alloc,
                    allocated_by=None
                )
                remaining = txn.unallocated_amount

        # --- 4. Sync user ledger ---
        if hasattr(txn.user, 'ledger'):
            txn.user.ledger.update_totals()


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
@receiver([post_save, post_delete], sender=Expense)
def update_batch_expenses(sender, instance, **kwargs):
    batch = instance.batch
    if not batch or not _batch_exists(batch):
        return
    total_exp = Expense.objects.filter(batch=batch).aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0.00')
    Batch.objects.filter(pk=batch.pk).update(total_batch_expenses=total_exp)


# ==========================================
# 3. UPDATE BATCH + LEDGER WHEN ALLOCATIONS CHANGE
# ==========================================
@receiver([post_save, post_delete], sender=PaymentAllocation)
def update_batch_on_allocation_change(sender, instance, **kwargs):
    if instance.batch and _batch_exists(instance.batch):
        instance.batch.update_payment_state()
        if hasattr(instance.batch.user, 'ledger'):
            instance.batch.user.ledger.update_totals()


# ==========================================
# 4. REALLOCATE FREED CREDIT WHEN ALLOCATION IS REMOVED
# ==========================================
@receiver(post_delete, sender=PaymentAllocation)
def reallocate_freed_credit(sender, instance, **kwargs):
    """
    When an allocation is deleted (e.g. admin removes it from a batch),
    the credit becomes unallocated again. Automatically try to push it to
    other outstanding batches.

    SAFETY: If a batch is currently being deleted, skip reallocation here.
    The deletion handler will explicitly reallocate after the batch is gone.
    """
    if batch_deletion_in_progress():
        return
    if instance.transaction:
        _allocate_transaction(instance.transaction)


# ==========================================
# 5. SYNC USER LEDGER ON BATCH CHANGES
# ==========================================
@receiver([post_save, post_delete], sender=Batch)
def sync_ledger_on_batch_change(sender, instance, **kwargs):
    if instance.user and hasattr(instance.user, 'ledger'):
        instance.user.ledger.update_totals()


# ==========================================
# 6. AUTO-ALLOCATE NEW TRANSACTIONS
# ==========================================
@receiver(post_save, sender=Transaction)
def auto_allocate_transaction(sender, instance, created, **kwargs):
    """
    When a new payment is recorded, automatically allocate it to
    outstanding batches. Linked batch is paid first, then oldest others.
    """
    if not created:
        return
    _allocate_transaction(instance)


# ==========================================
# 7. AUTO-APPLY EXISTING CREDIT TO NEW BATCHES
# ==========================================
@receiver(post_save, sender=Batch)
def auto_allocate_on_batch_create(sender, instance, created, **kwargs):
    """
    When a brand-new batch is created, check if the user already has
    unallocated payments sitting in their account. If so, pay this new
    batch first, then cascade to older batches.
    """
    if not created:
        return

    if instance.transaction_type == Batch.TransactionType.BUY:
        txn_type = Transaction.TransactionType.DISBURSEMENT
    else:
        txn_type = Transaction.TransactionType.RECEIPT

    unallocated_txns = Transaction.objects.filter(
        user=instance.user,
        transaction_type=txn_type
    ).annotate(
        allocated=Sum('allocations__amount')
    ).filter(
        Q(allocated__lt=F('amount')) | Q(allocated__isnull=True)
    ).order_by('transaction_date', 'created_at')

    for txn in unallocated_txns:
        _allocate_transaction(txn, priority_batch=instance)


# ==========================================
# 8. SYNC LEDGER ON TRANSACTION DELETE
# ==========================================
@receiver(pre_delete, sender=Transaction)
def capture_batches_before_txn_delete(sender, instance, **kwargs):
    """Store affected batch IDs so we can refresh them after deletion."""
    instance._affected_batch_ids = list(
        instance.allocations.values_list('batch_id', flat=True)
    )


@receiver(post_delete, sender=Transaction)
def sync_ledger_on_transaction_delete(sender, instance, **kwargs):
    """When a transaction is deleted, refresh ledger and all affected batches."""
    if instance.user and hasattr(instance.user, 'ledger'):
        instance.user.ledger.update_totals()

    batch_ids = getattr(instance, '_affected_batch_ids', [])
    for batch in Batch.objects.filter(pk__in=batch_ids):
        batch.update_payment_state()