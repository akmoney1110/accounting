# account/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from decimal import Decimal
from decimal import Decimal, ROUND_HALF_UP


# ==========================================
# 1. CUSTOM USER MODEL
# ==========================================
from decimal import Decimal, ROUND_HALF_UP
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.utils import timezone


class User(AbstractUser):
    class Roles(models.TextChoices):
        ADMIN = 'ADMIN', 'Super Admin / Manager'
        VENDOR = 'VENDOR', 'Vendor / Supplier'
        CLIENT = 'CLIENT', 'Client / Buyer'

    role = models.CharField(max_length=10, choices=Roles.choices, default=Roles.ADMIN)
    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    credit_limit = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0.00'),
        help_text="Max credit limit allowed for Clients"
    )
    assigned_products = models.ManyToManyField(
        'Product', 
        through='UserProductRate', 
        related_name='associated_users',
        blank=True
    )



    def save(self, *args, **kwargs):
        # Automatically mark Admins as staff so they can access staff features if needed
        if self.role == self.Roles.ADMIN:
            self.is_staff = True
        else:
            self.is_staff = False
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.username} [{self.get_role_display()}]"

# account/models.py
from decimal import Decimal, ROUND_HALF_UP
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.utils import timezone




class Product(models.Model):
    name = models.CharField(max_length=100, unique=True)
    unit = models.CharField(max_length=20, default='kg', help_text="e.g. kg, bags, tons")
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.unit})"


