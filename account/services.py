from django.db.models import Sum
from decimal import Decimal
from .models import Batch, Transaction, Expense

def get_vendor_summary(vendor_user):
    """Calculates total payable, total paid, and balance left for a vendor."""
    batches = Batch.objects.filter(vendor=vendor_user)
    total_due = sum(b.vendor_total_due for b in batches)
    
    total_paid = Transaction.objects.filter(user=vendor_user).aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0.00')
    
    return {
        'total_due': total_due,
        'total_paid': total_paid,
        'balance_left': total_due - total_paid
    }

def get_batch_net_profit(batch_id):
    """Calculates net profit for a specific batch after shrinkage and expenses."""
    batch = Batch.objects.get(id=batch_id)
    
    revenue = batch.client_total_billed
    vendor_cost = batch.vendor_total_due
    operational_expenses = batch.expenses.aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0.00')
    
    net_profit = revenue - (vendor_cost + operational_expenses)
    
    return {
        'revenue': revenue,
        'vendor_cost': vendor_cost,
        'expenses': operational_expenses,
        'net_profit': net_profit
    }
