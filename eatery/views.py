from django.shortcuts import render

# Create your views here.
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.shortcuts import render

from account.views import EateryManagerRequiredMixin
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View

from account.views import EateryManagerRequiredMixin

from .forms import (
    FoodCategoryForm,
    FoodItemForm,CustomerCheckoutForm
)
import json
from decimal import Decimal

from .models import (
    FoodCategory,
    FoodItem,
    Order,
)
from .models import (
    FoodCategory,
    FoodItem,
    Order,
)


# ============================================================
# PUBLIC EATERY MENU
# ============================================================
def menu(request):
    categories = (
        FoodCategory.objects
        .filter(
            is_active=True,
            foods__is_available=True,
        )
        .prefetch_related("foods")
        .distinct()
        .order_by("order", "name")
    )

    featured_foods = (
        FoodItem.objects
        .filter(
            is_available=True,
            is_featured=True,
        )
        .select_related("category")
        .order_by("name")
    )

    context = {
        "categories": categories,
        "featured_foods": featured_foods,
    }

    return render(
        request,
        "eatery/menu.html",
        context,
    )







# ============================================================
# EATERY MANAGER DASHBOARD
# ============================================================
class EateryManagerDashboardView(
    LoginRequiredMixin,
    EateryManagerRequiredMixin,
    View,
):
    """
    Main dashboard for Dikubs Eatery.

    Accessible only to:
        - Super Admin
        - Eatery Manager
    """

    template_name = "eatery/manager/dashboard.html"

    def get(self, request):
        orders = Order.objects.all()

        pending_orders = orders.filter(
            status="pending"
        )

        confirmed_orders = orders.filter(
            status="confirmed"
        )

        preparing_orders = orders.filter(
            status="preparing"
        )

        ready_orders = orders.filter(
            status="ready"
        )

        context = {
            # --------------------------------------------------
            # ORDER COUNTS
            # --------------------------------------------------
            "total_orders": orders.count(),

            "pending_orders_count": (
                pending_orders.count()
            ),

            "confirmed_orders_count": (
                confirmed_orders.count()
            ),

            "preparing_orders_count": (
                preparing_orders.count()
            ),

            "ready_orders_count": (
                ready_orders.count()
            ),

            # --------------------------------------------------
            # MENU COUNTS
            # --------------------------------------------------
            "total_foods": FoodItem.objects.count(),

            "available_foods": FoodItem.objects.filter(
                is_available=True
            ).count(),

            "total_categories": (
                FoodCategory.objects.count()
            ),

            # --------------------------------------------------
            # RECENT ORDERS
            # --------------------------------------------------
            "recent_orders": (
                orders
                .prefetch_related("items")
                .order_by("-created_at")[:10]
            ),
        }

        return render(
            request,
            self.template_name,
            context,
        )
    



# ============================================================
# CATEGORY LIST
# ============================================================
class FoodCategoryListView(
    LoginRequiredMixin,
    EateryManagerRequiredMixin,
    View,
):
    template_name = "eatery/manager/category_list.html"

    def get(self, request):
        categories = (
            FoodCategory.objects
            .prefetch_related("foods")
            .order_by("order", "name")
        )

        return render(
            request,
            self.template_name,
            {
                "categories": categories,
            },
        )


# ============================================================
# CREATE CATEGORY
# ============================================================
class FoodCategoryCreateView(
    LoginRequiredMixin,
    EateryManagerRequiredMixin,
    View,
):
    template_name = "eatery/manager/category_form.html"

    def get(self, request):
        form = FoodCategoryForm()

        return render(
            request,
            self.template_name,
            {
                "form": form,
                "page_title": "Add Food Category",
            },
        )

    def post(self, request):
        form = FoodCategoryForm(request.POST)

        if form.is_valid():
            category = form.save()

            messages.success(
                request,
                f'"{category.name}" category created successfully.',
            )

            return redirect(
                "eatery:category_list"
            )

        return render(
            request,
            self.template_name,
            {
                "form": form,
                "page_title": "Add Food Category",
            },
        )


