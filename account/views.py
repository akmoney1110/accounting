# account/views.py
from decimal import Decimal, ROUND_HALF_UP
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.db import transaction as db_transaction
from django.db.models import Count, F, Q, Sum, DecimalField, Avg
from django.db.models.functions import Coalesce, TruncMonth
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import ListView, CreateView, UpdateView

from .forms import (
    BatchForm,
    BatchExpenseFormSet,
    CustomLoginForm,
    ExpenseForm,
    TransactionForm,
    ProductForm,
    UserCreateForm,
    AssignProductFormSet,
    UserProfileForm,
)
from .models import (
    Batch,
    Expense,
    Ledger,
    PaymentAllocation,
    Product,
    Transaction,
    User,
    UserProductRate,
)


# ============================================================
# ACCESS CONTROL DECORATORS
# ============================================================
def manager_required(view_func):
    def check(user):
        if not user.is_authenticated:
            return False
        if user.role not in (User.Roles.ADMIN, User.Roles.MANAGER):
            raise PermissionDenied
        return True
    return user_passes_test(check)(view_func)


def staff_required(view_func):
    def check(user):
        if not user.is_authenticated:
            return False
        if user.role not in (User.Roles.ADMIN, User.Roles.MANAGER, User.Roles.STAFF):
            raise PermissionDenied
        return True
    return user_passes_test(check)(view_func)


# ============================================================
# ACCESS CONTROL MIXINS
# ============================================================
class AdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        user = self.request.user
        return user.is_authenticated and user.role == User.Roles.ADMIN


class ManagerRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        user = self.request.user
        return user.is_authenticated and user.role in (
            User.Roles.ADMIN, User.Roles.MANAGER
        )


class StaffRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        user = self.request.user
        return user.is_authenticated and user.role in (
            User.Roles.ADMIN, User.Roles.MANAGER, User.Roles.STAFF
        )


class VendorRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        user = self.request.user
        return user.is_authenticated and user.role == User.Roles.VENDOR


class ClientRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        user = self.request.user
        return user.is_authenticated and user.role == User.Roles.CLIENT


# ============================================================
# 1. AUTHENTICATION
# ============================================================
class LoginView(View):
    template_name = "account/login.html"

    def get(self, request):
        if request.user.is_authenticated:
            return self.redirect_by_role(request.user)
        form = CustomLoginForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = CustomLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")
            return self.redirect_by_role(user)
        messages.error(request, "Invalid username or password.")
        return render(request, self.template_name, {"form": form})

    @staticmethod
    def redirect_by_role(user):
        if user.role == User.Roles.ADMIN:
            return redirect("admin_dashboard")
        if user.role == User.Roles.MANAGER:
            return redirect("manager_dashboard")
        if user.role == User.Roles.STAFF:
            return redirect("staff_dashboard")
        if user.role == User.Roles.VENDOR:
            return redirect("vendor_portal")
        if user.role == User.Roles.CLIENT:
            return redirect("client_portal")
        messages.error(None, "Your account does not have a valid business role.")
        return redirect("login")


class LogoutView(View):
    def get(self, request):
        logout(request)
        messages.info(request, "Logged out successfully.")
        return redirect("login")


# ============================================================
# 2. ADMIN DASHBOARD
# ============================================================
class AdminDashboardView(LoginRequiredMixin, AdminRequiredMixin, View):
    def get(self, request):
        today = timezone.now().date()
        thirty_days_ago = today - timedelta(days=30)

        total_sales = (
            Batch.objects.filter(transaction_type=Batch.TransactionType.SELL)
            .aggregate(total=Sum("total_amount"))["total"] or Decimal("0.00")
        )
        total_purchases = (
            Batch.objects.filter(transaction_type=Batch.TransactionType.BUY)
            .aggregate(total=Sum("total_amount"))["total"] or Decimal("0.00")
        )
        total_expenses = (
            Expense.objects.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        )
        net_profit = total_sales - total_purchases - total_expenses

        total_batches = Batch.objects.count()
        total_partners = User.objects.exclude(role=User.Roles.ADMIN).count()
        pending_payments = Batch.objects.filter(
            payment_status__in=[
                Batch.PaymentStatus.NO_PAYMENT,
                Batch.PaymentStatus.PARTIAL_PAYMENT,
            ]
        ).count()
        total_weight = (
            Batch.objects.aggregate(total=Sum("weight"))["total"] or Decimal("0.00")
        )
        total_dry_weight = (
            Batch.objects.aggregate(total=Sum("dry_weight"))["total"] or Decimal("0.00")
        )
        total_moisture_loss = (
            Batch.objects.filter(dry_weight__isnull=False)
            .annotate(loss=F("weight") - F("dry_weight"))
            .aggregate(total=Sum("loss"))["total"] or Decimal("0.00")
        )

        def _latest_rate(user, tx_type):
            latest_batch = (
                Batch.objects.filter(user=user, transaction_type=tx_type)
                .order_by("-transaction_date", "-created_at")
                .first()
            )
            if latest_batch and latest_batch.applied_rate and latest_batch.applied_rate > 0:
                return latest_batch.applied_rate
            rate_obj = UserProductRate.objects.filter(user=user).order_by("-id").first()
            if rate_obj and rate_obj.rate and rate_obj.rate > 0:
                return rate_obj.rate
            return Decimal("0.00")

        def _kg_and_rate(ledgers, tx_type):
            total_amt = Decimal("0.00")
            total_kg = Decimal("0.00")
            for ledger in ledgers:
                bal = abs(ledger.balance)
                if bal <= 0:
                    continue
                rate = _latest_rate(ledger.user, tx_type)
                if rate > 0:
                    total_kg += bal / rate
                    total_amt += bal
            avg_rate = Decimal("0.00")
            if total_kg > 0:
                avg_rate = (total_amt / total_kg).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                total_kg = total_kg.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            return total_kg, avg_rate

        vendor_ledgers = Ledger.objects.filter(user__role=User.Roles.VENDOR)
        client_ledgers = Ledger.objects.filter(user__role=User.Roles.CLIENT)

        amount_owe_vendors = (
            vendor_ledgers.filter(balance__gt=0).aggregate(total=Sum("balance"))["total"]
            or Decimal("0.00")
        )
        vendors_owe_me = abs(
            vendor_ledgers.filter(balance__lt=0).aggregate(total=Sum("balance"))["total"]
            or Decimal("0.00")
        )
        clients_owe_me = (
            client_ledgers.filter(balance__gt=0).aggregate(total=Sum("balance"))["total"]
            or Decimal("0.00")
        )
        owe_clients = abs(
            client_ledgers.filter(balance__lt=0).aggregate(total=Sum("balance"))["total"]
            or Decimal("0.00")
        )

        amount_owe_vendors_kg, amount_owe_vendors_rate = _kg_and_rate(
            vendor_ledgers.filter(balance__gt=0), "BUY"
        )
        vendors_owe_me_kg, vendors_owe_me_rate = _kg_and_rate(
            vendor_ledgers.filter(balance__lt=0), "BUY"
        )
        clients_owe_me_kg, clients_owe_me_rate = _kg_and_rate(
            client_ledgers.filter(balance__gt=0), "SELL"
        )
        owe_clients_kg, owe_clients_rate = _kg_and_rate(
            client_ledgers.filter(balance__lt=0), "SELL"
        )

        CASHEW_PRODUCT_NAME = "RAW CASHEW NUT (RCN) WET"
        vendor_wet_weight = (
            Batch.objects.filter(
                transaction_type=Batch.TransactionType.BUY,
                product__name=CASHEW_PRODUCT_NAME
            )
            .aggregate(total=Sum("weight"))["total"] or Decimal("0.00")
        )
        vendor_dry_weight = (
            Batch.objects.filter(
                transaction_type=Batch.TransactionType.BUY,
                product__name=CASHEW_PRODUCT_NAME,
                dry_weight__isnull=False
            )
            .aggregate(total=Sum("dry_weight"))["total"] or Decimal("0.00")
        )
        vendor_moisture_loss = (
            Batch.objects.filter(
                transaction_type=Batch.TransactionType.BUY,
                product__name=CASHEW_PRODUCT_NAME,
                dry_weight__isnull=False
            )
            .annotate(loss=F("weight") - F("dry_weight"))
            .aggregate(total=Sum("loss"))["total"] or Decimal("0.00")
        )

        payment_status_counts = {
            "full": Batch.objects.filter(payment_status=Batch.PaymentStatus.FULL_PAYMENT).count(),
            "partial": Batch.objects.filter(payment_status=Batch.PaymentStatus.PARTIAL_PAYMENT).count(),
            "none": Batch.objects.filter(payment_status=Batch.PaymentStatus.NO_PAYMENT).count(),
        }

        top_vendors = (
            User.objects.filter(role=User.Roles.VENDOR)
            .annotate(
                total_supplied=Sum("batches__weight", filter=Q(batches__transaction_type="BUY")),
                total_value=Sum("batches__total_amount", filter=Q(batches__transaction_type="BUY")),
                batch_count=Count("batches", filter=Q(batches__transaction_type="BUY")),
            )
            .filter(total_supplied__gt=0)
            .order_by("-total_value")[:5]
        )

        top_clients = (
            User.objects.filter(role=User.Roles.CLIENT)
            .annotate(
                total_bought=Sum("batches__weight", filter=Q(batches__transaction_type="SELL")),
                total_value=Sum("batches__total_amount", filter=Q(batches__transaction_type="SELL")),
                batch_count=Count("batches", filter=Q(batches__transaction_type="SELL")),
            )
            .filter(total_bought__gt=0)
            .order_by("-total_value")[:5]
        )

        expense_breakdown = list(
            Expense.objects.values("category")
            .annotate(total=Sum("amount"), count=Count("id"))
            .order_by("-total")
        )

        six_months_ago = today - timedelta(days=180)
        monthly_trends = (
            Batch.objects.filter(transaction_date__gte=six_months_ago)
            .annotate(month=TruncMonth("transaction_date"))
            .values("month", "transaction_type")
            .annotate(
                total_amount=Sum("total_amount"),
                total_weight=Sum("weight"),
                count=Count("id"),
            )
            .order_by("month")
        )

        monthly_chart_data = {}
        for row in monthly_trends:
            month_key = row["month"].strftime("%Y-%m") if row["month"] else "Unknown"
            if month_key not in monthly_chart_data:
                monthly_chart_data[month_key] = {}
            monthly_chart_data[month_key][row["transaction_type"]] = {
                "amount": row["total_amount"] or Decimal("0.00"),
                "weight": row["total_weight"] or Decimal("0.00"),
                "count": row["count"],
            }

        recent_batches = (
            Batch.objects.select_related("product", "user")
            .order_by("-transaction_date", "-created_at")[:10]
        )
        recent_transactions = (
            Transaction.objects.select_related("user", "batch")
            .order_by("-created_at")[:10]
        )

        this_month_sales = (
            Batch.objects.filter(
                transaction_type="SELL",
                transaction_date__year=today.year,
                transaction_date__month=today.month,
            ).aggregate(total=Sum("total_amount"))["total"] or Decimal("0.00")
        )
        last_month = today.replace(day=1) - timedelta(days=1)
        last_month_sales = (
            Batch.objects.filter(
                transaction_type="SELL",
                transaction_date__year=last_month.year,
                transaction_date__month=last_month.month,
            ).aggregate(total=Sum("total_amount"))["total"] or Decimal("0.00")
        )

        sales_growth = Decimal("0.00")
        if last_month_sales > 0:
            sales_growth = ((this_month_sales - last_month_sales) / last_month_sales * 100).quantize(
                Decimal("0.1"), rounding=ROUND_HALF_UP
            )

        unallocated_payments = Decimal("0.00")
        for txn in Transaction.objects.filter(batch__isnull=True):
            unallocated_payments += txn.unallocated_amount

        context = {
            "total_sales": total_sales,
            "total_purchases": total_purchases,
            "total_expenses": total_expenses,
            "net_profit": net_profit,
            "total_batches": total_batches,
            "total_partners": total_partners,
            "pending_payments": pending_payments,
            "total_weight": total_weight,
            "total_dry_weight": total_dry_weight,
            "total_moisture_loss": total_moisture_loss,
            "amount_owe_vendors": amount_owe_vendors,
            "vendors_owe_me": vendors_owe_me,
            "clients_owe_me": clients_owe_me,
            "owe_clients": owe_clients,
            "amount_owe_vendors_kg": amount_owe_vendors_kg,
            "amount_owe_vendors_rate": amount_owe_vendors_rate,
            "vendors_owe_me_kg": vendors_owe_me_kg,
            "vendors_owe_me_rate": vendors_owe_me_rate,
            "clients_owe_me_kg": clients_owe_me_kg,
            "clients_owe_me_rate": clients_owe_me_rate,
            "owe_clients_kg": owe_clients_kg,
            "owe_clients_rate": owe_clients_rate,
            "payment_status_counts": payment_status_counts,
            "expense_breakdown": expense_breakdown,
            "top_vendors": top_vendors,
            "vendor_wet_weight": vendor_wet_weight,
            "vendor_dry_weight": vendor_dry_weight,
            "vendor_moisture_loss": vendor_moisture_loss,
            "top_clients": top_clients,
            "monthly_chart_data": monthly_chart_data,
            "this_month_sales": this_month_sales,
            "last_month_sales": last_month_sales,
            "sales_growth": sales_growth,
            "unallocated_payments": unallocated_payments,
            "recent_batches": recent_batches,
            "recent_transactions": recent_transactions,
            "today": today,
            "thirty_days_ago": thirty_days_ago,
        }
        return render(request, "account/admin_dashboard.html", context)


