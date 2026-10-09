from django.urls import path

from . import views


app_name = "supermarket"


urlpatterns = [

    path(
        "manage/",
        views.SupermarketManagerDashboardView.as_view(),
        name="manager_dashboard",
    ),

    path(
        "manage/categories/",
        views.CategoryListView.as_view(),
        name="category_list",
    ),

    path(
        "manage/categories/add/",
        views.CategoryCreateView.as_view(),
        name="category_add",
    ),

    path(
        "manage/categories/<int:pk>/edit/",
        views.CategoryUpdateView.as_view(),
        name="category_edit",
    ),

    path(
        "manage/categories/<int:pk>/delete/",
        views.CategoryDeleteView.as_view(),
        name="category_delete",
    ),
    # ============================================================
# BRANDS
# ============================================================

path(
    "manage/brands/",
    views.BrandListView.as_view(),
    name="brand_list",
),

path(
    "manage/brands/add/",
    views.BrandCreateView.as_view(),
    name="brand_add",
),

path(
    "manage/brands/<int:pk>/edit/",
    views.BrandUpdateView.as_view(),
    name="brand_edit",
),

path(
    "manage/brands/<int:pk>/delete/",
    views.BrandDeleteView.as_view(),
    name="brand_delete",
),


# ============================================================
# ATTRIBUTES
# ============================================================

path(
    "manage/attributes/",
    views.AttributeListView.as_view(),
    name="attribute_list",
),

path(
    "manage/attributes/add/",
    views.AttributeCreateView.as_view(),
    name="attribute_add",
),

path(
    "manage/attributes/<int:pk>/edit/",
    views.AttributeUpdateView.as_view(),
    name="attribute_edit",
),

path(
    "manage/attributes/<int:pk>/delete/",
    views.AttributeDeleteView.as_view(),
    name="attribute_delete",
),

path(
    "manage/attributes/<int:pk>/values/add/",
    views.AttributeValueCreateView.as_view(),
    name="attribute_value_add",
),

path(
    "manage/attribute-values/<int:pk>/delete/",
    views.AttributeValueDeleteView.as_view(),
    name="attribute_value_delete",
),
# ============================================================
# PRODUCTS
# ============================================================

path(
    "manage/products/",
    views.ProductListView.as_view(),
    name="product_list",
),

path(
    "manage/products/add/",
    views.ProductCreateView.as_view(),
    name="product_add",
),

path(
    "manage/products/<int:pk>/",
    views.ProductDetailView.as_view(),
    name="product_detail",
),

path(
    "manage/products/<int:pk>/edit/",
    views.ProductUpdateView.as_view(),
    name="product_edit",
),

path(
    "manage/products/<int:pk>/delete/",
    views.ProductDeleteView.as_view(),
    name="product_delete",
),


# ============================================================
# PRODUCT VARIANTS
# ============================================================

path(
    "manage/products/<int:product_pk>/variants/add/",
    views.ProductVariantCreateView.as_view(),
    name="variant_add",
),

path(
    "manage/variants/<int:pk>/edit/",
    views.ProductVariantUpdateView.as_view(),
    name="variant_edit",
),

path(
    "manage/variants/<int:pk>/delete/",
    views.ProductVariantDeleteView.as_view(),
    name="variant_delete",
),
# ============================================================
# CATEGORY ATTRIBUTES
# ============================================================

path(
    "manage/categories/<int:category_pk>/attributes/",
    views.CategoryAttributeListView.as_view(),
    name="category_attribute_list",
),

path(
    "manage/categories/<int:category_pk>/attributes/add/",
    views.CategoryAttributeCreateView.as_view(),
    name="category_attribute_add",
),

path(
    "manage/category-attributes/<int:pk>/edit/",
    views.CategoryAttributeUpdateView.as_view(),
    name="category_attribute_edit",
),

path(
    "manage/category-attributes/<int:pk>/delete/",
    views.CategoryAttributeDeleteView.as_view(),
    name="category_attribute_delete",
),
# ============================================================
# PRODUCT GALLERY
# ============================================================

path(
    "manage/products/<int:product_pk>/gallery/upload/",
    views.ProductGalleryUploadView.as_view(),
    name="product_gallery_upload",
),

path(
    "manage/product-images/<int:pk>/edit/",
    views.ProductImageUpdateView.as_view(),
    name="product_image_edit",
),
# ============================================================
# PUBLIC SUPERMARKET
# ============================================================

path(
    "",
    views.SupermarketStoreView.as_view(),
    name="store",
),

path(
    "product/<int:pk>/",
    views.SupermarketProductDetailView.as_view(),
    name="store_product_detail",
),
# ============================================================
# CUSTOMER CART
# ============================================================

path(
    "cart/",
    views.SupermarketCartView.as_view(),
    name="cart",
),

path(
    "cart/add/<int:variant_pk>/",
    views.SupermarketCartAddView.as_view(),
    name="cart_add",
),

path(
    "cart/update/<int:variant_pk>/",
    views.SupermarketCartUpdateView.as_view(),
    name="cart_update",
),

path(
    "cart/remove/<int:variant_pk>/",
    views.SupermarketCartRemoveView.as_view(),
    name="cart_remove",
),
# ============================================================
# CHECKOUT
# ============================================================

path(
    "checkout/",
    views.SupermarketCheckoutView.as_view(),
    name="checkout",
),
# ============================================================
# MANAGER — SUPERMARKET ORDERS
# ============================================================

path(
    "manage/orders/",
    views.SupermarketOrderListView.as_view(),
    name="order_list",
),

path(
    "manage/orders/<int:pk>/",
    views.SupermarketOrderDetailView.as_view(),
    name="order_detail",
),

path(
    "manage/orders/<int:pk>/status/",
    views.SupermarketOrderStatusUpdateView.as_view(),
    name="order_status_update",
),

path(
    "manage/orders/<int:pk>/payment/",
    views.SupermarketOrderPaymentUpdateView.as_view(),
    name="order_payment_update",
),

path(
    "order/<str:order_number>/success/",
    views.SupermarketOrderSuccessView.as_view(),
    name="order_success",
),
path(
    "order/<str:order_number>/whatsapp/",
    views.SupermarketOrderWhatsAppView.as_view(),
    name="order_whatsapp",
),
path(
    "manage/product-images/<int:pk>/delete/",
    views.ProductImageDeleteView.as_view(),
    name="product_image_delete",
),
]