# ============================================================
# UPDATE CATEGORY
# ============================================================
class FoodCategoryUpdateView(
    LoginRequiredMixin,
    EateryManagerRequiredMixin,
    View,
):
    template_name = "eatery/manager/category_form.html"

    def get(self, request, pk):
        category = get_object_or_404(
            FoodCategory,
            pk=pk,
        )

        form = FoodCategoryForm(
            instance=category
        )

        return render(
            request,
            self.template_name,
            {
                "form": form,
                "category": category,
                "page_title": "Edit Food Category",
            },
        )

    def post(self, request, pk):
        category = get_object_or_404(
            FoodCategory,
            pk=pk,
        )

        form = FoodCategoryForm(
            request.POST,
            instance=category,
        )

        if form.is_valid():
            category = form.save()

            messages.success(
                request,
                f'"{category.name}" updated successfully.',
            )

            return redirect(
                "eatery:category_list"
            )

        return render(
            request,
            self.template_name,
            {
                "form": form,
                "category": category,
                "page_title": "Edit Food Category",
            },
        )


# ============================================================
# DELETE CATEGORY
# ============================================================
class FoodCategoryDeleteView(
    LoginRequiredMixin,
    EateryManagerRequiredMixin,
    View,
):

    def post(self, request, pk):
        category = get_object_or_404(
            FoodCategory,
            pk=pk,
        )

        category_name = category.name

        # FoodItem uses SET_NULL, so deleting a category
        # will NOT delete its foods.
        category.delete()

        messages.success(
            request,
            f'"{category_name}" category deleted.',
        )

        return redirect(
            "eatery:category_list"
        )


# ============================================================
# FOOD LIST
# ============================================================
class FoodItemListView(
    LoginRequiredMixin,
    EateryManagerRequiredMixin,
    View,
):
    template_name = "eatery/manager/food_list.html"

    def get(self, request):
        foods = (
            FoodItem.objects
            .select_related("category")
            .order_by("category__order", "category__name", "name")
        )

        category_id = request.GET.get(
            "category",
            ""
        )

        availability = request.GET.get(
            "availability",
            ""
        )

        search = request.GET.get(
            "search",
            ""
        ).strip()

        if category_id:
            foods = foods.filter(
                category_id=category_id
            )

        if availability == "available":
            foods = foods.filter(
                is_available=True
            )

        elif availability == "unavailable":
            foods = foods.filter(
                is_available=False
            )

        if search:
            foods = foods.filter(
                name__icontains=search
            )

        context = {
            "foods": foods,

            "categories": (
                FoodCategory.objects
                .order_by("order", "name")
            ),

            "selected_category": category_id,

            "selected_availability": availability,

            "search_query": search,

            "total_foods": foods.count(),
        }

        return render(
            request,
            self.template_name,
            context,
        )


# ============================================================
# CREATE FOOD
# ============================================================
class FoodItemCreateView(
    LoginRequiredMixin,
    EateryManagerRequiredMixin,
    View,
):
    template_name = "eatery/manager/food_form.html"

    def get(self, request):
        form = FoodItemForm()

        return render(
            request,
            self.template_name,
            {
                "form": form,
                "page_title": "Add Food Item",
            },
        )

    def post(self, request):
        form = FoodItemForm(
            request.POST,
            request.FILES,
        )

        if form.is_valid():
            food = form.save()

            messages.success(
                request,
                f'"{food.name}" added to the menu.',
            )

            return redirect(
                "eatery:food_list"
            )

        return render(
            request,
            self.template_name,
            {
                "form": form,
                "page_title": "Add Food Item",
            },
        )


# ============================================================
# UPDATE FOOD
# ============================================================
class FoodItemUpdateView(
    LoginRequiredMixin,
    EateryManagerRequiredMixin,
    View,
):
    template_name = "eatery/manager/food_form.html"

    def get(self, request, pk):
        food = get_object_or_404(
            FoodItem,
            pk=pk,
        )

        form = FoodItemForm(
            instance=food
        )

        return render(
            request,
            self.template_name,
            {
                "form": form,
                "food": food,
                "page_title": "Edit Food Item",
            },
        )

    def post(self, request, pk):
        food = get_object_or_404(
            FoodItem,
            pk=pk,
        )

        form = FoodItemForm(
            request.POST,
            request.FILES,
            instance=food,
        )

        if form.is_valid():
            food = form.save()

            messages.success(
                request,
                f'"{food.name}" updated successfully.',
            )

            return redirect(
                "eatery:food_list"
            )

        return render(
            request,
            self.template_name,
            {
                "form": form,
                "food": food,
                "page_title": "Edit Food Item",
            },
        )