# ============================================================
# 3. MANAGER DASHBOARD
# ============================================================
class ManagerDashboardView(LoginRequiredMixin, ManagerRequiredMixin, View):
    template_name = "account/manager_dashboard.html"

    def get(self, request):
        today = timezone.now().date()
        thirty_days_ago = today - timedelta(days=30)

        total_sales = (
            Batch.objects.filter(transaction_type=Batch.TransactionType.SELL)
            .aggregate(total=Sum("total_amount"))["total"] or Decimal("0.00")
        )
        total_purchases = (
            Batch.objects.filter(transaction_type=Batch.TransactionType.BUY)
            .aggregate(total=Sum("total_amount"))["total"] or Decimal("0.00")
        )
        total_expenses = (
            Expense.objects.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        )
        net_profit = total_sales - total_purchases - total_expenses

        total_batches = Batch.objects.count()
        pending_payments = Batch.objects.filter(
            payment_status__in=[
                Batch.PaymentStatus.NO_PAYMENT,
                Batch.PaymentStatus.PARTIAL_PAYMENT,
            ]
        ).count()

        vendor_ledgers = Ledger.objects.filter(user__role=User.Roles.VENDOR)
        client_ledgers = Ledger.objects.filter(user__role=User.Roles.CLIENT)

        amount_owe_vendors = (
            vendor_ledgers.filter(balance__gt=0).aggregate(total=Sum("balance"))["total"]
            or Decimal("0.00")
        )
        clients_owe_me = (
            client_ledgers.filter(balance__gt=0).aggregate(total=Sum("balance"))["total"]
            or Decimal("0.00")
        )

        recent_batches = (
            Batch.objects.select_related("product", "user")
            .order_by("-transaction_date", "-created_at")[:10]
        )
        recent_transactions = (
            Transaction.objects.select_related("user", "batch")
            .order_by("-created_at")[:10]
        )

        top_vendors = (
            User.objects.filter(role=User.Roles.VENDOR)
            .annotate(
                total_value=Sum("batches__total_amount", filter=Q(batches__transaction_type="BUY")),
            )
            .filter(total_value__gt=0)
            .order_by("-total_value")[:5]
        )

        top_clients = (
            User.objects.filter(role=User.Roles.CLIENT)
            .annotate(
                total_value=Sum("batches__total_amount", filter=Q(batches__transaction_type="SELL")),
            )
            .filter(total_value__gt=0)
            .order_by("-total_value")[:5]
        )

        context = {
            "total_sales": total_sales,
            "total_purchases": total_purchases,
            "total_expenses": total_expenses,
            "net_profit": net_profit,
            "total_batches": total_batches,
            "pending_payments": pending_payments,
            "amount_owe_vendors": amount_owe_vendors,
            "clients_owe_me": clients_owe_me,
            "recent_batches": recent_batches,
            "settled_batches": total_batches - pending_payments,
            "recent_transactions": recent_transactions,
            "top_vendors": top_vendors,
            "top_clients": top_clients,
            "today": today,
            "thirty_days_ago": thirty_days_ago,
        }
        return render(request, self.template_name, context)


# ============================================================
# 4. STAFF DASHBOARD
# ============================================================
class StaffDashboardView(LoginRequiredMixin, StaffRequiredMixin, View):
    template_name = "account/staff_dashboard.html"

    def get(self, request):
        today = timezone.now().date()
        seven_days_ago = today - timedelta(days=7)
        thirty_days_ago = today - timedelta(days=30)

        recent_batches = (
            Batch.objects.select_related("product", "user")
            .order_by("-transaction_date", "-created_at")[:15]
        )

        pending_dry_weight = (
            Batch.objects.filter(
                transaction_type=Batch.TransactionType.BUY,
                dry_weight__isnull=True
            )
            .select_related("product", "user")
            .order_by("-transaction_date")[:10]
        )

        total_batches = Batch.objects.count()
        batches_this_week = Batch.objects.filter(transaction_date__gte=seven_days_ago).count()

        total_weight = (
            Batch.objects.aggregate(total=Sum("weight"))["total"] or Decimal("0.00")
        )
        total_dry_weight = (
            Batch.objects.aggregate(total=Sum("dry_weight"))["total"] or Decimal("0.00")
        )

        recent_expenses_total = (
            Expense.objects.filter(expense_date__gte=thirty_days_ago)
            .aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        )

        payment_status_counts = {
            "full": Batch.objects.filter(payment_status=Batch.PaymentStatus.FULL_PAYMENT).count(),
            "partial": Batch.objects.filter(payment_status=Batch.PaymentStatus.PARTIAL_PAYMENT).count(),
            "none": Batch.objects.filter(payment_status=Batch.PaymentStatus.NO_PAYMENT).count(),
        }

        recent_expenses = (
            Expense.objects.select_related("batch")
            .order_by("-expense_date", "-created_at")[:10]
        )

        context = {
            "recent_batches": recent_batches,
            "pending_dry_weight": pending_dry_weight,
            "total_batches": total_batches,
            "batches_this_week": batches_this_week,
            "total_weight": total_weight,
            "total_dry_weight": total_dry_weight,
            "recent_expenses_total": recent_expenses_total,
            "payment_status_counts": payment_status_counts,
            "recent_expenses": recent_expenses,
            "today": today,
        }
        return render(request, self.template_name, context)


