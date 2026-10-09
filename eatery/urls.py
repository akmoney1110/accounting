from django.urls import path

from . import views
from .views import (
    PaystackCallbackView,
    PaymentPendingView,
    RetryPaymentView,
    paystack_webhook,
)


app_name = "eatery"


urlpatterns = [

    # ==========================================================
    # PUBLIC CUSTOMER MENU
    # ==========================================================
    path(
        "",
        views.menu,
        name="menu",
    ),

    # ==========================================================
    # EATERY MANAGER DASHBOARD
    # ==========================================================
    path(
        "manage/",
        views.EateryManagerDashboardView.as_view(),
        name="manager_dashboard",
    ),

    # ==========================================================
    # CATEGORIES
    # ==========================================================
    path(
        "manage/categories/",
        views.FoodCategoryListView.as_view(),
        name="category_list",
    ),

    path(
        "manage/categories/add/",
        views.FoodCategoryCreateView.as_view(),
        name="category_create",
    ),

    path(
        "manage/categories/<int:pk>/edit/",
        views.FoodCategoryUpdateView.as_view(),
        name="category_update",
    ),

    path(
        "manage/categories/<int:pk>/delete/",
        views.FoodCategoryDeleteView.as_view(),
        name="category_delete",
    ),

    # ==========================================================
    # FOOD ITEMS
    # ==========================================================
    path(
        "manage/menu/",
        views.FoodItemListView.as_view(),
        name="food_list",
    ),

    path(
        "manage/menu/add/",
        views.FoodItemCreateView.as_view(),
        name="food_create",
    ),

    path(
        "manage/menu/<int:pk>/edit/",
        views.FoodItemUpdateView.as_view(),
        name="food_update",
    ),

    path(
        "manage/menu/<int:pk>/availability/",
        views.FoodItemAvailabilityView.as_view(),
        name="food_availability",
    ),

    path(
        "manage/menu/<int:pk>/delete/",
        views.FoodItemDeleteView.as_view(),
        name="food_delete",
    ),

    path(
        "payment/paystack/callback/",
        PaystackCallbackView.as_view(),
        name="paystack_callback",
    ),
    path(
        "payment/pending/<str:order_number>/",
        PaymentPendingView.as_view(),
        name="payment_pending",
    ),
    path(
        "payment/retry/<str:order_number>/",
        RetryPaymentView.as_view(),
        name="retry_payment",
    ),
    path(
        "payment/paystack/webhook/",
        paystack_webhook,
        name="paystack_webhook",
    ),







    path(
    "cart/",
    views.cart,
    name="cart",
),

    path(
    "checkout/",
    views.CheckoutView.as_view(),
    name="checkout",
),

    path(
    "order/<str:order_number>/success/",
    views.order_success,
    name="order_success",
),
    # ==========================================================
    # ORDER MANAGEMENT
    # ==========================================================
    path(
    "manage/orders/",
    views.EateryOrderListView.as_view(),
    name="order_list",
),
    path(
    "order/<str:order_number>/whatsapp/",
    views.order_whatsapp,
    name="order_whatsapp",
),
    path(
    "manage/orders/<int:pk>/whatsapp/",
    views.EateryCustomerWhatsAppView.as_view(),
    name="customer_whatsapp",
),
    path(
    "manage/orders/<int:pk>/",
    views.EateryOrderDetailView.as_view(),
    name="order_detail",
),

        path(
    "manage/orders/<int:pk>/status/",
    views.EateryOrderStatusUpdateView.as_view(),
    name="order_status_update",
),
]