from django.db import transaction
# ============================================================
# TOGGLE FOOD AVAILABILITY
# ============================================================
class FoodItemAvailabilityView(
    LoginRequiredMixin,
    EateryManagerRequiredMixin,
    View,
):

    def post(self, request, pk):
        food = get_object_or_404(
            FoodItem,
            pk=pk,
        )

        food.is_available = not food.is_available

        food.save(
            update_fields=[
                "is_available",
                "updated_at",
            ]
        )

        if food.is_available:
            messages.success(
                request,
                f'"{food.name}" is now available.',
            )
        else:
            messages.warning(
                request,
                f'"{food.name}" is now unavailable.',
            )

        return redirect(
            "eatery:food_list"
        )


# ============================================================
# DELETE FOOD
# ============================================================
class FoodItemDeleteView(
    LoginRequiredMixin,
    EateryManagerRequiredMixin,
    View,
):

    def post(self, request, pk):
        food = get_object_or_404(
            FoodItem,
            pk=pk,
        )

        food_name = food.name

        food.delete()

        messages.success(
            request,
            f'"{food_name}" removed from the menu.',
        )

        return redirect(
            "eatery:food_list"
        )    
    


def cart(request):
    return render(
        request,
        "eatery/cart.html",
    )

from .models import OrderItem
class CheckoutView(View):
    template_name = "eatery/checkout.html"

    # WhatsApp number:
    # country code + number, no +, spaces, or dashes.
    WHATSAPP_NUMBER = "2337062548298"

    def get(self, request):
        form = CustomerCheckoutForm()

        return render(
            request,
            self.template_name,
            {
                "form": form,
            },
        )

    def post(self, request):
        form = CustomerCheckoutForm(request.POST)

        raw_cart = request.POST.get(
            "cart_data",
            ""
        )

        # =====================================================
        # 1. VALIDATE CUSTOMER DETAILS
        # =====================================================
        if not form.is_valid():
            return render(
                request,
                self.template_name,
                {
                    "form": form,
                    "cart_data": raw_cart,
                },
            )

        # =====================================================
        # 2. PARSE BROWSER CART
        # =====================================================
        try:
            cart_data = json.loads(raw_cart)

        except (json.JSONDecodeError, TypeError):
            messages.error(
                request,
                "Your cart could not be read. Please try again.",
            )

            return redirect(
                "eatery:cart"
            )

        if not isinstance(cart_data, list) or not cart_data:
            messages.error(
                request,
                "Your cart is empty.",
            )

            return redirect(
                "eatery:cart"
            )

        # =====================================================
        # 3. BUILD CLEAN QUANTITY MAP
        #
        # IMPORTANT:
        # We only trust the browser for:
        # - food ID
        # - quantity
        #
        # We DO NOT trust:
        # - food name
        # - price
        # - subtotal
        # - total
        #
        # Those come from the database.
        # =====================================================
        quantities = {}

        for item in cart_data:

            if not isinstance(item, dict):
                continue

            try:
                food_id = int(
                    item.get("id")
                )

                quantity = int(
                    item.get("quantity", 1)
                )

            except (TypeError, ValueError):
                continue

            if food_id <= 0:
                continue

            if quantity <= 0:
                continue

            # Prevent unreasonable quantities.
            quantity = min(
                quantity,
                100,
            )

            quantities[food_id] = (
                quantities.get(food_id, 0)
                + quantity
            )

        if not quantities:
            messages.error(
                request,
                "Your cart does not contain any valid items.",
            )

            return redirect(
                "eatery:cart"
            )

        # =====================================================
        # 4. GET CURRENT FOOD RECORDS FROM DATABASE
        # =====================================================
        foods = (
            FoodItem.objects
            .filter(
                id__in=quantities.keys(),
                is_available=True,
            )
            .select_related("category")
        )

        foods_by_id = {
            food.id: food
            for food in foods
        }

        # =====================================================
        # 5. CHECK FOR REMOVED / UNAVAILABLE ITEMS
        # =====================================================
        missing_ids = (
            set(quantities.keys())
            - set(foods_by_id.keys())
        )

        if missing_ids:
            messages.error(
                request,
                (
                    "One or more items in your cart are no longer "
                    "available. Please review your cart."
                ),
            )

            return redirect(
                "eatery:cart"
            )

        # =====================================================
        # 6. CALCULATE TOTAL FROM DATABASE PRICES
        # =====================================================
        calculated_items = []

        total_amount = Decimal(
            "0.00"
        )

        for food_id, quantity in quantities.items():

            food = foods_by_id[
                food_id
            ]

            unit_price = food.price

            subtotal = (
                unit_price
                * quantity
            )

            total_amount += subtotal

            calculated_items.append(
                {
                    "food": food,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "subtotal": subtotal,
                }
            )

        if total_amount <= 0:
            messages.error(
                request,
                "Unable to calculate your order total.",
            )

            return redirect(
                "eatery:cart"
            )

        # =====================================================
        # 7. CREATE ORDER ATOMICALLY
        # =====================================================
        try:

            with transaction.atomic():

                order = Order.objects.create(
                    customer_name=(
                        form.cleaned_data[
                            "customer_name"
                        ]
                    ),

                    phone=(
                        form.cleaned_data[
                            "phone"
                        ]
                    ),

                    email=(
                        form.cleaned_data.get(
                            "email"
                        )
                        or None
                    ),

                    address=(
                        form.cleaned_data[
                            "address"
                        ]
                    ),

                    note=(
                        form.cleaned_data.get(
                            "note"
                        )
                        or ""
                    ),

                    total_amount=total_amount,

                    status="pending",
                )

                order_items = []

                for item in calculated_items:

                    food = item[
                        "food"
                    ]

                    order_items.append(
                        OrderItem(
                            order=order,
                            food=food,

                            # Snapshot the name at the
                            # time of ordering.
                            food_name=food.name,

                            unit_price=item[
                                "unit_price"
                            ],

                            quantity=item[
                                "quantity"
                            ],

                            subtotal=item[
                                "subtotal"
                            ],
                        )
                    )

                OrderItem.objects.bulk_create(
                    order_items
                )

        except Exception as e:

            # During development this helps us
            # identify database/order problems.
            print(
                "\n"
                "================ ORDER ERROR ================"
            )

            print(
                type(e).__name__
            )

            print(
                str(e)
            )

            print(
                "============================================="
                "\n"
            )

            messages.error(
                request,
                (
                    "We could not place your order. "
                    "Please try again."
                ),
            )

            return render(
                request,
                self.template_name,
                {
                    "form": form,
                    "cart_data": raw_cart,
                },
            )

        # =====================================================
        # 8. BUILD WHATSAPP ORDER MESSAGE
        #
        # IMPORTANT:
        # This happens AFTER the transaction succeeds.
        # =====================================================

        whatsapp_lines = [
            "🍽️ *NEW FOOD ORDER*",
            "",
            f"*Order:* #{order.order_number}",
            "",
            "👤 *CUSTOMER DETAILS*",
            f"Name: {order.customer_name}",
            f"Phone: {order.phone}",
        ]

        # Add email only if supplied.
        if order.email:
            whatsapp_lines.append(
                f"Email: {order.email}"
            )

        whatsapp_lines.extend(
            [
                "",
                "🛒 *ORDER ITEMS*",
                "",
            ]
        )

        # Use calculated_items because these contain
        # the trusted database prices used for the order.
        for item in calculated_items:

            food = item[
                "food"
            ]

            quantity = item[
                "quantity"
            ]

            unit_price = item[
                "unit_price"
            ]

            subtotal = item[
                "subtotal"
            ]

            whatsapp_lines.append(
                (
                    f"• {quantity} × {food.name}\n"
                    f"  GHS {unit_price:.2f} each "
                    f"= GHS {subtotal:.2f}"
                )
            )

        # =====================================================
        # TOTAL
        # =====================================================
        whatsapp_lines.extend(
            [
                "",
                "━━━━━━━━━━━━━━━━━━",
                f"💰 *TOTAL: GHS {total_amount:.2f}*",
                "━━━━━━━━━━━━━━━━━━",
                "",
                "📍 *DELIVERY ADDRESS*",
                str(order.address),
            ]
        )

        # =====================================================
        # CUSTOMER NOTE
        # =====================================================
        if order.note:

            whatsapp_lines.extend(
                [
                    "",
                    "📝 *CUSTOMER NOTE*",
                    str(order.note),
                ]
            )

        whatsapp_lines.extend(
            [
                "",
                (
                    "Please confirm availability "
                    "and delivery details."
                ),
            ]
        )

        whatsapp_message = "\n".join(
            whatsapp_lines
        )

        # =====================================================
        # 9. CREATE WHATSAPP URL
        # =====================================================
        whatsapp_url = (
            f"https://wa.me/"
            f"{self.WHATSAPP_NUMBER}"
            f"?text={quote(whatsapp_message)}"
        )

        # =====================================================
        # 10. SAVE SUCCESS INFORMATION IN SESSION
        # =====================================================

        request.session[
            "latest_eatery_order"
        ] = order.pk

        request.session[
            "eatery_whatsapp_url"
        ] = whatsapp_url

        # =====================================================
        # 11. REDIRECT TO SUCCESS PAGE
        # =====================================================
        return redirect(
            "eatery:order_success",
            order_number=order.order_number,
        )
    