# ============================================================
# 5. USER PROFILE
# ============================================================
class UserProfileView(LoginRequiredMixin, View):
    template_name = "account/profile.html"

    def get(self, request, pk=None):
        if pk and request.user.role == User.Roles.ADMIN:
            profile_user = get_object_or_404(User, pk=pk)
        else:
            profile_user = request.user

        if request.user.role != User.Roles.ADMIN and request.user != profile_user:
            messages.error(request, "You can only view your own profile.")
            return redirect("login")

        ledger, _ = Ledger.objects.get_or_create(user=profile_user)
        batches = profile_user.batches.select_related("product").order_by("-transaction_date")

        batch_stats = {
            'total': batches.count(),
            'paid': batches.filter(payment_status=Batch.PaymentStatus.FULL_PAYMENT).count(),
            'partial': batches.filter(payment_status=Batch.PaymentStatus.PARTIAL_PAYMENT).count(),
            'unpaid': batches.filter(payment_status=Batch.PaymentStatus.NO_PAYMENT).count(),
            'buy': batches.filter(transaction_type=Batch.TransactionType.BUY).count(),
            'sell': batches.filter(transaction_type=Batch.TransactionType.SELL).count(),
        }

        transactions = profile_user.transactions.select_related('batch').order_by("-transaction_date")
        txn_stats = {
            'total': transactions.count(),
            'disbursements': transactions.filter(transaction_type=Transaction.TransactionType.DISBURSEMENT).count(),
            'receipts': transactions.filter(transaction_type=Transaction.TransactionType.RECEIPT).count(),
        }

        unallocated_total = Decimal('0.00')
        unallocated_transactions = []
        for txn in transactions:
            ua = txn.unallocated_amount
            if ua > 0:
                unallocated_total += ua
                unallocated_transactions.append({'txn': txn, 'unallocated': ua})

        product_rates = profile_user.product_rates.select_related('product').order_by('product__name')

        recent_allocations = PaymentAllocation.objects.filter(
            Q(transaction__user=profile_user) | Q(batch__user=profile_user)
        ).select_related('transaction', 'batch', 'allocated_by').order_by('-allocated_at')[:20]

        total_weight = batches.aggregate(total=Sum('weight'))['total'] or Decimal('0.00')
        total_dry_weight = batches.aggregate(total=Sum('dry_weight'))['total'] or Decimal('0.00')

        context = {
            "profile_user": profile_user,
            "ledger": ledger,
            "batches": batches,
            "transactions": transactions,
            "unallocated_total": unallocated_total,
            "unallocated_transactions": unallocated_transactions,
            "batch_stats": batch_stats,
            "txn_stats": txn_stats,
            "product_rates": product_rates,
            "recent_allocations": recent_allocations,
            "total_weight": total_weight,
            "total_dry_weight": total_dry_weight,
            "can_edit": request.user.role == User.Roles.ADMIN or request.user == profile_user,
        }
        return render(request, self.template_name, context)


class UserProfileEditView(LoginRequiredMixin, View):
    template_name = "account/profile_edit.html"

    def get(self, request, pk=None):
        if pk and request.user.role == User.Roles.ADMIN:
            profile_user = get_object_or_404(User, pk=pk)
        else:
            profile_user = request.user

        if request.user.role != User.Roles.ADMIN and request.user != profile_user:
            messages.error(request, "You can only edit your own profile.")
            return redirect("login")

        form = UserProfileForm(instance=profile_user)
        return render(request, self.template_name, {"form": form, "profile_user": profile_user})

    def post(self, request, pk=None):
        if pk and request.user.role == User.Roles.ADMIN:
            profile_user = get_object_or_404(User, pk=pk)
        else:
            profile_user = request.user

        if request.user.role != User.Roles.ADMIN and request.user != profile_user:
            messages.error(request, "You can only edit your own profile.")
            return redirect("login")

        form = UserProfileForm(request.POST, request.FILES, instance=profile_user)
        if form.is_valid():
            user = form.save()
            messages.success(request, f"Profile for {user.username} updated successfully!")
            if request.user.role == User.Roles.ADMIN:
                return redirect('user_profile', pk=user.pk)
            else:
                return redirect('my_profile')

        return render(request, self.template_name, {"form": form, "profile_user": profile_user})


# ============================================================
# 6. BATCH LIST
# ============================================================
class BatchListView(LoginRequiredMixin, StaffRequiredMixin, View):
    template_name = "account/batch_list.html"

    def get(self, request):
        batches = Batch.objects.select_related('product', 'user').all()

        transaction_type = request.GET.get('transaction_type', '')
        payment_status = request.GET.get('payment_status', '')
        search_query = request.GET.get('search', '').strip()
        date_from = request.GET.get('date_from', '')
        date_to = request.GET.get('date_to', '')
        created_by = request.GET.get('created_by', '')

        created_by_user = None
        if created_by:
            try:
                created_by_user = User.objects.get(pk=created_by)
            except User.DoesNotExist:
                pass

        if transaction_type:
            batches = batches.filter(transaction_type=transaction_type)
        if payment_status:
            batches = batches.filter(payment_status=payment_status)
        if search_query:
            batches = batches.filter(
                Q(batch_code__icontains=search_query) |
                Q(product__name__icontains=search_query) |
                Q(user__username__icontains=search_query)
            )
        if date_from:
            try:
                batches = batches.filter(transaction_date__gte=date_from)
            except:
                pass
        if date_to:
            try:
                batches = batches.filter(transaction_date__lte=date_to)
            except:
                pass
        if created_by:
            batches = batches.filter(created_by_id=created_by)

        batches = batches.order_by('-transaction_date', '-created_at')

        total_batches = batches.count()
        total_amount = batches.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
        total_weight = batches.aggregate(total=Sum('weight'))['total'] or Decimal('0.00')

        status_breakdown = {
            'FULL_PAYMENT': batches.filter(payment_status='FULL_PAYMENT').count(),
            'PARTIAL_PAYMENT': batches.filter(payment_status='PARTIAL_PAYMENT').count(),
            'NO_PAYMENT': batches.filter(payment_status='NO_PAYMENT').count(),
            'UNPAID_OR_PARTIAL': batches.filter(
                payment_status__in=['NO_PAYMENT', 'PARTIAL_PAYMENT']
            ).count(),
        }

        type_breakdown = {
            'BUY': batches.filter(transaction_type='BUY').count(),
            'SELL': batches.filter(transaction_type='SELL').count(),
        }

        context = {
            'batches': batches,
            'total_batches': total_batches,
            'total_amount': total_amount,
            'total_weight': total_weight,
            'status_breakdown': status_breakdown,
            'type_breakdown': type_breakdown,
            'selected_transaction_type': transaction_type,
            'selected_payment_status': payment_status,
            'selected_created_by': created_by,
            'created_by_user': created_by_user,
            'search_query': search_query,
            'date_from': date_from,
            'date_to': date_to,
            'transaction_type_choices': Batch.TransactionType.choices,
            'payment_status_choices': Batch.PaymentStatus.choices,
        }
        return render(request, self.template_name, context)


