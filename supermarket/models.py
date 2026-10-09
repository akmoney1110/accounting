from django.db import models

# Create your models here.
from django.db import models
from django.utils import timezone
import uuid


# ============================================================
# CATEGORY
# ============================================================

class ProductCategory(models.Model):
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subcategories",
    )
    name = models.CharField(
        max_length=120,
        unique=True,
    )

    description = models.TextField(
        blank=True,
    )

    image = models.ImageField(
        upload_to="supermarket/categories/",
        blank=True,
        null=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    order = models.PositiveIntegerField(
        default=0,
    )

    class Meta:
        ordering = [
        "order",
        "name",
    ]

        verbose_name_plural = (
        "Product Categories"
    )

        constraints = [
            models.UniqueConstraint(
            fields=[
                "parent",
                "name",
            ],
            name="unique_supermarket_category_parent_name",
        )
    ]

    def __str__(self):
        return self.name


# ============================================================
# BRAND
# ============================================================

class Brand(models.Model):
    name = models.CharField(
        max_length=120,
        unique=True,
    )

    logo = models.ImageField(
        upload_to="supermarket/brands/",
        blank=True,
        null=True,
    )

    description = models.TextField(
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    def __str__(self):
        return self.name


# ============================================================
# PRODUCT
# ============================================================

class Product(models.Model):
    category = models.ForeignKey(
        ProductCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
    )

    brand = models.ForeignKey(
        Brand,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
    )

    name = models.CharField(
        max_length=200,
    )

    description = models.TextField(
        blank=True,
    )

    image = models.ImageField(
        upload_to="supermarket/products/",
        blank=True,
        null=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    is_featured = models.BooleanField(
        default=False,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def available_variants(self):
        return self.variants.filter(
            is_active=True,
            stock_quantity__gt=0,
        )

    @property
    def starting_price(self):
        variant = (
            self.variants
            .filter(is_active=True)
            .order_by("price")
            .first()
        )

        if variant:
            return variant.current_price

        return None


# ============================================================
# ADDITIONAL PRODUCT IMAGES
# ============================================================

class ProductImage(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="images",
    )

    image = models.ImageField(
        upload_to="supermarket/products/gallery/",
    )

    alt_text = models.CharField(
        max_length=200,
        blank=True,
    )

    order = models.PositiveIntegerField(
        default=0,
    )

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.product.name} image"


# ============================================================
# PRODUCT VARIANT
# ============================================================

class ProductVariant(models.Model):

    UNIT_CHOICES = [
        ("piece", "Piece"),
        ("pack", "Pack"),
        ("box", "Box"),
        ("bag", "Bag"),
        ("bottle", "Bottle"),
        ("carton", "Carton"),
        ("kg", "Kilogram"),
        ("g", "Gram"),
        ("l", "Litre"),
        ("ml", "Millilitre"),
        ("pair", "Pair"),
        ("set", "Set"),
        ("roll", "Roll"),
        ("dozen", "Dozen"),
        ("other", "Other"),
    ]

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="variants",
    )

    sku = models.CharField(
        max_length=100,
        unique=True,
    )

    # --------------------------------------------------------
    # VARIANT ATTRIBUTES
    # --------------------------------------------------------

    size = models.CharField(
        max_length=100,
        blank=True,
        help_text="Example: Small, Medium, XL, 32, 43",
    )

    color = models.CharField(
        max_length=100,
        blank=True,
        help_text="Example: Black, White, Red",
    )

    weight = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
    )

    weight_unit = models.CharField(
        max_length=20,
        blank=True,
        help_text="Example: kg, g",
    )

    volume = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
    )

    volume_unit = models.CharField(
        max_length=20,
        blank=True,
        help_text="Example: L, ml",
    )

    unit = models.CharField(
        max_length=30,
        choices=UNIT_CHOICES,
        default="piece",
    )

    # --------------------------------------------------------
    # PRICING
    # --------------------------------------------------------

    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    sale_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True,
    )

    # --------------------------------------------------------
    # INVENTORY
    # --------------------------------------------------------

    stock_quantity = models.PositiveIntegerField(
        default=0,
    )

    low_stock_threshold = models.PositiveIntegerField(
        default=5,
    )

    track_stock = models.BooleanField(
        default=True,
    )

    # --------------------------------------------------------
    # STATUS
    # --------------------------------------------------------

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "product__name",
            "price",
        ]

    def __str__(self):

        description = self.variant_description

        if description:
                return (
                f"{self.product.name} - "
                f"{description}"
            )

        return (
            f"{self.product.name} - "
            f"{self.sku}"
        )


    @property
    def variant_description(self):
        

        assignments = (
            self.attribute_values
            .select_related(
                "attribute",
                "value",
            )
            .order_by(
                "attribute__order",
                "attribute__name",
            )
        )

        values = [
            assignment.value.value
            for assignment in assignments
        ]

        return " / ".join(values)


    @property
    def variant_full_description(self):
  
        assignments = (
            self.attribute_values
            .select_related(
                "attribute",
                "value",
            )
            .order_by(
                "attribute__order",
                "attribute__name",
            )
        )

        values = [
            (
                f"{assignment.attribute.name}: "
                f"{assignment.value.value}"
            )
            for assignment in assignments
        ]

        return " / ".join(values)[:255]

    @property
    def current_price(self):
        if (
            self.sale_price is not None
            and self.sale_price > 0
            and self.sale_price < self.price
        ):
            return self.sale_price

        return self.price

    @property
    def in_stock(self):
        if not self.is_active:
            return False

        if not self.track_stock:
            return True

        return self.stock_quantity > 0

    @property
    def is_low_stock(self):
        if not self.track_stock:
            return False

        return (
            self.stock_quantity
            <= self.low_stock_threshold
        )