def order_success(
    request,
    order_number,
):
    # -----------------------------------------------------
    # GET ORDER
    # -----------------------------------------------------
    order = get_object_or_404(
        Order.objects.prefetch_related(
            "items"
        ),
        order_number=order_number,
    )

    # -----------------------------------------------------
    # SECURITY CHECK
    #
    # Prevent somebody from simply changing the order
    # number in the URL and viewing another customer's
    # order / delivery details.
    # -----------------------------------------------------
    latest_order_id = request.session.get(
        "latest_eatery_order"
    )

    if latest_order_id != order.pk:
        return redirect(
            "eatery:menu"
        )

    # -----------------------------------------------------
    # GET WHATSAPP URL
    #
    # CheckoutView created this only after the order
    # was successfully saved.
    #
    # We use .pop() so refreshing the success page
    # will NOT repeatedly auto-open WhatsApp.
    # -----------------------------------------------------
    whatsapp_url = request.session.pop(
        "eatery_whatsapp_url",
        None,
    )

    # -----------------------------------------------------
    # PAGE CONTEXT
    # -----------------------------------------------------
    context = {
        "order": order,
        "whatsapp_url": whatsapp_url,
    }

    # -----------------------------------------------------
    # RENDER SUCCESS PAGE
    # -----------------------------------------------------
    return render(
        request,
        "eatery/order_success.html",
        context,
    )