# ============================================================
# 7. BATCH DETAIL
# ============================================================
class BatchDetailView(LoginRequiredMixin, StaffRequiredMixin, View):
    def get(self, request, pk):
        batch = get_object_or_404(
            Batch.objects.select_related("product", "user"),
            pk=pk,
        )

        user = request.user

        if user.role == User.Roles.VENDOR and batch.user != user:
            messages.error(request, "You do not have permission to view this batch.")
            return redirect("vendor_portal")

        if user.role == User.Roles.CLIENT and batch.user != user:
            messages.error(request, "You do not have permission to view this batch.")
            return redirect("client_portal")

        expenses = batch.expenses.select_related("batch").order_by("-expense_date")
        transactions = batch.transactions.select_related("user", "batch").order_by("-transaction_date")
        expense_form = ExpenseForm()

        total_amount = batch.total_amount or Decimal('0.00')
        amount_paid = batch.amount_paid or Decimal('0.00')

        payment_percentage = Decimal('0.00')
        if total_amount > Decimal('0.00'):
            payment_percentage = (amount_paid / total_amount * 100).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        cost_increase_percent = None
        if batch.dry_weight and batch.applied_rate and batch.applied_rate > Decimal('0.00'):
            cost_increase_percent = (
                (batch.effective_rate / batch.applied_rate * 100) - 100
            ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        allocations = batch.payment_allocations.select_related('transaction').order_by('-allocated_at')

        unallocated_transactions = []
        total_unallocated = Decimal('0.00')

        if user.role == User.Roles.ADMIN:
            txn_type = (
                Transaction.TransactionType.DISBURSEMENT
                if batch.transaction_type == 'BUY'
                else Transaction.TransactionType.RECEIPT
            )

            unallocated_transactions = Transaction.objects.filter(
                user=batch.user,
                transaction_type=txn_type
            ).annotate(
                allocated=Sum('allocations__amount')
            ).filter(
                Q(allocated__lt=F('amount')) | Q(allocated__isnull=True)
            ).order_by('-transaction_date')

            total_paid = Transaction.objects.filter(
                user=batch.user,
                transaction_type=txn_type
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

            total_allocated = PaymentAllocation.objects.filter(
                transaction__user=batch.user,
                transaction__transaction_type=txn_type
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

            total_unallocated = total_paid - total_allocated

        context = {
            "batch": batch,
            "expenses": expenses,
            "transactions": transactions,
            "expense_form": expense_form,
            "payment_percentage": payment_percentage,
            "cost_increase_percent": cost_increase_percent,
            "allocations": allocations,
            "unallocated_transactions": unallocated_transactions,
            "total_unallocated": total_unallocated,
        }
        return render(request, "account/batch_detail.html", context)


# ============================================================
# 8. CREATE BATCH
# ============================================================
class CreateBatchView(LoginRequiredMixin, StaffRequiredMixin, View):
    template_name = "account/batch_create.html"

    def get(self, request):
        form = BatchForm()
        expense_formset = BatchExpenseFormSet(
            queryset=Expense.objects.none(),
            prefix='expenses'
        )
        return render(request, self.template_name, {
            "form": form,
            "expense_formset": expense_formset,
        })

    def post(self, request):
        form = BatchForm(request.POST)
        expense_formset = BatchExpenseFormSet(
            request.POST,
            queryset=Expense.objects.none(),
            prefix='expenses'
        )

        if form.is_valid() and expense_formset.is_valid():
            with db_transaction.atomic():
                batch = form.save(commit=False)
                batch.created_by = request.user
                batch.save()

                expenses = expense_formset.save(commit=False)
                for expense in expenses:
                    expense.batch = batch
                    expense.created_by = request.user
                    expense.save()
                for obj in expense_formset.deleted_objects:
                    obj.delete()

                batch.refresh_from_db()

                amount_paid_now = form.cleaned_data.get('amount_paid_now', Decimal('0.00'))

                if amount_paid_now > Decimal('0.00'):
                    trans_type = (
                        Transaction.TransactionType.DISBURSEMENT
                        if batch.transaction_type == 'BUY'
                        else Transaction.TransactionType.RECEIPT
                    )
                    Transaction.objects.create(
                        user=batch.user,
                        batch=batch,
                        amount=amount_paid_now,
                        transaction_type=trans_type,
                        transaction_date=batch.transaction_date,
                        reference_code=f"AUTO-{batch.batch_code}",
                        notes=f"Initial payment on Batch #{batch.batch_code}",
                        created_by=request.user,
                    )
                    # Signal auto-allocates to linked batch first, then cascades to older batches

            expense_word = "expense" if len(expenses) == 1 else "expenses"
            if amount_paid_now > Decimal('0.00'):
                messages.success(
                    request,
                    f"Batch {batch.batch_code} created with {len(expenses)} {expense_word}. "
                    f"Payment of N{amount_paid_now:,.2f} recorded and auto-allocated."
                )
            else:
                messages.success(
                    request,
                    f"Batch {batch.batch_code} ({batch.transaction_type}) logged with {len(expenses)} {expense_word}."
                )
            return redirect("batch_detail", pk=batch.pk)

        return render(request, self.template_name, {
            "form": form,
            "expense_formset": expense_formset,
        })


# ============================================================
# 9. BATCH EDIT / DELETE
# ============================================================
class BatchEditView(LoginRequiredMixin, AdminRequiredMixin, View):
    template_name = "account/batch_edit.html"

    def get(self, request, pk):
        batch = get_object_or_404(Batch, pk=pk)
        form = BatchForm(instance=batch)
        return render(request, self.template_name, {'form': form, 'batch': batch})

    def post(self, request, pk):
        batch = get_object_or_404(Batch, pk=pk)
        form = BatchForm(request.POST, instance=batch)
        if form.is_valid():
            updated_batch = form.save()
            messages.success(request, f"Batch {updated_batch.batch_code} updated successfully!")
            return redirect('batch_detail', pk=updated_batch.pk)
        return render(request, self.template_name, {'form': form, 'batch': batch})


class BatchDeleteView(LoginRequiredMixin, AdminRequiredMixin, View):
    def get(self, request, pk):
        batch = get_object_or_404(Batch, pk=pk)
        expense_count = batch.expenses.count()
        allocation_count = batch.payment_allocations.count()
        transaction_count = batch.transactions.count()
        context = {
            'batch': batch,
            'expense_count': expense_count,
            'transaction_count': transaction_count,
            'allocation_count': allocation_count,
        }
        return render(request, "account/batch_confirm_delete.html", context)

    def post(self, request, pk):
        from .signals import _allocate_transaction, set_batch_deletion

        batch = get_object_or_404(Batch, pk=pk)
        batch_code = batch.batch_code

        with db_transaction.atomic():
            # Collect transactions that had allocations to this batch
            txn_ids = list(batch.payment_allocations.values_list('transaction_id', flat=True))
            # Unlink transactions from this batch
            batch.transactions.update(batch=None)
            # Suppress reallocation signals during cascade delete
            set_batch_deletion(True)
            try:
                batch.payment_allocations.all().delete()
                batch.expenses.all().delete()
                batch.delete()
            finally:
                set_batch_deletion(False)
            # Explicitly reallocate freed credit to remaining batches
            for txn in Transaction.objects.filter(pk__in=txn_ids):
                _allocate_transaction(txn)

        messages.success(
            request,
            f"Batch {batch_code} deleted. Linked transactions preserved as unallocated credit."
        )
        return redirect('admin_dashboard')


# ============================================================
# 10. EXPENSES
# ============================================================
class AddExpenseView(LoginRequiredMixin, AdminRequiredMixin, View):
    def post(self, request, pk):
        batch = get_object_or_404(Batch, pk=pk)
        form = ExpenseForm(request.POST)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.batch = batch
            expense.created_by = request.user
            expense.save()
            messages.success(request, f"Expense of {expense.amount} added to {batch.batch_code}.")
        else:
            messages.error(request, "Failed to add expense. Please check the submitted values.")
        return redirect("batch_detail", pk=batch.pk)


class ExpenseListView(LoginRequiredMixin, StaffRequiredMixin, View):
    template_name = "account/expense_list.html"

    def get(self, request):
        expenses = Expense.objects.select_related('batch', 'batch__user').all()

        category = request.GET.get('category', '')
        date_from = request.GET.get('date_from', '')
        date_to = request.GET.get('date_to', '')
        search = request.GET.get('search', '').strip()
        created_by = request.GET.get('created_by', '')

        created_by_user = None
        if created_by:
            try:
                created_by_user = User.objects.get(pk=created_by)
            except User.DoesNotExist:
                pass

        if category:
            expenses = expenses.filter(category=category)
        if date_from:
            expenses = expenses.filter(expense_date__gte=date_from)
        if date_to:
            expenses = expenses.filter(expense_date__lte=date_to)
        if search:
            expenses = expenses.filter(
                Q(title__icontains=search) | Q(batch__batch_code__icontains=search)
            )
        if created_by:
            expenses = expenses.filter(created_by_id=created_by)

        expenses = expenses.order_by('-expense_date', '-created_at')

        total_amount = expenses.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        category_breakdown = expenses.values('category').annotate(
            total=Sum('amount'), count=Count('id')
        ).order_by('-total')

        context = {
            'expenses': expenses,
            'total_amount': total_amount,
            'category_breakdown': category_breakdown,
            'category_choices': Expense.ExpenseCategory.choices,
            'selected_category': category,
            'selected_created_by': created_by,
            'created_by_user': created_by_user,
            'date_from': date_from,
            'date_to': date_to,
            'search_query': search,
        }
        return render(request, self.template_name, context)


class ExpenseCreateView(LoginRequiredMixin, StaffRequiredMixin, View):
    template_name = "account/expense_form.html"

    def get(self, request):
        form = ExpenseForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = ExpenseForm(request.POST)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.created_by = request.user
            expense = form.save()
            messages.success(request, f"N{expense.amount:,.2f} recorded for {expense.get_category_display()}.")
            return redirect('expense_list')
        return render(request, self.template_name, {'form': form})


class ExpenseUpdateView(LoginRequiredMixin, AdminRequiredMixin, View):
    template_name = "account/expense_form.html"

    def get(self, request, pk):
        expense = get_object_or_404(Expense.objects.select_related('batch'), pk=pk)
        form = ExpenseForm(instance=expense)
        return render(request, self.template_name, {'form': form, 'expense': expense})

    def post(self, request, pk):
        expense = get_object_or_404(Expense.objects.select_related('batch'), pk=pk)
        form = ExpenseForm(request.POST, instance=expense)
        if form.is_valid():
            form.save()
            messages.success(request, "Expense updated successfully.")
            return redirect('expense_list')
        return render(request, self.template_name, {'form': form, 'expense': expense})


class DeleteExpenseView(LoginRequiredMixin, AdminRequiredMixin, View):
    def post(self, request, pk):
        expense = get_object_or_404(Expense, pk=pk)
        if expense.batch:
            batch_pk = expense.batch.pk
            expense.delete()
            messages.success(request, "Expense deleted successfully.")
            return redirect('batch_detail', pk=batch_pk)
        else:
            expense.delete()
            messages.success(request, "General expense deleted successfully.")
            return redirect('expense_list')


# ============================================================
# 11. RECORD TRANSACTION
# ============================================================
class RecordTransactionView(LoginRequiredMixin, ManagerRequiredMixin, View):
    template_name = "account/transaction_add.html"

    def get(self, request):
        form = TransactionForm(
            request_user=request.user
        )

        return render(
            request,
            self.template_name,
            {"form": form}
        )

    def post(self, request):
        form = TransactionForm(
            request.POST,
            request_user=request.user
        )

        if not form.is_valid():
            return render(
                request,
                self.template_name,
                {"form": form}
            )

        # ==========================================================
        # EXTRA SERVER-SIDE SECURITY CHECK
        #
        # Managers can ONLY record:
        #
        #     Vendor → DISBURSEMENT
        #
        # They cannot record:
        #
        #     Client → RECEIPT
        #
        # This is intentionally checked again here even though the
        # TransactionForm already validates it.
        # ==========================================================

        if request.user.role == User.Roles.MANAGER:

            transaction_type = form.cleaned_data.get(
                "transaction_type"
            )

            partner = form.cleaned_data.get("user")

            if transaction_type != Transaction.TransactionType.DISBURSEMENT:
                messages.error(
                    request,
                    "Managers can only record payments made to vendors."
                )
                return render(
                    request,
                    self.template_name,
                    {"form": form}
                )

            if not partner or partner.role != User.Roles.VENDOR:
                messages.error(
                    request,
                    "Managers can only record payments for vendors."
                )
                return render(
                    request,
                    self.template_name,
                    {"form": form}
                )

        # ==========================================================
        # SAVE TRANSACTION
        #
        # Existing behavior preserved.
        # ==========================================================

        with db_transaction.atomic():

            transaction = form.save(
                commit=False
            )

            transaction.created_by = request.user

            transaction.save()

            # Signal auto-allocates to outstanding batches automatically

        # ==========================================================
        # TRANSACTION RESULT
        # ==========================================================

        txn_ref = (
            transaction.reference_code
            or f"#{transaction.pk}"
        )

        allocations = transaction.allocations.select_related(
            'batch'
        )

        total_allocated = (
            allocations.aggregate(
                t=Sum('amount')
            )['t']
            or Decimal('0.00')
        )

        remaining = transaction.unallocated_amount

        paid_batches = [
            f"{a.batch.batch_code} (N{a.amount:,.2f})"
            for a in allocations
        ]

        # ==========================================================
        # SUCCESS MESSAGE
        # ==========================================================

        if paid_batches:

            if remaining > Decimal('0.00'):

                msg = (
                    f"Transaction {txn_ref} recorded. "
                    f"Paid: {'; '.join(paid_batches)}. "
                    f"N{remaining:,.2f} remains as unallocated credit."
                )

            else:

                msg = (
                    f"Transaction {txn_ref} recorded. "
                    f"Fully allocated: {'; '.join(paid_batches)}."
                )

        else:

            msg = (
                f"Transaction {txn_ref} recorded as unallocated credit "
                f"(N{transaction.amount:,.2f})."
            )

        messages.success(
            request,
            msg
        )

        return redirect(
            "admin_dashboard"
        )


# ============================================================
# 12. PAYMENT LIST & DETAIL
# ============================================================
class PaymentListView(LoginRequiredMixin, ManagerRequiredMixin, View):
    template_name = "account/payment_list.html"

    def get(self, request):
        transactions = Transaction.objects.select_related('user', 'batch').all()

        tx_type = request.GET.get('transaction_type', '')
        user_id = request.GET.get('user_id', '')
        date_from = request.GET.get('date_from', '')
        date_to = request.GET.get('date_to', '')
        search = request.GET.get('search', '').strip()
        created_by = request.GET.get('created_by', '')

        created_by_user = None
        if created_by:
            try:
                created_by_user = User.objects.get(pk=created_by)
            except User.DoesNotExist:
                pass

        if tx_type:
            transactions = transactions.filter(transaction_type=tx_type)
        if user_id:
            transactions = transactions.filter(user_id=user_id)
        if date_from:
            transactions = transactions.filter(transaction_date__gte=date_from)
        if date_to:
            transactions = transactions.filter(transaction_date__lte=date_to)
        if search:
            transactions = transactions.filter(
                Q(reference_code__icontains=search) |
                Q(notes__icontains=search) |
                Q(user__username__icontains=search)
            )
        if created_by:
            transactions = transactions.filter(created_by_id=created_by)

        transactions = transactions.order_by('-transaction_date', '-created_at')

        total_receipts = transactions.filter(
            transaction_type=Transaction.TransactionType.RECEIPT
        ).aggregate(t=Sum('amount'))['t'] or Decimal('0.00')

        total_disbursements = transactions.filter(
            transaction_type=Transaction.TransactionType.DISBURSEMENT
        ).aggregate(t=Sum('amount'))['t'] or Decimal('0.00')

        txn_data = []
        for txn in transactions:
            allocated = txn.allocations.aggregate(t=Sum('amount'))['t'] or Decimal('0.00')
            unallocated = (txn.amount or Decimal('0.00')) - allocated
            txn_data.append({
                'txn': txn,
                'allocated': allocated,
                'unallocated': unallocated,
                'is_fully_allocated': unallocated <= Decimal('0.00'),
            })

        context = {
            'txn_data': txn_data,
            'total_receipts': total_receipts,
            'total_disbursements': total_disbursements,
            'net_flow': total_receipts - total_disbursements,
            'txn_type_choices': Transaction.TransactionType.choices,
            'users': User.objects.exclude(role=User.Roles.ADMIN).order_by('username'),
            'selected_txn_type': tx_type,
            'selected_user': user_id,
            'selected_created_by': created_by,
            'created_by_user': created_by_user,
            'date_from': date_from,
            'date_to': date_to,
            'search_query': search,
        }
        return render(request, self.template_name, context)


class PaymentDetailView(LoginRequiredMixin, AdminRequiredMixin, View):
    template_name = "account/payment_detail.html"

    def get(self, request, pk):
        txn = get_object_or_404(
            Transaction.objects.select_related('user', 'batch'),
            pk=pk
        )

        allocations = txn.allocations.select_related(
            'batch', 'batch__user', 'allocated_by'
        ).order_by('-allocated_at')

        allocated_total = allocations.aggregate(t=Sum('amount'))['t'] or Decimal('0.00')
        unallocated = (txn.amount or Decimal('0.00')) - allocated_total

        outstanding = []
        if unallocated > Decimal('0.00'):
            target_type = (
                Batch.TransactionType.BUY
                if txn.transaction_type == Transaction.TransactionType.DISBURSEMENT
                else Batch.TransactionType.SELL
            )
            outstanding = (
                Batch.objects.filter(
                    user=txn.user,
                    transaction_type=target_type,
                )
                .annotate(
                    due=F('total_amount') - Coalesce(F('amount_paid'), Decimal('0.00'), output_field=DecimalField())
                )
                .filter(due__gt=Decimal('0.00'))
                .order_by('transaction_date', 'created_at')
            )

        context = {
            'txn': txn,
            'allocations': allocations,
            'allocated_total': allocated_total,
            'unallocated': unallocated,
            'is_fully_allocated': unallocated <= Decimal('0.00'),
            'outstanding': outstanding,
        }
        return render(request, self.template_name, context)
    

# ============================================================
# 13. ALLOCATE / REMOVE / RECORD DIRECT PAYMENT
# ============================================================
class AllocatePaymentView(LoginRequiredMixin, AdminRequiredMixin, View):
    def post(self, request, batch_pk):
        batch = get_object_or_404(Batch, pk=batch_pk)
        transaction_id = request.POST.get('transaction_id')
        amount_str = request.POST.get('amount', '').strip()

        if not transaction_id:
            messages.error(request, "Please select a transaction to allocate.")
            return redirect('batch_detail', pk=batch_pk)

        transaction = get_object_or_404(Transaction, pk=transaction_id, user=batch.user)

        try:
            amount = Decimal(amount_str)
        except Exception:
            messages.error(request, "Invalid amount.")
            return redirect('batch_detail', pk=batch_pk)

        if amount <= Decimal('0.00'):
            messages.error(request, "Allocation amount must be greater than zero.")
            return redirect('batch_detail', pk=batch_pk)

        allocated = PaymentAllocation.objects.filter(transaction=transaction).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')
        unallocated = (transaction.amount or Decimal('0.00')) - allocated

        if amount > unallocated:
            messages.error(
                request,
                f"Amount exceeds unallocated balance. Available: N{unallocated:,.2f}"
            )
            return redirect('batch_detail', pk=batch_pk)

        if amount > batch.balance_due:
            messages.error(
                request,
                f"Amount exceeds batch balance due. Balance: N{batch.balance_due:,.2f}"
            )
            return redirect('batch_detail', pk=batch_pk)

        PaymentAllocation.objects.create(
            transaction=transaction,
            batch=batch,
            amount=amount,
            allocated_by=request.user
        )

        messages.success(
            request,
            f"N{amount:,.2f} allocated from {transaction.reference_code or 'Payment'} to {batch.batch_code}."
        )
        return redirect('batch_detail', pk=batch_pk)


class RemoveAllocationView(LoginRequiredMixin, AdminRequiredMixin, View):
    def post(self, request, allocation_pk):
        allocation = get_object_or_404(PaymentAllocation, pk=allocation_pk)
        batch_pk = allocation.batch.pk
        allocation.delete()
        messages.success(request, "Payment allocation removed. Credit returned to user's account.")
        return redirect('batch_detail', pk=batch_pk)


class RecordPaymentView(LoginRequiredMixin, AdminRequiredMixin, View):
    def post(self, request, batch_pk):
        batch = get_object_or_404(Batch, pk=batch_pk)
        amount_str = request.POST.get('payment_amount', '').strip()

        if not amount_str:
            messages.error(request, "Please enter a payment amount.")
            return redirect('batch_detail', pk=batch_pk)

        try:
            amount = Decimal(amount_str)
        except Exception:
            messages.error(request, "Invalid amount.")
            return redirect('batch_detail', pk=batch_pk)

        if amount <= Decimal('0.00'):
            messages.error(request, "Payment amount must be greater than zero.")
            return redirect('batch_detail', pk=batch_pk)

        if amount > batch.balance_due:
            messages.error(
                request,
                f"Amount exceeds balance due. Balance: N{batch.balance_due:,.2f}"
            )
            return redirect('batch_detail', pk=batch_pk)

        trans_type = (
            Transaction.TransactionType.DISBURSEMENT
            if batch.transaction_type == 'BUY'
            else Transaction.TransactionType.RECEIPT
        )

        with db_transaction.atomic():
            transaction = Transaction.objects.create(
                user=batch.user,
                batch=batch,
                amount=amount,
                transaction_type=trans_type,
                transaction_date=timezone.now().date(),
                reference_code=f"PAY-{batch.batch_code}-{timezone.now().strftime('%Y%m%d%H%M%S')}",
                notes=f"Payment on Batch #{batch.batch_code} via detail page",
                created_by=request.user,
            )
            # Signal auto-allocates to linked batch first, then cascades to older batches

        messages.success(
            request,
            f"N{amount:,.2f} payment recorded and auto-allocated to {batch.batch_code}."
        )
        return redirect('batch_detail', pk=batch_pk)


# ============================================================
# 14. UPDATE DRY WEIGHT
# ============================================================
class UpdateDryWeightView(LoginRequiredMixin, AdminRequiredMixin, View):
    def post(self, request, pk):
        batch = get_object_or_404(Batch, pk=pk)
        dry_weight_str = request.POST.get('dry_weight', '').strip()

        if not dry_weight_str:
            messages.error(request, "Please enter a dry weight value.")
            return redirect("batch_detail", pk=batch.pk)

        try:
            dry_weight = Decimal(dry_weight_str)
        except Exception:
            messages.error(request, "Invalid dry weight value.")
            return redirect("batch_detail", pk=batch.pk)

        if dry_weight < Decimal('0.00'):
            messages.error(request, "Dry weight cannot be negative.")
            return redirect("batch_detail", pk=batch.pk)

        if dry_weight > batch.weight:
            messages.error(
                request,
                f"Dry weight ({dry_weight}kg) cannot exceed received weight ({batch.weight}kg)."
            )
            return redirect("batch_detail", pk=batch.pk)

        batch.dry_weight = dry_weight
        batch.save()

        messages.success(
            request,
            f"Dry weight updated to {dry_weight}kg. "
            f"Moisture loss: {batch.moisture_loss}kg ({batch.moisture_loss_percent}%). "
            f"Effective rate: N{batch.effective_rate}/kg (dry)."
        )
        return redirect("batch_detail", pk=batch.pk)


# ============================================================
# 15. PRODUCTS
# ============================================================
class ProductListView(LoginRequiredMixin, StaffRequiredMixin, ListView):
    model = Product
    template_name = "account/product_list.html"
    context_object_name = "products"

    def get_queryset(self):
        return Product.objects.annotate(
            user_count=Count('user_rates', distinct=True),
            batch_count=Count('batches', distinct=True),
        ).order_by('-is_active', 'name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["total_products"] = Product.objects.count()
        context["active_products"] = Product.objects.filter(is_active=True).count()
        context["inactive_products"] = Product.objects.filter(is_active=False).count()
        context["products_with_batches"] = Product.objects.filter(batches__isnull=False).distinct().count()
        return context


class ProductCreateView(LoginRequiredMixin, StaffRequiredMixin, CreateView):
    model = Product
    form_class = ProductForm
    template_name = "account/product_form.html"
    success_url = reverse_lazy("product_list")

    def form_valid(self, form):
        messages.success(self.request, f"Product '{form.instance.name}' created successfully!")
        return super().form_valid(form)


class ProductUpdateView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    model = Product
    form_class = ProductForm
    template_name = "account/product_form.html"
    success_url = reverse_lazy("product_list")

    def form_valid(self, form):
        messages.success(self.request, f"Product '{form.instance.name}' updated successfully!")
        return super().form_valid(form)


# ============================================================
# 16. USER DIRECTORY
# ============================================================
class UserListView(LoginRequiredMixin, ManagerRequiredMixin, View):
    template_name = "account/user_list.html"

    def get(self, request):
        users = User.objects.filter(
            role__in=[User.Roles.VENDOR, User.Roles.CLIENT]
        ).select_related('ledger').prefetch_related(
            'batches', 'product_rates', 'transactions'
        ).order_by('role', 'username')

        role_filter = request.GET.get('role', '')
        if role_filter in [User.Roles.VENDOR, User.Roles.CLIENT]:
            users = users.filter(role=role_filter)

        search = request.GET.get('search', '').strip()
        if search:
            users = users.filter(
                Q(username__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(phone__icontains=search)
            )

        filter_type = request.GET.get('filter_type', 'all')

        user_data = []
        total_clients_owe = Decimal('0.00')
        total_we_owe_vendors = Decimal('0.00')
        total_vendors_owe_us = Decimal('0.00')
        total_we_owe_clients = Decimal('0.00')
        total_clients_owe_kg = Decimal('0.00')
        total_vendors_owe_us_kg = Decimal('0.00')
        total_we_owe_clients_kg = Decimal('0.00')

        for u in users:
            ledger = getattr(u, 'ledger', None)
            balance = ledger.balance if ledger else Decimal('0.00')
            batches = list(u.batches.all())

            paid_count = sum(1 for b in batches if b.payment_status == Batch.PaymentStatus.FULL_PAYMENT)
            partial_count = sum(1 for b in batches if b.payment_status == Batch.PaymentStatus.PARTIAL_PAYMENT)
            unpaid_count = sum(1 for b in batches if b.payment_status == Batch.PaymentStatus.NO_PAYMENT)
            batch_count = len(batches)

            tx_type = 'SELL' if u.role == User.Roles.CLIENT else 'BUY'
            rate = self._latest_rate(u, tx_type)

            if u.role == User.Roles.CLIENT:
                owes_us_money = max(Decimal('0.00'), balance)
                we_owe_money = max(Decimal('0.00'), -balance)
                is_debtor = balance > Decimal('0.00')
                is_creditor = balance < Decimal('0.00')
            else:
                owes_us_money = max(Decimal('0.00'), -balance)
                we_owe_money = max(Decimal('0.00'), balance)
                is_debtor = balance < Decimal('0.00')
                is_creditor = balance > Decimal('0.00')

            owes_us_kg = Decimal('0.00')
            we_owe_kg = Decimal('0.00')
            if rate > Decimal('0.00'):
                if owes_us_money > Decimal('0.00'):
                    owes_us_kg = (owes_us_money / rate).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                if we_owe_money > Decimal('0.00'):
                    we_owe_kg = (we_owe_money / rate).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

            if batch_count == 0:
                pay_category = 'no_batches'
            elif unpaid_count > 0:
                pay_category = 'has_unpaid'
            elif partial_count > 0:
                pay_category = 'has_partial'
            else:
                pay_category = 'fully_paid'

            if filter_type == 'debtor' and not is_debtor:
                continue
            if filter_type == 'creditor' and not is_creditor:
                continue
            if filter_type == 'has_unpaid' and unpaid_count == 0:
                continue
            if filter_type == 'has_partial' and partial_count == 0:
                continue
            if filter_type == 'fully_paid' and (unpaid_count > 0 or partial_count > 0 or batch_count == 0):
                continue
            if filter_type == 'settled' and (is_debtor or is_creditor):
                continue

            unallocated = Decimal('0.00')
            for txn in u.transactions.all():
                unallocated += txn.unallocated_amount

            if u.role == User.Roles.CLIENT:
                total_clients_owe += owes_us_money
                total_we_owe_clients += we_owe_money
                total_we_owe_clients_kg += we_owe_kg
            else:
                total_we_owe_vendors += we_owe_money
                total_vendors_owe_us += owes_us_money
                total_vendors_owe_us_kg += owes_us_kg

            user_data.append({
                'user': u,
                'is_suspended': not u.is_active,
                'ledger': ledger,
                'balance': balance,
                'batch_count': batch_count,
                'paid_count': paid_count,
                'partial_count': partial_count,
                'unpaid_count': unpaid_count,
                'owes_us_money': owes_us_money,
                'owes_us_kg': owes_us_kg,
                'we_owe_money': we_owe_money,
                'we_owe_kg': we_owe_kg,
                'is_debtor': is_debtor,
                'is_creditor': is_creditor,
                'pay_category': pay_category,
                'unallocated': unallocated,
                'product_count': u.product_rates.count(),
                'rate': rate,
            })

        context = {
            'user_data': user_data,
            'total_count': len(user_data),
            'vendor_count': sum(1 for d in user_data if d['user'].role == User.Roles.VENDOR),
            'client_count': sum(1 for d in user_data if d['user'].role == User.Roles.CLIENT),
            'total_clients_owe': total_clients_owe,
            'total_clients_owe_kg': total_clients_owe_kg,
            'total_we_owe_vendors': total_we_owe_vendors,
            'total_vendors_owe_us': total_vendors_owe_us,
            'total_vendors_owe_us_kg': total_vendors_owe_us_kg,
            'total_we_owe_clients': total_we_owe_clients,
            'total_we_owe_clients_kg': total_we_owe_clients_kg,
            'selected_role': role_filter,
            'selected_filter': filter_type,
            'search_query': search,
            'role_choices': [
                ('', 'All Partners'),
                (User.Roles.VENDOR, 'Farmers (Vendors)'),
                (User.Roles.CLIENT, 'Buyers (Clients)'),
            ],
            'filter_choices': [
                ('all', 'All Statuses'),
                ('debtor', 'Debtors (Owe Us)'),
                ('creditor', 'Creditors (We Owe Them)'),
                ('has_unpaid', 'Has Unpaid Batches'),
                ('has_partial', 'Has Partial Payments'),
                ('fully_paid', 'Fully Paid Up'),
                ('settled', 'Zero Balance'),
            ],
        }
        return render(request, self.template_name, context)

    def _latest_rate(self, user, tx_type):
        latest_batch = Batch.objects.filter(
            user=user, transaction_type=tx_type
        ).order_by('-transaction_date', '-created_at').first()
        if latest_batch and latest_batch.applied_rate and latest_batch.applied_rate > 0:
            return latest_batch.applied_rate
        rate_obj = UserProductRate.objects.filter(user=user).order_by('-id').first()
        if rate_obj and rate_obj.rate and rate_obj.rate > 0:
            return rate_obj.rate
        return Decimal('0.00')


# ============================================================
# 17. STAFF DIRECTORY
# ============================================================

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from .models import User



class StaffListView(LoginRequiredMixin, ManagerRequiredMixin, View):
    template_name = "account/staff_list.html"

    def get(self, request):
        staff_qs = User.objects.filter(
            role__in=[
                User.Roles.ADMIN,
                User.Roles.MANAGER,
                User.Roles.STAFF,
            ]
        ).annotate(
            batches_created_count=Count(
                'batches_created',
                distinct=True
            ),
            expenses_created_count=Count(
                'expenses_created',
                distinct=True
            ),
            transactions_created_count=Count(
                'transactions_created',
                distinct=True
            ),
        )

        # -----------------------------------------
        # SEARCH
        # -----------------------------------------
        search = request.GET.get('search', '').strip()

        if search:
            staff_qs = staff_qs.filter(
                Q(username__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(email__icontains=search)
            )

        # -----------------------------------------
        # ROLE FILTER
        # -----------------------------------------
        role_filter = request.GET.get('role', '').strip()

        valid_roles = [
            User.Roles.ADMIN,
            User.Roles.MANAGER,
            User.Roles.STAFF,
        ]

        if role_filter in valid_roles:
            staff_qs = staff_qs.filter(role=role_filter)

        # -----------------------------------------
        # STATUS FILTER
        # -----------------------------------------
        status_filter = request.GET.get('status', '').strip()

        if status_filter == 'active':
            staff_qs = staff_qs.filter(is_active=True)

        elif status_filter == 'suspended':
            staff_qs = staff_qs.filter(is_active=False)

        # -----------------------------------------
        # ORDER
        # -----------------------------------------
        staff_qs = staff_qs.order_by(
            'role',
            '-is_active',
            'username'
        )

        # -----------------------------------------
        # COUNTS
        # -----------------------------------------
        base_staff_qs = User.objects.filter(
            role__in=[
                User.Roles.ADMIN,
                User.Roles.MANAGER,
                User.Roles.STAFF,
            ]
        )

        context = {
            'staff_list': staff_qs,

            # Current filtered result count
            'total_staff': staff_qs.count(),

            # Overall counts
            'all_staff_count': base_staff_qs.count(),
            'active_staff_count': base_staff_qs.filter(
                is_active=True
            ).count(),
            'suspended_staff_count': base_staff_qs.filter(
                is_active=False
            ).count(),

            # Role counts
            'admin_count': base_staff_qs.filter(
                role=User.Roles.ADMIN
            ).count(),

            'manager_count': base_staff_qs.filter(
                role=User.Roles.MANAGER
            ).count(),

            'staff_count': base_staff_qs.filter(
                role=User.Roles.STAFF
            ).count(),

            'selected_role': role_filter,
            'selected_status': status_filter,
            'search_query': search,

            'role_choices': [
                ('', 'All Staff'),
                (User.Roles.ADMIN, 'Super Admins'),
                (User.Roles.MANAGER, 'Managers'),
                (User.Roles.STAFF, 'Operations Staff'),
            ],

            'status_choices': [
                ('', 'All Statuses'),
                ('active', 'Active'),
                ('suspended', 'Suspended'),
            ],
        }

        return render(
            request,
            self.template_name,
            context
        )


class StaffToggleStatusView(
    LoginRequiredMixin,
    ManagerRequiredMixin,
    View
):
    """
    Suspend or reactivate a staff account.

    Uses Django's built-in is_active field.

    POST only.
    """

    def post(self, request, pk):
        staff = get_object_or_404(
            User,
            pk=pk,
            role__in=[
                User.Roles.ADMIN,
                User.Roles.MANAGER,
                User.Roles.STAFF,
            ]
        )

        # -----------------------------------------
        # NEVER ALLOW A USER TO SUSPEND THEMSELVES
        # -----------------------------------------
        if staff.pk == request.user.pk:
            messages.error(
                request,
                "You cannot suspend your own account."
            )
            return redirect('staff_list')

        # -----------------------------------------
        # PROTECT SUPERUSERS
        # -----------------------------------------
        if staff.is_superuser:
            messages.error(
                request,
                "This account is a superuser and cannot be suspended here."
            )
            return redirect('staff_list')

        # -----------------------------------------
        # TOGGLE STATUS
        # -----------------------------------------
        if staff.is_active:
            staff.is_active = False
            staff.save(update_fields=['is_active'])

            messages.success(
                request,
                f"{staff.get_full_name() or staff.username} has been suspended."
            )

        else:
            staff.is_active = True
            staff.save(update_fields=['is_active'])

            messages.success(
                request,
                f"{staff.get_full_name() or staff.username} has been reactivated."
            )

        return redirect('staff_list')













class StaffLstView(LoginRequiredMixin, ManagerRequiredMixin, View):
    template_name = "account/staff_list.html"

    def get(self, request):
        staff_qs = User.objects.filter(
            role__in=[
                User.Roles.ADMIN,
                User.Roles.MANAGER,
                User.Roles.STAFF,
            ]
        ).annotate(
            batches_created_count=Count('batches_created', distinct=True),
            expenses_created_count=Count('expenses_created', distinct=True),
            transactions_created_count=Count('transactions_created', distinct=True),
        ).order_by('role', 'username')

        search = request.GET.get('search', '').strip()
        if search:
            staff_qs = staff_qs.filter(
                Q(username__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(email__icontains=search)
            )

        role_filter = request.GET.get('role', '')
        if role_filter in [User.Roles.ADMIN, User.Roles.MANAGER, User.Roles.STAFF]:
            staff_qs = staff_qs.filter(role=role_filter)

        context = {
            'staff_list': staff_qs,
            'total_staff': staff_qs.count(),
            'admin_count': staff_qs.filter(role=User.Roles.ADMIN).count(),
            'manager_count': staff_qs.filter(role=User.Roles.MANAGER).count(),
            'staff_count': staff_qs.filter(role=User.Roles.STAFF).count(),
            'selected_role': role_filter,
            'search_query': search,
            'role_choices': [
                ('', 'All Staff'),
                (User.Roles.ADMIN, 'Super Admins'),
                (User.Roles.MANAGER, 'Managers'),
                (User.Roles.STAFF, 'Operations Staff'),
            ],
        }
        return render(request, self.template_name, context)


# ============================================================
# 18. USER CREATION
# ============================================================
class UserCreateView(LoginRequiredMixin, ManagerRequiredMixin, View):
    template_name = "account/user_form.html"

    def get(self, request):
        user_form = UserCreateForm(
            request_user=request.user
        )

        product_formset = AssignProductFormSet(
            prefix='products'
        )

        return render(
            request,
            self.template_name,
            {
                'form': user_form,
                'product_formset': product_formset,
            }
        )

    def post(self, request):
        user_form = UserCreateForm(
            request.POST,
            request_user=request.user
        )

        product_formset = AssignProductFormSet(
            request.POST,
            prefix='products'
        )

        if user_form.is_valid() and product_formset.is_valid():

            # ======================================================
            # EXTRA SERVER-SIDE SECURITY
            # ======================================================

            requested_role = user_form.cleaned_data.get('role')

            if request.user.role == User.Roles.MANAGER:

                if requested_role not in [
                    User.Roles.VENDOR,
                    User.Roles.CLIENT,
                ]:
                    messages.error(
                        request,
                        "Managers can only create Vendors and Clients."
                    )

                    return render(
                        request,
                        self.template_name,
                        {
                            'form': user_form,
                            'product_formset': product_formset,
                        }
                    )

            # ======================================================
            # CREATE USER
            # ======================================================

            user = user_form.save()

            # ======================================================
            # ASSIGN PRODUCTS
            # ======================================================

            for form in product_formset:

                if (
                    form.cleaned_data
                    and form.cleaned_data.get('product')
                ):
                    UserProductRate.objects.create(
                        user=user,
                        product=form.cleaned_data['product'],
                        rate=form.cleaned_data['rate']
                    )

            # ======================================================
            # SUCCESS
            # ======================================================

            messages.success(
                request,
                f"New {user.get_role_display()} "
                f"'{user.username}' created successfully. "
                f"They can now login with the password you set."
            )

            return redirect(
                'user_profile',
                pk=user.pk
            )

        return render(
            request,
            self.template_name,
            {
                'form': user_form,
                'product_formset': product_formset,
            }
        )


# ============================================================
# 19. VENDOR / CLIENT PORTALS
# ============================================================
class VendorPortalView(LoginRequiredMixin, VendorRequiredMixin, View):
    def get(self, request):
        vendor = request.user
        batches = (
            Batch.objects.filter(
                user=vendor,
                transaction_type=Batch.TransactionType.BUY,
            )
            .select_related("product")
            .order_by("-transaction_date")
        )
        ledger, _ = Ledger.objects.get_or_create(user=vendor)
        transactions = Transaction.objects.filter(user=vendor).order_by("-transaction_date")
        total_weight = batches.aggregate(total=Sum("weight"))["total"] or Decimal("0.00")

        context = {
            "batches": batches,
            "ledger": ledger,
            "transactions": transactions,
            "total_weight": total_weight,
        }
        return render(request, "account/vendor_portal.html", context)


class ClientPortalView(LoginRequiredMixin, ClientRequiredMixin, View):
    def get(self, request):
        client = request.user
        batches = (
            Batch.objects.filter(
                user=client,
                transaction_type=Batch.TransactionType.SELL,
            )
            .select_related("product")
            .order_by("-transaction_date")
        )
        ledger, _ = Ledger.objects.get_or_create(user=client)
        transactions = Transaction.objects.filter(user=client).order_by("-transaction_date")
        total_weight = batches.aggregate(total=Sum("weight"))["total"] or Decimal("0.00")

        context = {
            "batches": batches,
            "ledger": ledger,
            "transactions": transactions,
            "total_weight": total_weight,
        }
        return render(request, "account/client_portal.html", context)


# ============================================================
# 20. AJAX HELPERS
# ============================================================
class GetUsersByTypeView(LoginRequiredMixin, StaffRequiredMixin, View):
    def get(self, request):
        tx_type = request.GET.get('transaction_type', '')
        if tx_type == 'BUY':
            users = User.objects.filter(role=User.Roles.VENDOR, is_active=True)
        elif tx_type == 'SELL':
            users = User.objects.filter(role=User.Roles.CLIENT, is_active=True)
        else:
            users = User.objects.none()

        data = [
            {
                'id': u.id,
                'username': u.username,
                'label': f"{u.username} ({u.get_role_display()})"
            }
            for u in users
        ]
        return JsonResponse({'users': data})


class GetProductsByUserView(LoginRequiredMixin, StaffRequiredMixin, View):
    def get(self, request):
        user_id = request.GET.get('user_id')
        if not user_id:
            return JsonResponse({'products': []})

        products = Product.objects.filter(
            user_rates__user_id=user_id,
            is_active=True
        ).distinct().values('id', 'name', 'unit')

        return JsonResponse({'products': list(products)})


class GetUserProductRateView(LoginRequiredMixin, StaffRequiredMixin, View):
    def get(self, request):
        user_id = request.GET.get('user_id')
        product_id = request.GET.get('product_id')

        try:
            rate_obj = UserProductRate.objects.get(user_id=user_id, product_id=product_id)
            return JsonResponse({'rate': str(rate_obj.rate), 'found': True})
        except UserProductRate.DoesNotExist:
            return JsonResponse({'rate': '0.00', 'found': False})


class GetOutstandingBatchesView(LoginRequiredMixin, StaffRequiredMixin, View):
    def get(self, request):
        user_id = request.GET.get('user_id')
        tx_type = request.GET.get('transaction_type')

        if not user_id:
            return JsonResponse({'batches': [], 'total_due': '0.00'})

        batch_type = 'BUY' if tx_type == 'DISBURSEMENT' else 'SELL'

        outstanding = Batch.objects.filter(
            user_id=user_id,
            transaction_type=batch_type,
            total_amount__gt=Coalesce(F('amount_paid'), Decimal('0.00'), output_field=DecimalField())
        ).order_by('transaction_date', 'created_at')

        batch_list = []
        total_due = Decimal('0.00')

        for batch in outstanding:
            bal = batch.balance_due
            if bal > Decimal('0.00'):
                total_due += bal
                batch_list.append({
                    'id': batch.id,
                    'batch_code': batch.batch_code,
                    'balance_due': str(bal),
                    'total_amount': str(batch.total_amount or Decimal('0.00')),
                    'amount_paid': str(batch.amount_paid or Decimal('0.00')),
                    'transaction_date': batch.transaction_date.isoformat(),
                    'product__name': batch.product.name if batch.product else None,
                })

        return JsonResponse({
            'batches': batch_list,
            'total_due': str(total_due)
        })



# ============================================================
# STAFF DELETE
# ============================================================
class StaffDeleteView(LoginRequiredMixin, AdminRequiredMixin, View):
    """Delete a staff member. Batches where they are the primary party block deletion.
    Records they created (as created_by) are preserved with NULL author."""
    template_name = "account/staff_confirm_delete.html"

    def get(self, request, pk):
        staff = get_object_or_404(
            User.objects.filter(role__in=[
                User.Roles.ADMIN, User.Roles.MANAGER, User.Roles.STAFF
            ]),
            pk=pk
        )

        if staff == request.user:
            messages.error(request, "You cannot delete your own account.")
            return redirect('staff_list')

        primary_batches = staff.batches.count()
        authored_batches = staff.batches_created.count()
        authored_expenses = staff.expenses_created.count()
        authored_transactions = staff.transactions_created.count()

        context = {
            'staff': staff,
            'primary_batches': primary_batches,
            'authored_batches': authored_batches,
            'authored_expenses': authored_expenses,
            'authored_transactions': authored_transactions,
            'can_delete': primary_batches == 0,
        }
        return render(request, self.template_name, context)

    def post(self, request, pk):
        staff = get_object_or_404(
            User.objects.filter(role__in=[
                User.Roles.ADMIN, User.Roles.MANAGER, User.Roles.STAFF
            ]),
            pk=pk
        )

        if staff == request.user:
            messages.error(request, "You cannot delete your own account.")
            return redirect('staff_list')

        if staff.batches.exists():
            messages.error(
                request,
                f"Cannot delete {staff.username} because they are the primary party on {staff.batches.count()} batch(es). "
                f"Reassign those batches first."
            )
            return redirect('staff_list')

        username = staff.username
        staff.delete()
        messages.success(request, f"Staff member '{username}' has been deleted.")
        return redirect('staff_list')
    




from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction as db_transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

# Make sure User is imported
# from .models import User


class UserDeleteView(LoginRequiredMixin, AdminRequiredMixin, View):
    template_name = "account/user_confirm_delete.html"

    def get(self, request, pk):
        user = get_object_or_404(User, pk=pk)

        # ==========================================================
        # NEVER ALLOW A USER TO DELETE THEMSELVES
        # ==========================================================

        if user.pk == request.user.pk:
            messages.error(
                request,
                "You cannot delete your own account."
            )
            return redirect("user_list")

        # ==========================================================
        # MANAGER SECURITY
        #
        # Managers can ONLY delete Vendors and Clients.
        # ==========================================================

        if request.user.role == User.Roles.MANAGER:
            if user.role not in [
                User.Roles.VENDOR,
                User.Roles.CLIENT,
            ]:
                messages.error(
                    request,
                    "Managers can only delete Vendors and Clients."
                )
                return redirect("user_list")

        return render(
            request,
            self.template_name,
            {
                "user_to_delete": user,
            }
        )

    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)

        # ==========================================================
        # NEVER ALLOW SELF DELETE
        # ==========================================================

        if user.pk == request.user.pk:
            messages.error(
                request,
                "You cannot delete your own account."
            )
            return redirect("user_list")

        # ==========================================================
        # MANAGER SECURITY
        # ==========================================================

        if request.user.role == User.Roles.MANAGER:
            if user.role not in [
                User.Roles.VENDOR,
                User.Roles.CLIENT,
            ]:
                messages.error(
                    request,
                    "Managers can only delete Vendors and Clients."
                )
                return redirect("user_list")

        username = user.username
        role = user.get_role_display()

        # ==========================================================
        # DELETE
        # ==========================================================

        with db_transaction.atomic():
            user.delete()

        messages.success(
            request,
            f"{role} '{username}' was permanently deleted."
        )

        return redirect("user_list")




class UserSuspendView(LoginRequiredMixin, AdminRequiredMixin, View):

    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)

        # ==========================================================
        # NEVER ALLOW SELF SUSPENSION
        # ==========================================================

        if user.pk == request.user.pk:
            messages.error(
                request,
                "You cannot suspend your own account."
            )
            return redirect("user_list")

        # ==========================================================
        # MANAGER SECURITY
        #
        # Managers can ONLY suspend/activate Vendors and Clients.
        # ==========================================================

        if request.user.role == User.Roles.MANAGER:
            if user.role not in [
                User.Roles.VENDOR,
                User.Roles.CLIENT,
            ]:
                messages.error(
                    request,
                    "Managers can only suspend or activate Vendors and Clients."
                )
                return redirect("user_list")

        # ==========================================================
        # TOGGLE ACTIVE STATUS
        # ==========================================================

        user.is_active = not user.is_active
        user.save(update_fields=["is_active"])

        if user.is_active:
            messages.success(
                request,
                f"'{user.username}' has been activated and can login again."
            )
        else:
            messages.warning(
                request,
                f"'{user.username}' has been suspended and can no longer login."
            )

        return redirect("user_list")        
    


from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.views import View

from .models import User


class StaffSuspendView(LoginRequiredMixin, View):

    def post(self, request, pk):

        # ==========================================================
        # ADMIN ONLY
        # ==========================================================
        if not request.user.is_superuser:
            messages.error(
                request,
                "Only an administrator can suspend staff members."
            )
            return redirect('staff_list')

        # ==========================================================
        # FIND USER
        # ==========================================================
        user = get_object_or_404(
            User,
            pk=pk,
            role__in=[
                User.Roles.ADMIN,
                User.Roles.MANAGER,
                User.Roles.STAFF,
            ]
        )

        # ==========================================================
        # DON'T ALLOW SELF-SUSPENSION
        # ==========================================================
        if user.pk == request.user.pk:
            messages.error(
                request,
                "You cannot suspend your own account."
            )
            return redirect('staff_list')

        # ==========================================================
        # DON'T SUSPEND ANOTHER SUPERUSER
        # ==========================================================
        if user.is_superuser:
            messages.error(
                request,
                "A super administrator cannot be suspended."
            )
            return redirect('staff_list')

        # ==========================================================
        # SUSPEND
        # ==========================================================
        user.is_active = False
        user.save(update_fields=['is_active'])

        messages.success(
            request,
            f"{user.get_full_name() or user.username} has been suspended."
        )

        return redirect('staff_list')


class StaffUnsuspendView(LoginRequiredMixin, View):

    def post(self, request, pk):

        # ==========================================================
        # ADMIN ONLY
        # ==========================================================
        if not request.user.is_superuser:
            messages.error(
                request,
                "Only an administrator can unsuspend staff members."
            )
            return redirect('staff_list')

        # ==========================================================
        # FIND USER
        # ==========================================================
        user = get_object_or_404(
            User,
            pk=pk,
            role__in=[
                User.Roles.ADMIN,
                User.Roles.MANAGER,
                User.Roles.STAFF,
            ]
        )

        # ==========================================================
        # DON'T CHANGE SUPERUSER
        # ==========================================================
        if user.is_superuser:
            messages.error(
                request,
                "A super administrator does not need to be unsuspended."
            )
            return redirect('staff_list')

        # ==========================================================
        # UNSUSPEND
        # ==========================================================
        user.is_active = True
        user.save(update_fields=['is_active'])

        messages.success(
            request,
            f"{user.get_full_name() or user.username} has been reactivated."
        )

        return redirect('staff_list')        