# ============================================================
# ORDER
# ============================================================

class SupermarketOrder(models.Model):

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("confirmed", "Confirmed"),
        ("processing", "Processing"),
        ("ready", "Ready"),
        ("out_for_delivery", "Out for Delivery"),
        ("delivered", "Delivered"),
        ("cancelled", "Cancelled"),
    ]

    PAYMENT_STATUS_CHOICES = [
        ("unpaid", "Unpaid"),
        ("pending", "Pending Verification"),
        ("paid", "Paid"),
        ("failed", "Failed"),
        ("refunded", "Refunded"),
    ]

    order_number = models.CharField(
        max_length=35,
        unique=True,
        editable=False,
    )

    customer_name = models.CharField(
        max_length=150,
    )

    phone = models.CharField(
        max_length=30,
    )

    email = models.EmailField(
        blank=True,
        null=True,
    )

    address = models.TextField()

    note = models.TextField(
        blank=True,
    )

    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    delivery_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="pending",
    )

    payment_status = models.CharField(
        max_length=30,
        choices=PAYMENT_STATUS_CHOICES,
        default="unpaid",
    )

    whatsapp_opened = models.BooleanField(
        default=False,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):

        description = self.variant_description

        if description:
            return (
            f"{self.quantity} × "
            f"{self.product_name} - "
            f"{description}"
        )

        return (
        f"{self.quantity} × "
        f"{self.product_name}"
    )

    def save(self, *args, **kwargs):
        if not self.order_number:
            date = timezone.now().strftime(
                "%Y%m%d"
            )

            short_id = (
                uuid.uuid4()
                .hex[:6]
                .upper()
            )

            self.order_number = (
                f"SUP-{date}-{short_id}"
            )

        super().save(*args, **kwargs)


# ============================================================
# ORDER ITEM
# ============================================================