# ============================================================
# ORDER LIST
# ============================================================
class EateryOrderListView(
    LoginRequiredMixin,
    EateryManagerRequiredMixin,
    View,
):
    template_name = "eatery/manager/order_list.html"

    def get(self, request):
        orders = (
            Order.objects
            .prefetch_related("items")
            .order_by("-created_at")
        )

        status = request.GET.get(
            "status",
            ""
        ).strip()

        search = request.GET.get(
            "search",
            ""
        ).strip()

        valid_statuses = {
            choice[0]
            for choice in Order.STATUS_CHOICES
        }

        if status in valid_statuses:
            orders = orders.filter(
                status=status
            )

        if search:
            from django.db.models import Q

            orders = orders.filter(
                Q(
                    order_number__icontains=search
                )
                |
                Q(
                    customer_name__icontains=search
                )
                |
                Q(
                    phone__icontains=search
                )
            )

        context = {
            "orders": orders,

            "selected_status": status,

            "search_query": search,

            "total_orders_count": (
                Order.objects.count()
            ),

            "pending_count": (
                Order.objects.filter(
                    status="pending"
                ).count()
            ),

            "confirmed_count": (
                Order.objects.filter(
                    status="confirmed"
                ).count()
            ),

            "preparing_count": (
                Order.objects.filter(
                    status="preparing"
                ).count()
            ),

            "ready_count": (
                Order.objects.filter(
                    status="ready"
                ).count()
            ),

            "delivery_count": (
                Order.objects.filter(
                    status="out_for_delivery"
                ).count()
            ),
        }

        return render(
            request,
            self.template_name,
            context,
        )


