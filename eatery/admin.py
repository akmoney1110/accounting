from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import FoodCategory, FoodItem, Order, OrderItem


@admin.register(FoodCategory)
class FoodCategoryAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "is_active",
        "order",
    )

    list_editable = (
        "is_active",
        "order",
    )

    search_fields = ("name",)


@admin.register(FoodItem)
class FoodItemAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "category",
        "price",
        "is_available",
        "is_featured",
    )

    list_filter = (
        "category",
        "is_available",
        "is_featured",
    )

    search_fields = (
        "name",
        "description",
    )

    list_editable = (
        "price",
        "is_available",
        "is_featured",
    )


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = (
        "food_name",
        "unit_price",
        "quantity",
        "subtotal",
    )

    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "order_number",
        "customer_name",
        "phone",
        "total_amount",
        "status",
        "created_at",
    )

    list_filter = (
        "status",
        "created_at",
    )

    search_fields = (
        "order_number",
        "customer_name",
        "phone",
        "address",
    )

    readonly_fields = (
        "order_number",
        "total_amount",
        "created_at",
        "updated_at",
    )

    list_editable = ("status",)

    inlines = [OrderItemInline]