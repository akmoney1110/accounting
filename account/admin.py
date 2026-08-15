from decimal import Decimal
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.db.models import F, Sum
from django.utils.html import format_html

from .models import (
    User, 
    Product, 
    UserProductRate, 
    Batch, 
    Expense, 
    Transaction, 
    Ledger,
    PaymentAllocation,
)


# ==========================================
# INLINES
# ==========================================

class UserProductRateInline(admin.TabularInline):
    model = UserProductRate
    extra = 1
    autocomplete_fields = ['product']
    verbose_name = "Assigned Product & Rate"
    verbose_name_plural = "Assigned Products & Buying/Selling Rates"


class LedgerInline(admin.StackedInline):
    model = Ledger
    can_delete = False
    extra = 0
    readonly_fields = ('total_due_or_billed', 'total_paid_or_received', 'balance', 'last_synced_at')


class ExpenseInline(admin.TabularInline):
    model = Expense
    extra = 1
    fields = ('category', 'title', 'amount', 'expense_date')


class PaymentAllocationInline(admin.TabularInline):
    model = PaymentAllocation
    extra = 0
    autocomplete_fields = ['transaction']
    readonly_fields = ('allocated_at', 'allocated_by')
    fields = ('transaction', 'amount', 'allocated_at', 'allocated_by')


class TransactionInline(admin.TabularInline):
    model = Transaction
    extra = 0
    fields = ('transaction_type', 'payment_method', 'amount', 'transaction_date', 'reference_code')
    readonly_fields = ('transaction_date',)


# ==========================================
# CUSTOM FILTERS
# ==========================================

class PaymentStatusListFilter(admin.SimpleListFilter):
    title = 'Payment Status'
    parameter_name = 'payment_status'

    def lookups(self, request, model_admin):
        return (
            ('FULL_PAYMENT', 'Full Payment'),
            ('PARTIAL_PAYMENT', 'Partial Payment'),
            ('NO_PAYMENT', 'No Payment'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'FULL_PAYMENT':
            return queryset.filter(amount_paid__gte=F('total_amount'), total_amount__gt=0)
        if self.value() == 'PARTIAL_PAYMENT':
            return queryset.filter(amount_paid__gt=0, amount_paid__lt=F('total_amount'))
        if self.value() == 'NO_PAYMENT':
            return queryset.filter(amount_paid=0)
        return queryset


# ==========================================
# MODEL ADMINS
# ==========================================

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        'username', 
        'email', 
        'role_badge', 
        'phone', 
        'credit_limit_formatted', 
        'is_active'
    )
    list_filter = ('role', 'is_active', 'is_staff')
    search_fields = ('username', 'email', 'phone', 'first_name', 'last_name')
    ordering = ('username',)
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Role & Business Info', {
            'fields': ('role', 'phone', 'address', 'credit_limit')
        }),
    )
    
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Role & Business Info', {
            'fields': ('role', 'email', 'phone', 'address', 'credit_limit'),
        }),
    )
    
    inlines = [UserProductRateInline, LedgerInline]

    @admin.display(description='Role', ordering='role')
    def role_badge(self, obj):
        role_map = {
            'ADMIN': ('#f3e8ff', '#6b21a8'),
            'VENDOR': ('#dbeafe', '#1e40af'),
            'CLIENT': ('#d1fae5', '#065f46'),
        }
        bg, color = role_map.get(obj.role, ('#f3f4f6', '#1f2937'))
        return format_html(
            '<span style="background-color: {}; color: {}; padding: 3px 8px; border-radius: 6px; font-weight: 600; font-size: 11px;">{}</span>',
            bg, color, obj.get_role_display()
        )

    @admin.display(description='Credit Limit', ordering='credit_limit')
    def credit_limit_formatted(self, obj):
        val = obj.credit_limit or Decimal('0.00')
        return f"₦{val:,.2f}"


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'unit', 'is_active_badge', 'assigned_users_count')
    list_filter = ('is_active',)
    search_fields = ('name',)

    @admin.display(description='Status', ordering='is_active')
    def is_active_badge(self, obj):
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            'green' if obj.is_active else 'red',
            'Active' if obj.is_active else 'Inactive'
        )

    @admin.display(description='Assigned Users')
    def assigned_users_count(self, obj):
        return obj.user_rates.count()