# ============================================================
# ORDER DETAIL
# ============================================================
class EateryOrderDetailView(
    LoginRequiredMixin,
    EateryManagerRequiredMixin,
    View,
):
    template_name = "eatery/manager/order_detail.html"

    def get(self, request, pk):
        order = get_object_or_404(
            Order.objects.prefetch_related(
                "items"
            ),
            pk=pk,
        )

        context = {
            "order": order,
            "status_choices": (
                Order.STATUS_CHOICES
            ),
        }

        return render(
            request,
            self.template_name,
            context,
        )


# ============================================================
# UPDATE ORDER STATUS
# ============================================================
class EateryOrderStatusUpdateView(
    LoginRequiredMixin,
    EateryManagerRequiredMixin,
    View,
):

    def post(self, request, pk):
        order = get_object_or_404(
            Order,
            pk=pk,
        )

        new_status = request.POST.get(
            "status",
            ""
        ).strip()

        valid_statuses = {
            choice[0]
            for choice in Order.STATUS_CHOICES
        }

        if new_status not in valid_statuses:
            messages.error(
                request,
                "Invalid order status.",
            )

            return redirect(
                "eatery:order_detail",
                pk=order.pk,
            )

        old_status = order.status

        order.status = new_status

        order.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        if old_status != new_status:
            messages.success(
                request,
                (
                    f"{order.order_number} updated to "
                    f"{order.get_status_display()}."
                ),
            )

        return redirect(
            "eatery:order_detail",
            pk=order.pk,
        )
    
from urllib.parse import quote


def order_whatsapp(request, order_number):
    """
    Opens WhatsApp with a trusted order summary.

    The order must belong to the current customer's
    session so another visitor cannot access customer
    information by guessing an order number.
    """

    order = get_object_or_404(
        Order.objects.prefetch_related("items"),
        order_number=order_number,
    )

    latest_order_id = request.session.get(
        "latest_eatery_order"
    )

    if latest_order_id != order.pk:
        return redirect("eatery:menu")

    # -----------------------------------------------------
    # DIKUBS WHATSAPP NUMBER
    # -----------------------------------------------------
    whatsapp_number = "+2347062548298"

    # -----------------------------------------------------
    # BUILD TRUSTED MESSAGE FROM DATABASE
    # -----------------------------------------------------
    lines = [
        "Hello Dikubs Eatery 👋",
        "",
        "I just placed an order.",
        "",
        f"Order: {order.order_number}",
        "",
        "ORDER ITEMS",
    ]

    for item in order.items.all():

        subtotal = f"{item.subtotal:,.2f}"

        lines.append(
            f"{item.quantity} × {item.food_name} — ₦{subtotal}"
        )

    lines.extend([
        "",
        f"Total: ₦{order.total_amount:,.2f}",
        "",
        "CUSTOMER DETAILS",
        f"Name: {order.customer_name}",
        f"Phone: {order.phone}",
        f"Delivery Address: {order.address}",
    ])

    if order.note:
        lines.extend([
            "",
            f"Instructions: {order.note}",
        ])

    lines.extend([
        "",
        "Please confirm my order. Thank you.",
    ])

    message = "\n".join(lines)

    whatsapp_url = (
        f"https://wa.me/{whatsapp_number}"
        f"?text={quote(message)}"
    )

    # We know the customer followed the WhatsApp
    # handoff link.
    if not order.whatsapp_opened:
        order.whatsapp_opened = True

        order.save(
            update_fields=[
                "whatsapp_opened",
                "updated_at",
            ]
        )

    return redirect(whatsapp_url)
