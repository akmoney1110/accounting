# account/forms.py
from decimal import Decimal
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import User, Product, UserProductRate, Batch, Expense, Transaction


# Utility class mixin for Tailwind UI styling
TWIND_INPUT = (
    "w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-slate-800 "
    "bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent text-sm transition-all"
)


class BaseStyledForm(forms.ModelForm):
    """Applies clean Tailwind classes to form inputs automatically."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            current_class = field.widget.attrs.get('class', '')
            if 'w-full' not in current_class:
                field.widget.attrs['class'] = f"{TWIND_INPUT} {current_class}".strip()


class CustomLoginForm(AuthenticationForm):
    """Custom Login Form styled with modern Tailwind CSS."""
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': TWIND_INPUT, 
            'placeholder': 'Username or Email',
            'autofocus': True
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': TWIND_INPUT, 
            'placeholder': 'Password'
        })
    )


from decimal import Decimal
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Batch, Product,PaymentAllocation

class BatcForm(BaseStyledForm):
    """Unified BUY/SELL Batch Form with partial payment support."""

    amount_paid_now = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        initial=Decimal('0.00'),
        label="Amount Paid Now",
        widget=forms.NumberInput(attrs={
            'placeholder': '0.00 (Leave 0 if fully unpaid)',
            'id': 'id_amount_paid_now',
            'step': '0.01'
        }),
        help_text="Enter initial or partial payment made during batch creation."
    )

    class Meta:
        model = Batch
        fields = [
            'transaction_type', 
            'user', 
            'product', 
            'weight', 
            'dry_weight',
            'applied_rate', 
            'amount_paid_now', 
            'transaction_date'
        ]
        widgets = {
            'transaction_type': forms.Select(attrs={
                'class': f"{TWIND_INPUT} font-semibold",
                'id': 'id_transaction_type'
            }),
            'user': forms.Select(attrs={'id': 'id_user'}),
            'product': forms.Select(attrs={'id': 'id_product'}),
            'weight': forms.NumberInput(attrs={
                'placeholder': 'Enter weight in kg', 
                'id': 'id_weight',
                'step': '0.01'
            }),
            'dry_weight': forms.NumberInput(attrs={
                'placeholder': 'Weight after drying (leave blank if not ready)',
                'id': 'id_dry_weight',
                'step': '0.01'
            }),
            'applied_rate': forms.NumberInput(attrs={
                'placeholder': 'Auto-filled from user profile rate', 
                'id': 'id_applied_rate',
                'step': '0.01'
            }),
            'transaction_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['applied_rate'].required = False
        
        # Populate active products only
        self.fields['product'].queryset = Product.objects.filter(is_active=True)
        
        # Set default transaction date to today if creating new batch
        if not self.instance.pk and 'transaction_date' in self.fields:
            self.fields['transaction_date'].initial = timezone.now().date()

    def clean_weight(self):
        weight = self.cleaned_data.get('weight')
        if weight is not None and weight <= Decimal('0.00'):
            raise ValidationError("Weight must be greater than 0 kg.")
        return weight

    def clean_applied_rate(self):
        applied_rate = self.cleaned_data.get('applied_rate')
        if applied_rate is not None and applied_rate < Decimal('0.00'):
            raise ValidationError("Rate cannot be negative.")
        return applied_rate

    def clean_amount_paid_now(self):
        amount_paid_now = self.cleaned_data.get('amount_paid_now') or Decimal('0.00')
        if amount_paid_now < Decimal('0.00'):
            raise ValidationError("Payment amount cannot be negative.")
        return amount_paid_now

    def clean(self):
        cleaned_data = super().clean()
        weight = cleaned_data.get('weight') or Decimal('0.00')
        applied_rate = cleaned_data.get('applied_rate') or Decimal('0.00')
        amount_paid_now = cleaned_data.get('amount_paid_now') or Decimal('0.00')

        # Total calculated value of batch
        total_amount = weight * applied_rate

        # Prevent entering an upfront payment larger than the total batch value
        if amount_paid_now > total_amount and total_amount > Decimal('0.00'):
            self.add_error(
                'amount_paid_now', 
                f"Initial payment ({amount_paid_now}) cannot exceed total batch value ({total_amount:.2f})."
            )
        return cleaned_data
    
    def clean_dry_weight(self):
        dry = self.cleaned_data.get('dry_weight')
        if dry is not None and dry < Decimal('0.00'):
            raise ValidationError("Dry weight cannot be negative.")
        return dry

    def clean(self):
        cleaned_data = super().clean()
        weight = cleaned_data.get('weight') or Decimal('0.00')
        dry_weight = cleaned_data.get('dry_weight')
        amount_paid_now = cleaned_data.get('amount_paid_now') or Decimal('0.00')
        applied_rate = cleaned_data.get('applied_rate') or Decimal('0.00')

        # Validate dry weight <= received weight
        if dry_weight is not None and dry_weight > weight:
            self.add_error('dry_weight', "Dry weight cannot exceed received weight.")

        total_amount = weight * applied_rate

        if amount_paid_now > total_amount and total_amount > Decimal('0.00'):
            self.add_error(
                'amount_paid_now',
                f"Initial payment ({amount_paid_now}) cannot exceed total batch value ({total_amount:.2f})."
            )
        return cleaned_data
class BatchForm(BaseStyledForm):
    """Unified BUY/SELL Batch Form with partial payment support."""

    amount_paid_now = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        initial=Decimal('0.00'),
        label="Amount Paid Now",
        widget=forms.NumberInput(attrs={
            'placeholder': '0.00 (Leave 0 if fully unpaid)',
            'id': 'id_amount_paid_now',
            'step': '0.01'
        }),
        help_text="Enter initial or partial payment made during batch creation."
    )

    class Meta:
        model = Batch
        fields = [
            'transaction_type', 
            'user', 
            'product', 
            'weight', 
            'dry_weight',
            'applied_rate', 
            'amount_paid_now', 
            'transaction_date'
        ]
        widgets = {
            'transaction_type': forms.Select(attrs={
                'class': f"{TWIND_INPUT} font-semibold",
                'id': 'id_transaction_type'
            }),
            'user': forms.Select(attrs={'id': 'id_user'}),
            'product': forms.Select(attrs={'id': 'id_product'}),
            'weight': forms.NumberInput(attrs={
                'placeholder': 'Enter weight in kg', 
                'id': 'id_weight',
                'step': '0.01'
            }),
            'dry_weight': forms.NumberInput(attrs={
                'placeholder': 'Weight after drying (leave blank if not ready)',
                'id': 'id_dry_weight',
                'step': '0.01'
            }),
            'applied_rate': forms.NumberInput(attrs={
                'placeholder': 'Auto-filled from user profile rate', 
                'id': 'id_applied_rate',
                'step': '0.01'
            }),
            'transaction_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['applied_rate'].required = False
        self.fields['dry_weight'].required = False
        
        # Populate active products only
        self.fields['product'].queryset = Product.objects.filter(is_active=True)
        
        # ONLY show business partners (Vendors & Clients), never internal staff
        tx_type = self.data.get('transaction_type') if self.data else None
        if not tx_type and self.instance.pk:
            tx_type = self.instance.transaction_type
        
        user_qs = User.objects.filter(
            is_active=True,
            role__in=[User.Roles.VENDOR, User.Roles.CLIENT]
        )
        if tx_type == 'BUY':
            user_qs = user_qs.filter(role=User.Roles.VENDOR)
        elif tx_type == 'SELL':
            user_qs = user_qs.filter(role=User.Roles.CLIENT)
        self.fields['user'].queryset = user_qs
        
        # Set default transaction date to today if creating new batch
        if not self.instance.pk and 'transaction_date' in self.fields:
            self.fields['transaction_date'].initial = timezone.now().date()
    def clean_weight(self):
        weight = self.cleaned_data.get('weight')
        if weight is not None and weight <= Decimal('0.00'):
            raise ValidationError("Weight must be greater than 0 kg.")
        return weight

    def clean_applied_rate(self):
        applied_rate = self.cleaned_data.get('applied_rate')
        if applied_rate is not None and applied_rate < Decimal('0.00'):
            raise ValidationError("Rate cannot be negative.")
        return applied_rate

    def clean_dry_weight(self):
        dry = self.cleaned_data.get('dry_weight')
        if dry is not None and dry < Decimal('0.00'):
            raise ValidationError("Dry weight cannot be negative.")
        return dry

    def clean_amount_paid_now(self):
        amount_paid_now = self.cleaned_data.get('amount_paid_now') or Decimal('0.00')
        if amount_paid_now < Decimal('0.00'):
            raise ValidationError("Payment amount cannot be negative.")
        return amount_paid_now

    def clean(self):
        cleaned_data = super().clean()
        weight = cleaned_data.get('weight') or Decimal('0.00')
        applied_rate = cleaned_data.get('applied_rate')
        amount_paid_now = cleaned_data.get('amount_paid_now') or Decimal('0.00')
        dry_weight = cleaned_data.get('dry_weight')
        user = cleaned_data.get('user')
        tx_type = cleaned_data.get('transaction_type')
        product = cleaned_data.get('product')

        # ── 1. Dry weight cannot exceed wet weight ──
        if dry_weight is not None and dry_weight > weight:
            self.add_error('dry_weight', "Dry weight cannot exceed received weight.")

        # ── 2. Determine the effective rate for total calculation ──
        # If rate not entered, try to fetch from UserProductRate
        rate_for_calc = applied_rate
        if rate_for_calc is None or rate_for_calc == Decimal('0.00'):
            if user and product:
                rate_obj = UserProductRate.objects.filter(user=user, product=product).first()
                if rate_obj:
                    rate_for_calc = rate_obj.rate
        
        rate_for_calc = rate_for_calc or Decimal('0.00')
        total_amount = weight * rate_for_calc

        # ── 3. Upfront payment cannot exceed batch value ──
        if amount_paid_now > total_amount and total_amount > Decimal('0.00'):
            self.add_error(
                'amount_paid_now',
                f"Initial payment (₦{amount_paid_now:,.2f}) cannot exceed total batch value (₦{total_amount:.2f})."
            )

        # ═══════════════════════════════════════════════════════
        # 4. PRODUCTION-READY CREDIT LIMIT CHECK
        # ═══════════════════════════════════════════════════════
        if (
            tx_type == 'SELL' 
            and user 
            and user.role == User.Roles.CLIENT 
            and total_amount > Decimal('0.00')
        ):
            credit_limit = user.credit_limit or Decimal('0.00')
            
            if credit_limit > Decimal('0.00'):
                # How much does this client currently owe us?
                ledger = getattr(user, 'ledger', None)
                current_balance = ledger.balance if ledger else Decimal('0.00')
                
                # If they overpaid (negative balance), treat as zero owed
                if current_balance < Decimal('0.00'):
                    current_balance = Decimal('0.00')
                
                # What would they owe if we added this batch with NO payment?
                projected_without_payment = current_balance + total_amount
                
                if projected_without_payment > credit_limit:
                    # They need to pay enough to bring it back under the limit
                    minimum_required_upfront = projected_without_payment - credit_limit
                    
                    if amount_paid_now < minimum_required_upfront:
                        shortfall = minimum_required_upfront - amount_paid_now
                        self.add_error(
                            'amount_paid_now',
                            f"Credit limit exceeded. Client currently owes ₦{current_balance:,.2f}. "
                            f"This batch (₦{total_amount:,.2f}) would raise their debt to ₦{projected_without_payment:,.2f}, "
                            f"above their ₦{credit_limit:,.2f} limit. "
                            f"To proceed, the client must pay at least ₦{minimum_required_upfront:,.2f} upfront. "
                            f"You entered ₦{amount_paid_now:,.2f} (still short by ₦{shortfall:,.2f})."
                        )
                    # else: they paid enough — ALLOW the batch

        return cleaned_data

class TransactionForm(BaseStyledForm):
    """Form to log payments and ledger entries."""
    class Meta:
        model = Transaction
        fields = [
            'user', 'batch', 'transaction_type', 'payment_method',
            'amount', 'reference_code', 'transaction_date', 'notes'
        ]
        widgets = {
            'user': forms.Select(),
            'batch': forms.Select(),
            'transaction_type': forms.Select(attrs={'class': 'font-semibold'}),
            'payment_method': forms.Select(attrs={'class': 'font-semibold'}),
            'amount': forms.NumberInput(attrs={
                'placeholder': '0.00', 'step': '0.01', 'min': '0.01'
            }),
            'reference_code': forms.TextInput(attrs={
                'placeholder': 'Bank Ref / Cheque #'
            }),
            'transaction_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={
                'rows': 2, 'placeholder': 'Payment terms or partial payment notes'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['batch'].required = False  # <-- KEY: allow auto-cascade
        self.fields['notes'].required = False
        self.fields['reference_code'].required = False
        
        if not self.instance.pk:
            if not self.initial.get('transaction_type'):
                self.fields['transaction_type'].initial = 'DISBURSEMENT'
            if not self.initial.get('payment_method'):
                self.fields['payment_method'].initial = 'BANK_TRANSFER'
            if 'transaction_date' in self.fields:
                self.fields['transaction_date'].initial = timezone.now().date()

        self.fields['user'].queryset = User.objects.filter(
            is_active=True,
            role__in=[User.Roles.VENDOR, User.Roles.CLIENT]
        )

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is None or amount <= Decimal('0.00'):
            raise ValidationError("Amount must be greater than zero.")
        return amount






class TransctionForm(BaseStyledForm):
    """Form to log payments and ledger entries."""
    class Meta:
        model = Transaction
        fields = ['user', 'batch', 'transaction_type', 'payment_method', 'amount', 'reference_code', 'transaction_date', 'notes']
        widgets = {
            'user': forms.Select(),
            'batch': forms.Select(),
            'transaction_type': forms.Select(),
            'payment_method': forms.Select(),
            'amount': forms.NumberInput(attrs={'placeholder': '0.00', 'step': '0.01'}),
            'reference_code': forms.TextInput(attrs={'placeholder': 'Bank Ref / Cheque # / Receipt'}),
            'transaction_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Payment terms or partial payment notes'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['batch'].required = False
        self.fields['user'].queryset = User.objects.filter(
    is_active=True,
    role__in=[User.Roles.VENDOR, User.Roles.CLIENT]
)
        if not self.instance.pk and 'transaction_date' in self.fields:
            self.fields['transaction_date'].initial = timezone.now().date()


class UserProductRateForm(BaseStyledForm):
    """Form to assign buying/selling rates per product for Vendors and Clients."""
    class Meta:
        model = UserProductRate
        fields = ['user', 'product', 'rate']
        widgets = {
            'user': forms.Select(),
            'product': forms.Select(),
            'rate': forms.NumberInput(attrs={'placeholder': '0.00', 'step': '0.01'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['user'].queryset = User.objects.filter(
    is_active=True,
    role__in=[User.Roles.VENDOR, User.Roles.CLIENT]
)
        self.fields['product'].queryset = Product.objects.filter(is_active=True)



# account/forms.py
class ExpenseForm(BaseStyledForm):
    """Form to log batch expenses."""
    class Meta:
        model = Expense
        fields = ['batch', 'category', 'title', 'amount', 'expense_date', 'receipt_reference']
        widgets = {
            'batch': forms.Select(),
            'category': forms.Select(),
            'title': forms.TextInput(attrs={'placeholder': 'e.g., 50L Diesel for mechanical dryer'}),
            'amount': forms.NumberInput(attrs={'placeholder': '0.00', 'step': '0.01'}),
            'expense_date': forms.DateInput(attrs={'type': 'date'}),
            'receipt_reference': forms.TextInput(attrs={'placeholder': 'Optional Receipt / Voucher #'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['receipt_reference'].required = False
        self.fields['batch'].required = False 
        if not self.instance.pk and 'expense_date' in self.fields:
            self.fields['expense_date'].initial = timezone.now().date()

class TransactionForm(BaseStyledForm):
    """Form to log payments and ledger entries."""
    class Meta:
        model = Transaction
        fields = [
            'user', 'batch', 'transaction_type', 'payment_method',
            'amount', 'reference_code', 'transaction_date', 'notes'
        ]
        widgets = {
            'user': forms.Select(),
            'batch': forms.Select(),
            'transaction_type': forms.Select(attrs={
                'class': 'font-semibold'
            }),
            'payment_method': forms.Select(attrs={
                'class': 'font-semibold'
            }),
            'amount': forms.NumberInput(attrs={
                'placeholder': '0.00', 
                'step': '0.01',
                'min': '0.01'
            }),
            'reference_code': forms.TextInput(attrs={
                'placeholder': 'Bank Ref / Cheque #'
            }),
            'transaction_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={
                'rows': 2, 
                'placeholder': 'Payment terms or partial payment notes'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['batch'].required = False
        self.fields['notes'].required = False
        self.fields['reference_code'].required = False
        
        # Defaults for new records
        if not self.instance.pk:
            if not self.initial.get('transaction_type'):
                self.fields['transaction_type'].initial = 'DISBURSEMENT'
            if not self.initial.get('payment_method'):
                self.fields['payment_method'].initial = 'BANK_TRANSFER'
            if 'transaction_date' in self.fields:
                self.fields['transaction_date'].initial = timezone.now().date()

        self.fields['user'].queryset = User.objects.filter(
    is_active=True,
    role__in=[User.Roles.VENDOR, User.Roles.CLIENT]
)

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is None or amount <= Decimal('0.00'):
            raise ValidationError("Amount must be greater than zero.")
        return amount
class PaymentAllocationForm(BaseStyledForm):
    """Form to allocate an existing unallocated payment to a batch."""
    class Meta:
        model = PaymentAllocation
        fields = ['transaction', 'batch', 'amount']
        widgets = {
            'transaction': forms.Select(),
            'batch': forms.HiddenInput(),
            'amount': forms.NumberInput(attrs={'placeholder': '0.00', 'step': '0.01'}),
        }

    def __init__(self, *args, batch=None, **kwargs):
        super().__init__(*args, **kwargs)
        if batch:
            self.fields['batch'].initial = batch.pk
            # Only show unallocated transactions from THIS user
            self.fields['transaction'].queryset = Transaction.objects.filter(
                user=batch.user,
                batch__isnull=True
            ).annotate(
                allocated=Sum('allocations__amount')
            ).filter(
                Q(allocated__lt=F('amount')) | Q(allocated__isnull=True)
            )

    def clean(self):
        cleaned_data = super().clean()
        transaction = cleaned_data.get('transaction')
        batch = cleaned_data.get('batch')
        amount = cleaned_data.get('amount')

        if transaction and batch and amount:
            if transaction.user != batch.user:
                raise ValidationError("Transaction user must match batch user.")

            allocated = PaymentAllocation.objects.filter(
                transaction=transaction
            ).exclude(pk=self.instance.pk if self.instance.pk else None).aggregate(
                total=Sum('amount')
            )['total'] or Decimal('0.00')

            available = (transaction.amount or Decimal('0.00')) - allocated
            if amount > available:
                raise ValidationError(f"Exceeds unallocated amount (₦{available:,.2f}).")

            if amount > batch.balance_due:
                raise ValidationError(f"Exceeds batch balance due (₦{batch.balance_due:,.2f}).")

        return cleaned_data



# Add this to account/forms.py

class UserProfileForm(BaseStyledForm):
    """Form for editing user profile information."""
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone', 'address', 'credit_limit']
        widgets = {
            'first_name': forms.TextInput(attrs={'placeholder': 'First name'}),
            'last_name': forms.TextInput(attrs={'placeholder': 'Last name'}),
            'email': forms.EmailInput(attrs={'placeholder': 'email@example.com'}),
            'phone': forms.TextInput(attrs={'placeholder': '+234 800 000 0000'}),
            'address': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Full business address'}),
            'credit_limit': forms.NumberInput(attrs={'placeholder': '0.00', 'step': '0.01'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show credit_limit for clients
        if self.instance and self.instance.role != User.Roles.CLIENT:
            self.fields.pop('credit_limit', None)        




            
class ProductForm(BaseStyledForm):
    """Form to create and edit farm products."""
    class Meta:
        model = Product
        fields = ['name', 'unit', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'placeholder': 'e.g. Cashew Seed, Cocoa, Ginger',
                'class': 'w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-slate-800 bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent text-sm transition-all'
            }),
            'unit': forms.TextInput(attrs={
                'placeholder': 'kg, bags, tons, baskets',
                'class': 'w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-slate-800 bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent text-sm transition-all'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 rounded border-slate-300 text-emerald-600 focus:ring-emerald-500'
            }),
        }

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if not name:
            raise ValidationError("Product name cannot be empty.")
        # Check uniqueness (case-insensitive) only for new products or if name changed
        qs = Product.objects.filter(name__iexact=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError(f"A product called '{name}' already exists.")
        return name






class UserCreateForm(BaseStyledForm):
    """Form to create a new user (Vendor, Client, or Admin)."""
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Set a password',
            'class': 'w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-slate-800 bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent text-sm transition-all'
        }),
        help_text="User go use this password to login."
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Type password again',
            'class': 'w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-slate-800 bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent text-sm transition-all'
        }),
        help_text="Type the same password to confirm."
    )

    class Meta:
        model = User
        fields = [
            'username', 'first_name', 'last_name', 'email',
            'role', 'phone', 'address', 'credit_limit'
        ]
        widgets = {
            'username': forms.TextInput(attrs={'placeholder': 'e.g. farmer_john, buyer_mike'}),
            'first_name': forms.TextInput(attrs={'placeholder': 'First name'}),
            'last_name': forms.TextInput(attrs={'placeholder': 'Last name'}),
            'email': forms.EmailInput(attrs={'placeholder': 'email@example.com'}),
            'phone': forms.TextInput(attrs={'placeholder': '+234 800 000 0000'}),
            'address': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Village, Town, or Business address'}),
            'credit_limit': forms.NumberInput(attrs={'placeholder': '0.00', 'step': '0.01'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].required = False
        self.fields['first_name'].required = False
        self.fields['last_name'].required = False
        self.fields['phone'].required = False
        self.fields['address'].required = False
        self.fields['credit_limit'].required = False
        # Hide credit limit by default unless client selected
        self.fields['credit_limit'].widget.attrs['id'] = 'id_credit_limit'

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm = cleaned_data.get('confirm_password')

        if password and confirm and password != confirm:
            self.add_error('confirm_password', "Passwords no match. Type the same thing twice.")

        # Only clients get credit limit
        role = cleaned_data.get('role')
        if role != User.Roles.CLIENT:
            cleaned_data['credit_limit'] = Decimal('0.00')

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user
    


from django.forms import formset_factory, BaseFormSet

# ============================================================
# PRODUCT ASSIGNMENT (for User Create)
# ============================================================

class AssignProductForm(forms.Form):
    """Pick a product and set the price per kg/unit."""
    product = forms.ModelChoiceField(
        queryset=Product.objects.filter(is_active=True),
        required=False,
        empty_label="— Select Product —",
        widget=forms.Select(attrs={'class': TWIND_INPUT})
    )
    rate = forms.DecimalField(
        max_digits=10, decimal_places=2, required=False,
        widget=forms.NumberInput(attrs={
            'placeholder': '0.00', 'step': '0.01', 'class': TWIND_INPUT
        })
    )

    def clean(self):
        cleaned = super().clean()
        product = cleaned.get('product')
        rate = cleaned.get('rate')

        if product and rate is None:
            raise forms.ValidationError("Enter a rate for this product.")
        if rate is not None and not product:
            raise forms.ValidationError("Select a product for this rate.")
        return cleaned


class BaseAssignProductFormSet(BaseFormSet):
    def clean(self):
        super().clean()
        products = []
        for form in self.forms:
            if form.cleaned_data and form.cleaned_data.get('product'):
                prod = form.cleaned_data['product']
                if prod in products:
                    raise forms.ValidationError(
                        "You cannot assign the same product twice. Remove the duplicate row."
                    )
                products.append(prod)


AssignProductFormSet = formset_factory(
    AssignProductForm,
    formset=BaseAssignProductFormSet,
    extra=3,
    max_num=10
)


# ============================================================
# UPDATED USER CREATE FORM
# ============================================================

class UserCreateForm(BaseStyledForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Set a password',
            'class': TWIND_INPUT
        }),
        help_text="User go use this password to login."
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Type password again',
            'class': TWIND_INPUT
        }),
        help_text="Type the same password to confirm."
    )

    class Meta:
        model = User
        fields = [
            'username', 'first_name', 'last_name', 'email',
            'role', 'phone', 'address', 'credit_limit'
        ]
        widgets = {
            'username': forms.TextInput(attrs={'placeholder': 'e.g. farmer_john, buyer_mike'}),
            'first_name': forms.TextInput(attrs={'placeholder': 'First name'}),
            'last_name': forms.TextInput(attrs={'placeholder': 'Last name'}),
            'email': forms.EmailInput(attrs={'placeholder': 'email@example.com'}),
            'phone': forms.TextInput(attrs={'placeholder': '+234 800 000 0000'}),
            'address': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Village, Town, or Business address'}),
            'credit_limit': forms.NumberInput(attrs={'placeholder': '0.00', 'step': '0.01'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].required = False
        self.fields['first_name'].required = False
        self.fields['last_name'].required = False
        self.fields['phone'].required = False
        self.fields['address'].required = False
        self.fields['credit_limit'].required = False
        self.fields['credit_limit'].initial = Decimal('0.00')

    def clean(self):
        cleaned = super().clean()
        password = cleaned.get('password')
        confirm = cleaned.get('confirm_password')

        if password and confirm and password != confirm:
            self.add_error('confirm_password', "Passwords no match. Type the same thing twice.")

        # Only clients get credit limit
        role = cleaned.get('role')
        if role != User.Roles.CLIENT:
            cleaned['credit_limit'] = Decimal('0.00')

        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user    
    



from django.forms import modelformset_factory

class BatchExpenseForm(BaseStyledForm):
    """Expense row for inline batch creation."""
    class Meta:
        model = Expense
        fields = ['category', 'title', 'amount', 'expense_date', 'receipt_reference']
        widgets = {
            'category': forms.Select(attrs={'class': TWIND_INPUT}),
            'title': forms.TextInput(attrs={
                'placeholder': 'e.g. 50L Diesel for lorry',
                'class': TWIND_INPUT
            }),
            'amount': forms.NumberInput(attrs={
                'placeholder': '0.00', 'step': '0.01', 'class': TWIND_INPUT
            }),
            'expense_date': forms.DateInput(attrs={'type': 'date', 'class': TWIND_INPUT}),
            'receipt_reference': forms.TextInput(attrs={
                'placeholder': 'Receipt or Voucher #',
                'class': TWIND_INPUT
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['receipt_reference'].required = False
        if not self.instance.pk and 'expense_date' in self.fields:
            self.fields['expense_date'].initial = timezone.now().date()


# Formset: 2 empty rows by default, can add more with JS
BatchExpenseFormSet = modelformset_factory(
    Expense,
    form=BatchExpenseForm,
    extra=2,
    can_delete=True,
    fields=['category', 'title', 'amount', 'expense_date', 'receipt_reference']
)    