@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    list_select_related = ('user', 'product')

    list_display = (
        'batch_code', 
        'transaction_type_badge', 
        'user', 
        'product', 
        'dry_weight_formatted',
        'moisture_loss_formatted',
        'weight_formatted', 
        'applied_rate_formatted', 
        'total_amount_formatted',
        'amount_paid_formatted',
        'total_expenses_formatted',
        'effective_rate_formatted',
        'balance_due_formatted',
        'payment_status_badge',
        'transaction_date',
    )
    
    list_filter = (
        'transaction_type', 
        'payment_status', 
        'product', 
        'transaction_date',
        PaymentStatusListFilter,
    )
    
    search_fields = (
        'batch_code', 
        'user__username', 
        'user__first_name', 
        'user__last_name', 
        'product__name',
    )
    
    autocomplete_fields = ['user', 'product']
    date_hierarchy = 'transaction_date'
    ordering = ('-transaction_date', '-created_at')
    
    readonly_fields = (
        'batch_code', 
        'total_amount', 
        'amount_paid',
        'payment_status',
        'balance_due_formatted', 
        'payment_status_badge',
        'created_at',
    )
    
    fieldsets = (
        ('Batch Identification', {
            'fields': (
                ('batch_code', 'transaction_type'),
                'transaction_date',
            )
        }),
        ('Party & Commodity', {
            'fields': (
                'user',
                'product',
                ('weight', 'dry_weight', 'applied_rate'),
                'total_amount',
            )
        }),
        ('Payment Settlement & Balance Tracking', {
            'fields': (
                'amount_paid',
                'payment_status',
                'balance_due_formatted',
            )
        }),
        ('System Information', {
            'classes': ('collapse',),
            'fields': ('created_at',),
        }),
    )
    
    inlines = [ExpenseInline, PaymentAllocationInline]

    # --- FORMATTERS & BADGES ---

    @admin.display(description='Type', ordering='transaction_type')
    def transaction_type_badge(self, obj):
        is_buy = obj.transaction_type == 'BUY'
        bg = "#dbeafe" if is_buy else "#d1fae5"
        color = "#1e40af" if is_buy else "#065f46"
        display_text = obj.get_transaction_type_display()
        return format_html(
            '<span style="background-color: {}; color: {}; padding: 3px 8px; border-radius: 6px; font-weight: bold; font-size: 11px;">{}</span>',
            bg, color, display_text
        )

    @admin.display(description='Payment Status', ordering='payment_status')
    def payment_status_badge(self, obj):
        status_config = {
            'NO_PAYMENT': ('No Payment', '#fee2e2', '#991b1b'),
            'PARTIAL_PAYMENT': ('Partial Payment', '#fef3c7', '#92400e'),
            'FULL_PAYMENT': ('Full Payment', '#d1fae5', '#065f46'),
        }
        label, bg, color = status_config.get(obj.payment_status, ('No Payment', '#fee2e2', '#991b1b'))
        return format_html(
            '<span style="background-color: {}; color: {}; padding: 4px 10px; border-radius: 6px; font-weight: bold; font-size: 11px;">{}</span>',
            bg, color, label
        )

    @admin.display(description='Dry Wt', ordering='dry_weight')
    def dry_weight_formatted(self, obj):
        if obj.dry_weight is None:
            return format_html('<span style="color:#9ca3af;">{}</span>', '—')
        unit = obj.product.unit if obj.product else 'kg'
        return f"{obj.dry_weight:,.2f} {unit}"

    @admin.display(description='Moisture Loss')
    def moisture_loss_formatted(self, obj):
        loss = obj.moisture_loss
        if loss <= Decimal('0.00') and obj.dry_weight is None:
            return format_html('<span style="color:#9ca3af;">{}</span>', '—')
        unit = obj.product.unit if obj.product else 'kg'
        return format_html(
            '<span style="color:#dc2626; font-weight:600;">-{} {}</span>',
            f"{loss:,.2f}", unit
        )

    @admin.display(description='Weight', ordering='weight')
    def weight_formatted(self, obj):
        unit = obj.product.unit if obj.product else 'kg'
        weight_val = obj.weight or Decimal('0.00')
        return f"{weight_val:,.2f} {unit}"

    @admin.display(description='Rate', ordering='applied_rate')
    def applied_rate_formatted(self, obj):
        rate_val = obj.applied_rate or Decimal('0.00')
        return f"₦{rate_val:,.2f}"

    @admin.display(description='Total', ordering='total_amount')
    def total_amount_formatted(self, obj):
        total_val = obj.total_amount or Decimal('0.00')
        return f"₦{total_val:,.2f}"

    @admin.display(description='Paid', ordering='amount_paid')
    def amount_paid_formatted(self, obj):
        paid_val = obj.amount_paid or Decimal('0.00')
        return f"₦{paid_val:,.2f}"

    @admin.display(description='Balance Due')
    def balance_due_formatted(self, obj):
        due = obj.balance_due or Decimal('0.00')
        color = "#991b1b" if due > Decimal('0.00') else "#065f46"
        formatted_due = f"₦{due:,.2f}"
        return format_html(
            '<strong style="color: {}; font-size: 13px;">{}</strong>',
            color, formatted_due
        )

    @admin.display(description='Expenses', ordering='total_batch_expenses')
    def total_expenses_formatted(self, obj):
        val = obj.total_batch_expenses or Decimal('0.00')
        return f"₦{val:,.2f}"

    @admin.display(description='Effective Rate (Dry)')
    def effective_rate_formatted(self, obj):
        rate = obj.effective_rate
        if rate <= Decimal('0.00') and obj.dry_weight is None:
            return format_html('<span style="color:#9ca3af;">{}</span>', 'Awaiting dry weight')
        unit = obj.product.unit if obj.product else 'kg'
        return format_html(
            '<strong style="color:#065f46;">₦{} /{}</strong>',
            f"{rate:,.2f}", unit
        )


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        'reference_code', 
        'user', 
        'batch', 
        'transaction_type', 
        'payment_method', 
        'amount_formatted', 
        'unallocated_amount',
        'is_fully_allocated_badge',
        'transaction_date'
    )
    list_filter = ('transaction_type', 'payment_method', 'transaction_date')
    search_fields = ('user__username', 'reference_code', 'batch__batch_code')
    autocomplete_fields = ['user', 'batch']
    date_hierarchy = 'transaction_date'
    inlines = [PaymentAllocationInline]

    @admin.display(description='Amount', ordering='amount')
    def amount_formatted(self, obj):
        val = obj.amount or Decimal('0.00')
        return f"₦{val:,.2f}"

    @admin.display(description='Unallocated')
    def unallocated_amount(self, obj):
        val = obj.unallocated_amount
        color = '#065f46' if val > 0 else '#9ca3af'
        formatted = f"₦{val:,.2f}"
        return format_html('<span style="color: {};">{}</span>', color, formatted)

    @admin.display(description='Status')
    def is_fully_allocated_badge(self, obj):
        if obj.is_fully_allocated:
            return format_html(
            '<span style="background:#d1fae5; color:#065f46; padding:2px 8px; border-radius:4px; font-size:11px;">{}</span>',
            'Fully Allocated'
        )
        return format_html(
        '<span style="background:#dbeafe; color:#1e40af; padding:2px 8px; border-radius:4px; font-size:11px;">{}</span>',
        'Has Credit'
    )