import re


def normalize_whatsapp_number(phone):
    """
    Convert a customer phone number into the format
    required by wa.me.

    Examples:
        +2348012345678 -> 2348012345678
        2348012345678  -> 2348012345678
        08012345678    -> 2348012345678
    """

    phone = re.sub(r"\D", "", phone or "")

    if phone.startswith("0"):
        phone = "234" + phone[1:]

    return phone


class EateryCustomerWhatsAppView(
    LoginRequiredMixin,
    EateryManagerRequiredMixin,
    View,
):

    def get(self, request, pk):
        # =====================================================
        # GET ORDER
        # =====================================================
        order = get_object_or_404(
            Order,
            pk=pk,
        )

        # =====================================================
        # NORMALIZE CUSTOMER WHATSAPP NUMBER
        # =====================================================
        phone = normalize_whatsapp_number(
            order.phone
        )

        if not phone:
            messages.error(
                request,
                (
                    "This customer does not have "
                    "a valid WhatsApp phone number."
                ),
            )

            return redirect(
                "eatery:order_detail",
                pk=order.pk,
            )

        # =====================================================
        # DETERMINE MESSAGE TYPE
        #
        # If ?type= is supplied, use it.
        #
        # Otherwise automatically use the CURRENT
        # order status.
        # =====================================================
        requested_type = (
            request.GET.get("type")
            or ""
        ).strip().lower()

        current_status = (
            str(order.status)
            .strip()
            .lower()
        )

        message_type = (
            requested_type
            or current_status
            or "general"
        )

        # =====================================================
        # COMMON ORDER INFORMATION
        # =====================================================
        customer_name = (
            order.customer_name
            or "Customer"
        )

        order_number = (
            order.order_number
        )

        total = (
            f"₦{order.total_amount:,.2f}"
        )

        # =====================================================
        # WHATSAPP MESSAGES BY ORDER STATUS
        # =====================================================
        messages_by_type = {

            # -------------------------------------------------
            # PENDING
            # -------------------------------------------------
            "pending": (
                f"Hello {customer_name}, 👋\n\n"

                f"Thank you for placing an order with "
                f"*Dikubs Eatery*.\n\n"

                f"🧾 *Order:* {order_number}\n"
                f"💰 *Total:* {total}\n\n"

                f"We have received your order and it is "
                f"currently awaiting confirmation.\n\n"

                f"We'll update you shortly once your order "
                f"has been confirmed.\n\n"

                f"Thank you for choosing *Dikubs Eatery*. 🍽️"
            ),

            # -------------------------------------------------
            # CONFIRMED
            # -------------------------------------------------
            "confirmed": (
                f"Hello {customer_name}, 👋\n\n"

                f"Great news! Your order with "
                f"*Dikubs Eatery* has been confirmed. ✅\n\n"

                f"🧾 *Order:* {order_number}\n"
                f"💰 *Total:* {total}\n\n"

                f"We're getting everything ready and will "
                f"keep you updated as your order progresses.\n\n"

                f"Thank you for ordering from "
                f"*Dikubs Eatery*. 🍽️"
            ),

            # -------------------------------------------------
            # PREPARING
            # -------------------------------------------------
            "preparing": (
                f"Hello {customer_name}, 👋\n\n"

                f"👨‍🍳 *Your order is now being prepared!*\n\n"

                f"🧾 *Order:* {order_number}\n"
                f"💰 *Total:* {total}\n\n"

                f"Our kitchen is currently preparing your "
                f"order.\n\n"

                f"We'll let you know as soon as it is "
                f"ready for the next step.\n\n"

                f"Thank you for your patience. 🍽️\n"
                f"*Dikubs Eatery*"
            ),

            # -------------------------------------------------
            # READY
            # -------------------------------------------------
            "ready": (
                f"Hello {customer_name}, 👋\n\n"

                f"Good news! 🎉\n\n"

                f"Your *Dikubs Eatery* order is ready.\n\n"

                f"🧾 *Order:* {order_number}\n"
                f"💰 *Total:* {total}\n\n"

                f"Your meal has been prepared and is ready "
                f"for the next delivery step.\n\n"

                f"We'll keep you updated once it is "
                f"on the way. 🛵\n\n"

                f"*Dikubs Eatery*"
            ),

            # -------------------------------------------------
            # DELIVERY / OUT FOR DELIVERY
            # -------------------------------------------------
            "delivery": (
                f"Hello {customer_name}, 👋\n\n"

                f"🛵 *Your order is on the way!*\n\n"

                f"Your *Dikubs Eatery* order has been "
                f"dispatched for delivery.\n\n"

                f"🧾 *Order:* {order_number}\n"
                f"💰 *Total:* {total}\n\n"

                f"📍 *Delivery Address:*\n"
                f"{order.address}\n\n"

                f"Please keep your phone nearby in case "
                f"our delivery person needs to contact you.\n\n"

                f"Thank you for choosing "
                f"*Dikubs Eatery*. 🍽️"
            ),

            # -------------------------------------------------
            # ALTERNATIVE STATUS NAME
            # Some systems use "out_for_delivery".
            # -------------------------------------------------
            "out_for_delivery": (
                f"Hello {customer_name}, 👋\n\n"

                f"🛵 *Your order is on the way!*\n\n"

                f"Your *Dikubs Eatery* order has been "
                f"dispatched for delivery.\n\n"

                f"🧾 *Order:* {order_number}\n"
                f"💰 *Total:* {total}\n\n"

                f"📍 *Delivery Address:*\n"
                f"{order.address}\n\n"

                f"Please keep your phone nearby in case "
                f"our delivery person needs to contact you.\n\n"

                f"Thank you for choosing "
                f"*Dikubs Eatery*. 🍽️"
            ),

            # -------------------------------------------------
            # DELIVERED
            # -------------------------------------------------
            "delivered": (
                f"Hello {customer_name}, 👋\n\n"

                f"✅ *Order Delivered*\n\n"

                f"Your *Dikubs Eatery* order has been "
                f"marked as successfully delivered.\n\n"

                f"🧾 *Order:* {order_number}\n"
                f"💰 *Total:* {total}\n\n"

                f"We hope you enjoyed your meal! 😋\n\n"

                f"Thank you for choosing *Dikubs Eatery*. "
                f"We look forward to serving you again. ❤️"
            ),

            # -------------------------------------------------
            # CANCELLED
            # -------------------------------------------------
            "cancelled": (
                f"Hello {customer_name},\n\n"

                f"We're contacting you regarding your "
                f"*Dikubs Eatery* order.\n\n"

                f"🧾 *Order:* {order_number}\n"
                f"💰 *Total:* {total}\n\n"

                f"❌ Your order has been marked as "
                f"cancelled.\n\n"

                f"If you believe this was done in error or "
                f"you need assistance, please reply to this "
                f"message and we'll be happy to help.\n\n"

                f"*Dikubs Eatery*"
            ),

            # -------------------------------------------------
            # GENERAL
            # -------------------------------------------------
            "general": (
                f"Hello {customer_name}, 👋\n\n"

                f"We're contacting you regarding your "
                f"*Dikubs Eatery* order.\n\n"

                f"🧾 *Order:* {order_number}\n"
                f"💰 *Total:* {total}\n\n"

                f"Current order status: "
                f"*{current_status.replace('_', ' ').title()}*\n\n"

                f"If you have any questions regarding your "
                f"order, please reply to this message.\n\n"

                f"Thank you for choosing "
                f"*Dikubs Eatery*. 🍽️"
            ),
        }

        # =====================================================
        # SELECT MESSAGE
        # =====================================================
        message = messages_by_type.get(
            message_type,
            messages_by_type["general"],
        )

        # =====================================================
        # CREATE WHATSAPP URL
        # =====================================================
        whatsapp_url = (
            f"https://wa.me/{phone}"
            f"?text={quote(message)}"
        )

        # =====================================================
        # OPEN WHATSAPP
        # =====================================================
        return redirect(
            whatsapp_url
        )