class UserProductRate(models.Model):
    """Maps Vendors & Clients to products along with their buy/sell price."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='product_rates')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='user_rates')
    rate = models.DecimalField(
        max_digits=10, decimal_places=2, 
        help_text="Purchase price (if Vendor) or Sale price (if Client) per unit"
    )

    class Meta:
        unique_together = ('user', 'product')

    def __str__(self):
        role_label = "Vendor Selling Rate" if self.user.role == User.Roles.VENDOR else "Client Buying Rate"
        return f"{self.user.username} | {self.product.name} @ ${self.rate}/{self.product.unit} ({role_label})"

from decimal import Decimal, ROUND_HALF_UP
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model




from decimal import Decimal, ROUND_HALF_UP
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model




from decimal import Decimal, ROUND_HALF_UP
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from decimal import Decimal, ROUND_HALF_UP
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Batch(models.Model):
    class TransactionType(models.TextChoices):
        BUY = 'BUY', 'Buy from Vendor'
        SELL = 'SELL', 'Sell to Client'

    class PaymentStatus(models.TextChoices):
        NO_PAYMENT = 'NO_PAYMENT', 'No Payment'
        PARTIAL_PAYMENT = 'PARTIAL_PAYMENT', 'Partial Payment'
        FULL_PAYMENT = 'FULL_PAYMENT', 'Full Payment'

    batch_code = models.CharField(
        max_length=50, 
        unique=True, 
        blank=True, 
        help_text="Auto-generated if left empty (e.g. BUY-20260810-001)"
    )
    transaction_type = models.CharField(
        max_length=10, 
        choices=TransactionType.choices, 
        default=TransactionType.BUY
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.PROTECT, 
        related_name='batches',
        help_text="Vendor (for Purchases) or Client (for Sales)"
    )
    product = models.ForeignKey(
        'Product', 
        on_delete=models.PROTECT, 
        related_name='batches'
    )
    
    weight = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        help_text="Weight in kg"
    )
    dry_weight = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Weight after drying (~3 days). Leave blank if not dried yet."
    )
    applied_rate = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        blank=True, 
        help_text="Auto-fetched from User Product Rate if left blank"
    )
    total_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00')
    )
    
    # Stored Database Field (Updated by Expense Signals)
    total_batch_expenses = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00')
    )

    # Payment Tracking
    payment_status = models.CharField(
        max_length=20, 
        choices=PaymentStatus.choices, 
        default=PaymentStatus.NO_PAYMENT
    )
    amount_paid = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00')
    )
    
    transaction_date = models.DateField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Batch"
        verbose_name_plural = "Batches"
        ordering = ['-transaction_date', '-created_at']

    def __str__(self):
        return f"{self.batch_code} - {self.get_transaction_type_display()} ({self.weight}kg)"

    @property
    def balance_due(self):
        """Calculates remaining unpaid balance on this batch."""
        total = self.total_amount or Decimal('0.00')
        paid = self.amount_paid or Decimal('0.00')
        return max(Decimal('0.00'), total - paid)

    def calculate_payment_status(self):
        """Computes current payment status based on settlement amounts."""
        total = self.total_amount or Decimal('0.00')
        paid = self.amount_paid or Decimal('0.00')

        if total > Decimal('0.00') and paid >= total:
            return self.PaymentStatus.FULL_PAYMENT
        elif paid > Decimal('0.00'):
            return self.PaymentStatus.PARTIAL_PAYMENT
        return self.PaymentStatus.NO_PAYMENT

    def generate_batch_code(self):
        """Generates sequential batch code in format: [BUY/SELL]-YYYYMMDD-001"""
        t_date = self.transaction_date or timezone.now().date()
        if hasattr(t_date, 'strftime'):
            date_str = t_date.strftime('%Y%m%d')
        else:
            date_str = timezone.now().strftime('%Y%m%d')

        prefix = f"{self.transaction_type}-{date_str}-"
        
        last_batch = Batch.objects.filter(
            batch_code__startswith=prefix
        ).order_by('-id').first()

        if last_batch and last_batch.batch_code:
            try:
                last_num = int(last_batch.batch_code.split('-')[-1])
                new_num = last_num + 1
            except (ValueError, IndexError):
                new_num = 1
        else:
            new_num = 1

        return f"{prefix}{new_num:03d}"

    def clean(self):
        super().clean()
        
        # ============================================================
        # 1. ROLE COMPATIBILITY
        # ============================================================
        if self.user_id:
            user_role = getattr(self.user, 'role', None)
            
            if self.transaction_type == self.TransactionType.BUY and str(user_role).upper() != 'VENDOR':
                raise ValidationError({'user': 'A BUY transaction requires selecting a Vendor.'})
            
            if self.transaction_type == self.TransactionType.SELL and str(user_role).upper() != 'CLIENT':
                raise ValidationError({'user': 'A SELL transaction requires selecting a Client.'})

        # ============================================================
        # 2. DRY WEIGHT VALIDATION
        # ============================================================
        dry = getattr(self, 'dry_weight', None)
        if dry is not None and dry > Decimal('0.00'):
            wet = self.weight or Decimal('0.00')
            if dry > wet:
                raise ValidationError({
                    'dry_weight': f"Dry weight ({dry}kg) cannot exceed received weight ({wet}kg)."
                })
   
                
    @property
    def moisture_loss(self):
        """Weight lost during the drying process."""
        if self.dry_weight is None:
            return Decimal('0.00')
        wet = self.weight or Decimal('0.00')
        dry = self.dry_weight or Decimal('0.00')
        return max(Decimal('0.00'), wet - dry)

    @property
    def effective_rate(self):
        """
        True cost per kg of dry product.
        Formula: (total_amount + total_batch_expenses) / dry_weight
        """
        if not self.dry_weight or self.dry_weight <= Decimal('0.00'):
            return Decimal('0.00')
        total_cost = (self.total_amount or Decimal('0.00')) + (self.total_batch_expenses or Decimal('0.00'))
        return (total_cost / self.dry_weight).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    def save(self, *args, **kwargs):
        def round_2(val):
            if val is None:
                return Decimal('0.00')
            return Decimal(str(val)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        # 1. Auto-generate Batch Code
        if not self.batch_code:
            self.batch_code = self.generate_batch_code()

        # 2. Auto-fetch pre-configured User Product Rate
        if self.user_id and self.product_id and (self.applied_rate is None or self.applied_rate == Decimal('0.00')):
            from .models import UserProductRate
            rate_obj = UserProductRate.objects.filter(user=self.user, product=self.product).first()
            if rate_obj:
                self.applied_rate = rate_obj.rate
            else:
                self.applied_rate = Decimal('0.00')

        # 3. Compute Total Amount
        if self.weight and self.applied_rate is not None:
            self.total_amount = round_2(Decimal(str(self.weight)) * Decimal(str(self.applied_rate)))

        # 4. Auto-update Payment Status
        self.payment_status = self.calculate_payment_status()

        self.full_clean()
        
        # Save batch instance
        super().save(*args, **kwargs)

        # 5. Sync User Ledger
        from .models import Ledger
        if hasattr(self.user, 'ledger'):
            self.user.ledger.update_totals()
        else:
            Ledger.objects.get_or_create(user=self.user)[0].update_totals()

    def update_payment_state(self):
        """Recalculate amount_paid and payment_status from PaymentAllocations."""
        from django.db.models import Sum
        
        total_paid = self.payment_allocations.aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')
        
        self.amount_paid = total_paid
        self.payment_status = self.calculate_payment_status()
        
        # Direct DB update to avoid recursion through full_clean/save signals
        Batch.objects.filter(pk=self.pk).update(
            amount_paid=self.amount_paid,
            payment_status=self.payment_status
        )
            
    @property
    def moisture_loss_percent(self):
        """Percentage of weight lost during drying."""
        if self.dry_weight is None or not self.weight or self.weight <= Decimal('0.00'):
            return Decimal('0.00')
        loss = self.moisture_loss
        return ((loss / self.weight) * 100).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    @property
    def net_position(self):
        """Total value minus operational expenses."""
        total = self.total_amount or Decimal('0.00')
        expenses = self.total_batch_expenses or Decimal('0.00')
        return total - expenses        
            
            
            
            
            # ==========================================
class Expense(models.Model):
    class ExpenseCategory(models.TextChoices):
        TRANSPORTATION = 'TRANSPORT', 'Transportation & Freight'
        FUEL = 'FUEL', 'Fuel & Energy'
        LABOR = 'LABOR', 'Labor & Offloading'
        PACKAGING = 'PACKAGING', 'Packaging & Supplies (Sacks/Bags)'
        STORAGE = 'STORAGE', 'Storage & Warehousing'
        QUALITY = 'QUALITY', 'Quality Inspection & Testing'
        SECURITY = 'SECURITY', 'Security & Logistics'
        LEVIES = 'LEVIES', 'Taxes & Local Levies'
        OTHER = 'OTHER', 'Miscellaneous / Other'

    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='expenses')
    batch = models.ForeignKey(
        Batch, 
        on_delete=models.SET_NULL,  # expense stays even if batch is deleted
        related_name='expenses',
        null=True, 
        blank=True,
        help_text="Leave empty for general overhead expenses"
    )
    category = models.CharField(max_length=20, choices=ExpenseCategory.choices)
    title = models.CharField(max_length=250, help_text="Short detail (e.g. 50L Diesel for mechanical dryer)")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    expense_date = models.DateField()
    receipt_reference = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        batch_code = self.batch.batch_code if self.batch else "General Expense"
        return f"{self.get_category_display()} - ₦{self.amount} ({batch_code})"

# ==========================================
# 5. FINANCIAL TRANSACTIONS
# ==========================================
class Transaction(models.Model):
    class PaymentMethod(models.TextChoices):
        BANK_TRANSFER = 'BANK_TRANSFER', 'Bank Transfer'
        CASH = 'CASH', 'Cash'
        CHEQUE = 'CHEQUE', 'Cheque'
        MOBILE_MONEY = 'MOBILE_MONEY', 'Mobile Money'

    class TransactionType(models.TextChoices):
        DISBURSEMENT = 'DISBURSEMENT', 'Payment to Vendor'
        RECEIPT = 'RECEIPT', 'Payment from Client'

    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name='transactions')
    batch = models.ForeignKey(Batch, on_delete=models.SET_NULL, blank=True, null=True, related_name='transactions')
    transaction_type = models.CharField(max_length=15, choices=TransactionType.choices)
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices, default=PaymentMethod.BANK_TRANSFER)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reference_code = models.CharField(max_length=100, help_text="Bank Ref, Cheque Number, or Receipt Code")
    transaction_date = models.DateField()
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    @property
    def unallocated_amount(self):
        """How much of this transaction is NOT yet allocated to any batch."""
        from django.db.models import Sum
        allocated = self.allocations.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        return (self.amount or Decimal('0.00')) - allocated

    @property
    def is_fully_allocated(self):
        return self.unallocated_amount <= Decimal('0.00')

    def __str__(self):
        return f"{self.get_transaction_type_display()} - ${self.amount} ({self.user.username})"


# ==========================================
# 6. AUTOMATED USER LEDGER
# ==========================================


# account/models.py
from decimal import Decimal
from django.db.models import Sum

class Ledger(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='ledger')
    total_due_or_billed = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    total_paid_or_received = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    balance = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    last_synced_at = models.DateTimeField(auto_now=True)

    def update_totals(self):
        """Recalculate ledger: Batches = debt, Transactions = credits."""
        user = self.user

        # 1. Total Billed / Obligated from Batches
        batch_total = Batch.objects.filter(user=user).aggregate(
            total=Sum('total_amount')
        )['total'] or Decimal('0.00')

        # 2. Total Paid / Settlement from ALL Transactions (regardless of batch link)
        transaction_total = Transaction.objects.filter(user=user).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')

        self.total_due_or_billed = batch_total
        self.total_paid_or_received = transaction_total
        self.balance = batch_total - transaction_total
        self.save()






# ==========================================
# 4b. PAYMENT ALLOCATIONS (User Credit → Batch)
# ==========================================

class PaymentAllocation(models.Model):
    """
    Links a user-level Transaction to a specific Batch.
    Allows one payment to be split across multiple batches.
    """
    transaction = models.ForeignKey(
        'Transaction', 
        on_delete=models.CASCADE, 
        related_name='allocations'
    )
    batch = models.ForeignKey(
        'Batch', 
        on_delete=models.CASCADE, 
        related_name='payment_allocations'
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    allocated_at = models.DateTimeField(auto_now_add=True)
    allocated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )

    class Meta:
        ordering = ['-allocated_at']
        constraints = [
            models.UniqueConstraint(
                fields=['transaction', 'batch'], 
                name='unique_allocation_per_batch_txn'
            )
        ]

    def __str__(self):
        return f"₦{self.amount:,.2f} → {self.batch.batch_code}"

    def clean(self):
        from django.db.models import Sum
        from django.core.exceptions import ValidationError

        if self.transaction_id and self.batch_id:
            # 1. User must match
            if self.transaction.user_id != self.batch.user_id:
                raise ValidationError({
                    'transaction': 'Transaction user must match batch user.'
                })

            # 2. Can't allocate more than the transaction's unallocated amount
            allocated_qs = PaymentAllocation.objects.filter(transaction=self.transaction)
            if self.pk:
                allocated_qs = allocated_qs.exclude(pk=self.pk)
            allocated = allocated_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

            available = (self.transaction.amount or Decimal('0.00')) - allocated
            if self.amount > available:
                raise ValidationError({
                    'amount': f"Allocation (₦{self.amount:,.2f}) exceeds available unallocated funds (₦{available:,.2f})."
                })

            # 3. Can't allocate more than batch balance due
            batch_balance = self.batch.balance_due
            if self.amount > batch_balance:
                raise ValidationError({
                    'amount': f"Allocation (₦{self.amount:,.2f}) exceeds batch balance due (₦{batch_balance:,.2f})."
                })













# ==========================================
# SIGNALS: Auto-update Batch when Transactions change
# ==========================================
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

# ==========================================
# SIGNALS
# ==========================================
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

@receiver(post_save, sender=Transaction)
def transaction_post_save(sender, instance, created, **kwargs):
    # Update batch if directly linked (legacy support)
    if instance.batch:
        instance.batch.update_payment_state()
    
    # Always update user ledger
    if hasattr(instance.user, 'ledger'):
        instance.user.ledger.update_totals()
    else:
        Ledger.objects.get_or_create(user=instance.user)[0].update_totals()

@receiver(post_delete, sender=Transaction)
def transaction_post_delete(sender, instance, **kwargs):
    if instance.batch:
        instance.batch.update_payment_state()
    if hasattr(instance.user, 'ledger'):
        instance.user.ledger.update_totals()

@receiver(post_save, sender=PaymentAllocation)
def allocation_post_save(sender, instance, created, **kwargs):
    instance.batch.update_payment_state()

@receiver(post_delete, sender=PaymentAllocation)
def allocation_post_delete(sender, instance, **kwargs):
    instance.batch.update_payment_state()





# ==========================================
# 4b. PAYMENT ALLOCATIONS (User Credit → Batch)
# ==========================================


@receiver(post_save, sender=Expense)
def expense_post_save(sender, instance, created, **kwargs):
    """Auto-update batch total when expense is added/edited."""
    if instance.batch:
        total = instance.batch.expenses.aggregate(t=Sum('amount'))['t'] or Decimal('0.00')
        Batch.objects.filter(pk=instance.batch.pk).update(total_batch_expenses=total)

@receiver(post_delete, sender=Expense)
def expense_post_delete(sender, instance, **kwargs):
    """Auto-update batch total when expense is deleted."""
    if instance.batch:
        total = instance.batch.expenses.aggregate(t=Sum('amount'))['t'] or Decimal('0.00')
        Batch.objects.filter(pk=instance.batch.pk).update(total_batch_expenses=total)