class SupermarketOrderItem(models.Model):
    order = models.ForeignKey(
        SupermarketOrder,
        on_delete=models.CASCADE,
        related_name="items",
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    stock_deducted = models.BooleanField(
    default=False,
    help_text=(
        "Whether tracked inventory was deducted "
        "when this order item was created."
    ),
)
    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    # --------------------------------------------------------
    # SNAPSHOT
    #
    # These values remain unchanged even if the manager later
    # changes the product or variant.
    # --------------------------------------------------------

    product_name = models.CharField(
        max_length=200,
    )

    sku = models.CharField(
        max_length=100,
        blank=True,
    )

    size = models.CharField(
        max_length=100,
        blank=True,
    )

    color = models.CharField(
        max_length=100,
        blank=True,
    )

    variant_description = models.CharField(
        max_length=255,
        blank=True,
    )

    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    quantity = models.PositiveIntegerField(
        default=1,
    )

    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    def save(self, *args, **kwargs):
        self.subtotal = (
            self.unit_price *
            self.quantity
        )

        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.quantity} × "
            f"{self.product_name}"
        )
    


# ============================================================
# FLEXIBLE PRODUCT ATTRIBUTES
# ============================================================

class ProductAttribute(models.Model):
    """
    Defines an attribute that products/variants can use.

    Examples:
        Color
        Size
        Storage
        RAM
        Screen Size
        Voltage
        Fragrance
        Material
        Pack Size
    """

    name = models.CharField(
        max_length=100,
        unique=True,
    )

    slug = models.SlugField(
        max_length=120,
        unique=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    order = models.PositiveIntegerField(
        default=0,
    )

    class Meta:
        ordering = [
            "order",
            "name",
        ]

    def __str__(self):
        return self.name


# ============================================================
# ATTRIBUTE VALUES
# ============================================================

class ProductAttributeValue(models.Model):
    attribute = models.ForeignKey(
        ProductAttribute,
        on_delete=models.CASCADE,
        related_name="values",
    )

    value = models.CharField(
        max_length=150,
    )

    order = models.PositiveIntegerField(
        default=0,
    )

    class Meta:
        ordering = [
            "order",
            "value",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "attribute",
                    "value",
                ],
                name="unique_product_attribute_value",
            )
        ]

    def __str__(self):
        return (
            f"{self.attribute.name}: "
            f"{self.value}"
        )


# ============================================================
# CATEGORY ATTRIBUTES
# ============================================================

class CategoryAttribute(models.Model):
    category = models.ForeignKey(
        ProductCategory,
        on_delete=models.CASCADE,
        related_name="category_attributes",
    )

    attribute = models.ForeignKey(
        ProductAttribute,
        on_delete=models.CASCADE,
        related_name="categories",
    )

    is_required = models.BooleanField(
        default=False,
    )

    is_variant_attribute = models.BooleanField(
        default=True,
        help_text=(
            "Enable if this attribute creates "
            "different purchasable variants."
        ),
    )

    order = models.PositiveIntegerField(
        default=0,
    )

    class Meta:
        ordering = [
            "order",
            "attribute__name",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "category",
                    "attribute",
                ],
                name="unique_category_attribute",
            )
        ]

    def __str__(self):
        return (
            f"{self.category.name} - "
            f"{self.attribute.name}"
        )

# ============================================================
# VARIANT ATTRIBUTE VALUES
# ============================================================

class ProductVariantAttribute(models.Model):
    """
    Connects a variant to its attribute values.

    Example:

        iPhone 17 Variant
            Color   -> Black
            Storage -> 256GB

        T-Shirt Variant
            Color -> Blue
            Size  -> XL
    """

    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
        related_name="attribute_values",
    )

    attribute = models.ForeignKey(
        ProductAttribute,
        on_delete=models.CASCADE,
        related_name="variant_values",
    )

    value = models.ForeignKey(
        ProductAttributeValue,
        on_delete=models.CASCADE,
        related_name="variant_assignments",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "variant",
                    "attribute",
                ],
                name="unique_variant_attribute",
            )
        ]

    def __str__(self):
        return (
            f"{self.variant} - "
            f"{self.attribute.name}: "
            f"{self.value.value}"
        )

    def clean(self):
        from django.core.exceptions import ValidationError

        if (
            self.value_id
            and self.attribute_id
            and self.value.attribute_id
            != self.attribute_id
        ):
            raise ValidationError(
                {
                    "value": (
                        "The selected value does not "
                        "belong to this attribute."
                    )
                }
            )    