@admin.register(PaymentAllocation)
class PaymentAllocationAdmin(admin.ModelAdmin):
    list_display = ('transaction', 'batch', 'amount_formatted', 'allocated_by', 'allocated_at')
    list_filter = ('allocated_at',)
    search_fields = ('transaction__reference_code', 'batch__batch_code', 'transaction__user__username')
    autocomplete_fields = ['transaction', 'batch']
    readonly_fields = ('allocated_at',)

    @admin.display(description='Amount', ordering='amount')
    def amount_formatted(self, obj):
        return f"₦{obj.amount:,.2f}"


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('batch', 'category', 'title', 'amount_formatted', 'expense_date')
    list_filter = ('category', 'expense_date')
    search_fields = ('batch__batch_code', 'notes', 'title')
    autocomplete_fields = ['batch']
    date_hierarchy = 'expense_date'

    @admin.display(description='Amount', ordering='amount')
    def amount_formatted(self, obj):
        val = obj.amount or Decimal('0.00')
        return f"₦{val:,.2f}"


@admin.register(Ledger)
class LedgerAdmin(admin.ModelAdmin):
    list_display = (
        'user', 
        'total_due_or_billed_formatted', 
        'total_paid_or_received_formatted', 
        'balance_formatted', 
        'last_synced_at'
    )
    search_fields = ('user__username', 'user__first_name', 'user__last_name')
    readonly_fields = ('user', 'total_due_or_billed', 'total_paid_or_received', 'balance', 'last_synced_at')

    @admin.display(description='Billed / Due', ordering='total_due_or_billed')
    def total_due_or_billed_formatted(self, obj):
        val = obj.total_due_or_billed or Decimal('0.00')
        return f"₦{val:,.2f}"

    @admin.display(description='Paid / Received', ordering='total_paid_or_received')
    def total_paid_or_received_formatted(self, obj):
        val = obj.total_paid_or_received or Decimal('0.00')
        return f"₦{val:,.2f}"

    @admin.display(description='Current Balance', ordering='balance')
    def balance_formatted(self, obj):
        bal = obj.balance or Decimal('0.00')
        color = "red" if bal > Decimal('0.00') else "green"
        formatted_bal = f"₦{bal:,.2f}"
        return format_html(
            '<strong style="color: {};">{}</strong>',
            color, formatted_bal
        )