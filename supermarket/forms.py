from django import forms
from django.core.exceptions import ValidationError
from django.utils.text import slugify
from .services import (
    get_inherited_category_attributes,
)
from .models import (
    ProductCategory,
    Brand,
    Product,
    ProductImage,
    ProductVariant,
    ProductAttribute,
    ProductAttributeValue,
    ProductVariantAttribute,
    CategoryAttribute,
)
from .models import (
    ProductCategory,
    Brand,
    Product,
    ProductVariant,
    ProductAttribute,
    ProductAttributeValue,
    ProductVariantAttribute,
    CategoryAttribute,
)

from itertools import product as cartesian_product

from django import forms
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.text import slugify

from .services import (
    get_inherited_category_attributes,
)

from .models import (
    ProductCategory,
    Brand,
    Product,
    ProductVariant,
    ProductAttribute,
    ProductAttributeValue,
    ProductVariantAttribute,
    CategoryAttribute,
)
# ============================================================
# SHARED FORM STYLES
# ============================================================

INPUT_CLASS = """
w-full rounded-xl border border-gray-300 bg-white
px-4 py-3 text-sm text-gray-900 outline-none
transition
focus:border-emerald-500
focus:ring-4 focus:ring-emerald-100
"""

CHECKBOX_CLASS = """
h-5 w-5 rounded border-gray-300
text-emerald-600
focus:ring-emerald-500
"""


# ============================================================
# PRODUCT CATEGORY FORM
# ============================================================
# ============================================================
# VARIANT SKU HELPERS
# ============================================================


def _sku_piece(value):
    """
    Convert text into a safe SKU component.

    Example:
        "iPhone 16 Pro" -> "IPHONE-16-PRO"
        "256 GB"        -> "256-GB"
    """

    value = slugify(
        str(value or "")
    ).replace(
        "_",
        "-"
    ).upper()

    return value.strip("-")


def generate_unique_variant_sku(
    product,
    values=None,
    exclude_variant_pk=None,
):
    """
    Generate a globally unique SKU.

    Product ID is included so products with similar
    names cannot accidentally generate the same SKU.
    """

    values = values or []

    product_piece = _sku_piece(
        product.name
    )

    if not product_piece:
        product_piece = "PRODUCT"

    # Keep product portion reasonably short.
    product_piece = product_piece[:24]

    pieces = [
        product_piece,
        str(product.pk),
    ]

    for value in values:

        value_piece = _sku_piece(
            value.value
        )

        if value_piece:
            pieces.append(
                value_piece[:16]
            )

    base_sku = "-".join(
        pieces
    )

    sku_field = (
        ProductVariant._meta.get_field(
            "sku"
        )
    )

    max_length = (
        sku_field.max_length
        or 100
    )

    base_sku = base_sku[
        :max_length
    ].rstrip("-")

    candidate = base_sku

    counter = 2

    while True:

        queryset = (
            ProductVariant.objects
            .filter(
                sku__iexact=candidate
            )
        )

        if exclude_variant_pk:
            queryset = queryset.exclude(
                pk=exclude_variant_pk
            )

        if not queryset.exists():
            return candidate

        suffix = f"-{counter}"

        candidate = (
            base_sku[
                :max_length - len(suffix)
            ].rstrip("-")
            + suffix
        )

        counter += 1
class ProductCategoryForm(forms.ModelForm):

    class Meta:
        model = ProductCategory

        fields = [
            "parent",
            "name",
            "description",
            "image",
            "is_active",
            "order",
        ]

        widgets = {
            "parent": forms.Select(
                attrs={
                    "class": INPUT_CLASS,
                }
            ),

            "name": forms.TextInput(
                attrs={
                    "class": INPUT_CLASS,
                    "placeholder": (
                        "Example: Electronics"
                    ),
                }
            ),

            "description": forms.Textarea(
                attrs={
                    "class": INPUT_CLASS,
                    "rows": 4,
                    "placeholder": (
                        "Describe this category..."
                    ),
                }
            ),

            "image": forms.ClearableFileInput(
                attrs={
                    "class": INPUT_CLASS,
                    "accept": "image/*",
                }
            ),

            "order": forms.NumberInput(
                attrs={
                    "class": INPUT_CLASS,
                    "min": 0,
                }
            ),
        }

    def __init__(
        self,
        *args,
        **kwargs,
    ):
        super().__init__(
            *args,
            **kwargs,
        )

        self.fields["parent"].required = False
        self.fields["parent"].empty_label = (
            "Main category"
        )

        parent_queryset = (
            ProductCategory.objects
            .select_related("parent")
            .order_by(
                "parent__name",
                "order",
                "name",
            )
        )

        if self.instance.pk:
            excluded_ids = {
                self.instance.pk,
            }

            # Prevent selecting direct/indirect descendants
            # as a parent.
            pending_ids = [
                self.instance.pk
            ]

            while pending_ids:

                child_ids = list(
                    ProductCategory.objects
                    .filter(
                        parent_id__in=pending_ids
                    )
                    .values_list(
                        "pk",
                        flat=True,
                    )
                )

                new_ids = [
                    pk
                    for pk in child_ids
                    if pk not in excluded_ids
                ]

                if not new_ids:
                    break

                excluded_ids.update(
                    new_ids
                )

                pending_ids = new_ids

            parent_queryset = (
                parent_queryset.exclude(
                    pk__in=excluded_ids
                )
            )

        self.fields[
            "parent"
        ].queryset = parent_queryset

        self.fields[
            "is_active"
        ].widget.attrs.update({
            "class": CHECKBOX_CLASS,
        })

    def clean_name(self):

        name = (
            self.cleaned_data
            .get("name", "")
            .strip()
        )

        if not name:
            raise ValidationError(
                "Category name is required."
            )

        return name

    def clean(self):

        cleaned_data = super().clean()

        parent = cleaned_data.get(
            "parent"
        )

        name = cleaned_data.get(
            "name"
        )

        if (
            self.instance.pk
            and parent
            and parent.pk == self.instance.pk
        ):
            self.add_error(
                "parent",
                (
                    "A category cannot be "
                    "its own parent."
                ),
            )

        if name:

            duplicate = (
                ProductCategory.objects
                .filter(
                    parent=parent,
                    name__iexact=name,
                )
            )

            if self.instance.pk:
                duplicate = (
                    duplicate.exclude(
                        pk=self.instance.pk
                    )
                )

            if duplicate.exists():
                self.add_error(
                    "name",
                    (
                        "A category with this name "
                        "already exists under the "
                        "selected parent."
                    ),
                )

        return cleaned_data


# ============================================================
# BRAND FORM
# ============================================================

class BrandForm(forms.ModelForm):

    class Meta:
        model = Brand

        fields = [
            "name",
            "logo",
            "description",
            "is_active",
        ]

        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": INPUT_CLASS,
                    "placeholder": (
                        "Example: Samsung"
                    ),
                }
            ),

            "logo": forms.ClearableFileInput(
                attrs={
                    "class": INPUT_CLASS,
                    "accept": "image/*",
                }
            ),

            "description": forms.Textarea(
                attrs={
                    "class": INPUT_CLASS,
                    "rows": 4,
                    "placeholder": (
                        "Optional brand description..."
                    ),
                }
            ),
        }

    def __init__(
        self,
        *args,
        **kwargs,
    ):
        super().__init__(
            *args,
            **kwargs,
        )

        self.fields[
            "is_active"
        ].widget.attrs.update({
            "class": CHECKBOX_CLASS,
        })

    def clean_name(self):

        name = (
            self.cleaned_data
            .get("name", "")
            .strip()
        )

        if not name:
            raise ValidationError(
                "Brand name is required."
            )

        duplicate = (
            Brand.objects
            .filter(
                name__iexact=name
            )
        )

        if self.instance.pk:
            duplicate = duplicate.exclude(
                pk=self.instance.pk
            )

        if duplicate.exists():
            raise ValidationError(
                "This brand already exists."
            )

        return name


# ============================================================
# PRODUCT ATTRIBUTE FORM
# ============================================================

class ProductAttributeForm(
    forms.ModelForm
):

    class Meta:
        model = ProductAttribute

        fields = [
            "name",
            "slug",
            "is_active",
            "order",
        ]

        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": INPUT_CLASS,
                    "placeholder": (
                        "Example: Color"
                    ),
                }
            ),

            "slug": forms.TextInput(
                attrs={
                    "class": INPUT_CLASS,
                    "placeholder": (
                        "Example: color"
                    ),
                }
            ),

            "order": forms.NumberInput(
                attrs={
                    "class": INPUT_CLASS,
                    "min": 0,
                }
            ),
        }

    def __init__(
        self,
        *args,
        **kwargs,
    ):
        super().__init__(
            *args,
            **kwargs,
        )

        self.fields[
            "slug"
        ].required = False

        self.fields[
            "is_active"
        ].widget.attrs.update({
            "class": CHECKBOX_CLASS,
        })

    def clean_name(self):

        name = (
            self.cleaned_data
            .get("name", "")
            .strip()
        )

        if not name:
            raise ValidationError(
                "Attribute name is required."
            )

        duplicate = (
            ProductAttribute.objects
            .filter(
                name__iexact=name
            )
        )

        if self.instance.pk:
            duplicate = duplicate.exclude(
                pk=self.instance.pk
            )

        if duplicate.exists():
            raise ValidationError(
                (
                    "An attribute with this "
                    "name already exists."
                )
            )

        return name

    def clean_slug(self):

        slug = (
            self.cleaned_data
            .get("slug", "")
            .strip()
            .lower()
        )

        if not slug:
            name = (
                self.cleaned_data
                .get("name", "")
            )

            slug = slugify(name)

        if not slug:
            raise ValidationError(
                "A valid slug is required."
            )

        duplicate = (
            ProductAttribute.objects
            .filter(
                slug__iexact=slug
            )
        )

        if self.instance.pk:
            duplicate = duplicate.exclude(
                pk=self.instance.pk
            )

        if duplicate.exists():
            raise ValidationError(
                (
                    "This attribute slug "
                    "already exists."
                )
            )

        return slug


# ============================================================
# PRODUCT ATTRIBUTE VALUE FORM
# ============================================================

class ProductAttributeValueForm(
    forms.ModelForm
):

    class Meta:
        model = ProductAttributeValue

        fields = [
            "value",
            "order",
        ]

        widgets = {
            "value": forms.TextInput(
                attrs={
                    "class": INPUT_CLASS,
                    "placeholder": (
                        "Example: Black"
                    ),
                }
            ),

            "order": forms.NumberInput(
                attrs={
                    "class": INPUT_CLASS,
                    "min": 0,
                }
            ),
        }

    def __init__(
        self,
        *args,
        attribute=None,
        **kwargs,
    ):

        self.attribute = attribute

        super().__init__(
            *args,
            **kwargs,
        )

    def clean_value(self):

        value = (
            self.cleaned_data
            .get("value", "")
            .strip()
        )

        if not value:
            raise ValidationError(
                "Attribute value is required."
            )

        if not self.attribute:
            return value

        duplicate = (
            ProductAttributeValue.objects
            .filter(
                attribute=self.attribute,
                value__iexact=value,
            )
        )

        if self.instance.pk:
            duplicate = duplicate.exclude(
                pk=self.instance.pk
            )

        if duplicate.exists():
            raise ValidationError(
                (
                    "This value already exists "
                    "for this attribute."
                )
            )

        return value


# ============================================================
# CATEGORY ATTRIBUTE FORM
# ============================================================

class CategoryAttributeForm(
    forms.ModelForm
):

    class Meta:
        model = CategoryAttribute

        fields = [
            "attribute",
            "is_required",
            "is_variant_attribute",
            "order",
        ]

        widgets = {
            "attribute": forms.Select(
                attrs={
                    "class": INPUT_CLASS,
                }
            ),

            "order": forms.NumberInput(
                attrs={
                    "class": INPUT_CLASS,
                    "min": 0,
                }
            ),
        }

    def __init__(
        self,
        *args,
        category=None,
        **kwargs,
    ):

        self.category = category

        super().__init__(
            *args,
            **kwargs,
        )

        queryset = (
            ProductAttribute.objects
            .filter(
                is_active=True
            )
            .order_by(
                "order",
                "name",
            )
        )

        if category:

            existing = (
                CategoryAttribute.objects
                .filter(
                    category=category
                )
            )

            if self.instance.pk:
                existing = (
                    existing.exclude(
                        pk=self.instance.pk
                    )
                )

            used_ids = list(
                existing.values_list(
                    "attribute_id",
                    flat=True,
                )
            )

            queryset = queryset.exclude(
                pk__in=used_ids
            )

        self.fields[
            "attribute"
        ].queryset = queryset

        self.fields[
            "attribute"
        ].empty_label = (
            "Select attribute"
        )

        self.fields[
            "is_required"
        ].widget.attrs.update({
            "class": CHECKBOX_CLASS,
        })

        self.fields[
            "is_variant_attribute"
        ].widget.attrs.update({
            "class": CHECKBOX_CLASS,
        })

    def clean_attribute(self):

        attribute = (
            self.cleaned_data.get(
                "attribute"
            )
        )

        if not attribute:
            raise ValidationError(
                "Please select an attribute."
            )

        if self.category:

            duplicate = (
                CategoryAttribute.objects
                .filter(
                    category=self.category,
                    attribute=attribute,
                )
            )

            if self.instance.pk:
                duplicate = (
                    duplicate.exclude(
                        pk=self.instance.pk
                    )
                )

            if duplicate.exists():
                raise ValidationError(
                    (
                        "This attribute is already "
                        "assigned to this category."
                    )
                )

        return attribute


# ============================================================
# PRODUCT FORM
# ============================================================

class ProductForm(forms.ModelForm):

    class Meta:
        model = Product

        fields = [
            "category",
            "brand",
            "name",
            "description",
            "image",
            "is_active",
            "is_featured",
        ]

        widgets = {
            "category": forms.Select(
                attrs={
                    "class": INPUT_CLASS,
                }
            ),

            "brand": forms.Select(
                attrs={
                    "class": INPUT_CLASS,
                }
            ),

            "name": forms.TextInput(
                attrs={
                    "class": INPUT_CLASS,
                    "placeholder": (
                        "Example: Samsung Galaxy A56"
                    ),
                }
            ),

            "description": forms.Textarea(
                attrs={
                    "class": INPUT_CLASS,
                    "rows": 6,
                    "placeholder": (
                        "Describe the product..."
                    ),
                }
            ),

            "image": forms.ClearableFileInput(
                attrs={
                    "class": INPUT_CLASS,
                    "accept": "image/*",
                }
            ),
        }

    def __init__(
        self,
        *args,
        **kwargs,
    ):
        super().__init__(
            *args,
            **kwargs,
        )

        self.fields[
            "category"
        ].queryset = (
            ProductCategory.objects
            .filter(
                is_active=True
            )
            .select_related(
                "parent"
            )
            .order_by(
                "parent__name",
                "order",
                "name",
            )
        )

        self.fields[
            "brand"
        ].queryset = (
            Brand.objects
            .filter(
                is_active=True
            )
            .order_by(
                "name"
            )
        )

        self.fields[
            "category"
        ].required = False

        self.fields[
            "brand"
        ].required = False

        self.fields[
            "category"
        ].empty_label = (
            "Select category"
        )

        self.fields[
            "brand"
        ].empty_label = (
            "No brand"
        )

        self.fields[
            "is_active"
        ].widget.attrs.update({
            "class": CHECKBOX_CLASS,
        })

        self.fields[
            "is_featured"
        ].widget.attrs.update({
            "class": CHECKBOX_CLASS,
        })

    def clean_name(self):

        name = (
            self.cleaned_data
            .get("name", "")
            .strip()
        )

        if not name:
            raise ValidationError(
                "Product name is required."
            )

        return name


# ============================================================
# PRODUCT VARIANT FORM
# ============================================================

# ============================================================
# PRODUCT VARIANT FORM
# ============================================================
# ============================================================
# PRODUCT VARIANT FORM
# SINGLE VARIANT / EDITING
# ============================================================

# ============================================================
# PRODUCT GALLERY IMAGE FORM
# ============================================================


class ProductImageForm(forms.ModelForm):

    class Meta:
        model = ProductImage

        fields = [
            "image",
            "alt_text",
            "order",
        ]

        widgets = {
            "image": forms.ClearableFileInput(
                attrs={
                    "class": INPUT_CLASS,
                    "accept": "image/*",
                }
            ),

            "alt_text": forms.TextInput(
                attrs={
                    "class": INPUT_CLASS,
                    "placeholder": (
                        "Example: Samsung Galaxy A56 front view"
                    ),
                }
            ),

            "order": forms.NumberInput(
                attrs={
                    "class": INPUT_CLASS,
                    "min": 0,
                }
            ),
        }

    def clean_alt_text(self):

        return (
            self.cleaned_data
            .get("alt_text", "")
            .strip()
        )


# ============================================================
# MULTIPLE PRODUCT IMAGE UPLOAD FORM
# ============================================================


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleImageField(forms.ImageField):

    widget = MultipleFileInput(
        attrs={
            "class": INPUT_CLASS,
            "accept": "image/*",
        }
    )

    def clean(
        self,
        data,
        initial=None,
    ):

        single_image_clean = super().clean

        if isinstance(
            data,
            (list, tuple),
        ):
            result = []

            for image in data:
                result.append(
                    single_image_clean(
                        image,
                        initial,
                    )
                )

            return result

        return [
            single_image_clean(
                data,
                initial,
            )
        ]


class ProductGalleryUploadForm(forms.Form):

    images = MultipleImageField(
        required=True,
        label="Gallery images",
        help_text=(
            "Select one or more product images."
        ),
    )

    def clean_images(self):

        images = self.cleaned_data.get(
            "images",
            []
        )

        if not images:
            raise ValidationError(
                "Please select at least one image."
            )

        if len(images) > 20:
            raise ValidationError(
                "You can upload a maximum of "
                "20 images at a time."
            )

        return images
class ProductVariantForm(forms.ModelForm):

    class Meta:
        model = ProductVariant

        fields = [
            "sku",
            "unit",
            "price",
            "sale_price",
            "stock_quantity",
            "low_stock_threshold",
            "track_stock",
            "is_active",
        ]

        widgets = {
            "sku": forms.TextInput(
                attrs={
                    "class": INPUT_CLASS,
                    "placeholder": (
                        "Leave blank to auto-generate"
                    ),
                    "autocomplete": "off",
                }
            ),

            "unit": forms.Select(
                attrs={
                    "class": INPUT_CLASS,
                }
            ),

            "price": forms.NumberInput(
                attrs={
                    "class": INPUT_CLASS,
                    "step": "0.01",
                    "min": "0.01",
                    "placeholder": "0.00",
                }
            ),

            "sale_price": forms.NumberInput(
                attrs={
                    "class": INPUT_CLASS,
                    "step": "0.01",
                    "min": "0.01",
                    "placeholder": (
                        "Optional sale price"
                    ),
                }
            ),

            "stock_quantity": forms.NumberInput(
                attrs={
                    "class": INPUT_CLASS,
                    "min": "0",
                    "placeholder": "0",
                }
            ),

            "low_stock_threshold": forms.NumberInput(
                attrs={
                    "class": INPUT_CLASS,
                    "min": "0",
                    "placeholder": "5",
                }
            ),
        }

    def __init__(
        self,
        *args,
        product=None,
        **kwargs,
    ):

        self.product = product

        super().__init__(
            *args,
            **kwargs,
        )

        # ----------------------------------------------------
        # Resolve product automatically during editing.
        # ----------------------------------------------------

        if (
            self.product is None
            and self.instance
            and self.instance.pk
        ):
            self.product = (
                self.instance.product
            )

        # ----------------------------------------------------
        # Basic fields
        # ----------------------------------------------------

        self.fields[
            "sku"
        ].required = False

        self.fields[
            "sale_price"
        ].required = False

        self.fields[
            "track_stock"
        ].widget.attrs.update({
            "class": CHECKBOX_CLASS,
        })

        self.fields[
            "is_active"
        ].widget.attrs.update({
            "class": CHECKBOX_CLASS,
        })

        self.fields[
            "sku"
        ].help_text = (
            "Leave blank to generate automatically."
        )

        # ----------------------------------------------------
        # Dynamic attributes
        # ----------------------------------------------------

        if (
            not self.product
            or not self.product.category_id
        ):
            return

        category_attributes = (
            self.get_category_attributes()
        )

        existing_values = {}

        if (
            self.instance
            and self.instance.pk
        ):

            existing_values = {
                assignment.attribute_id:
                    assignment.value_id

                for assignment in (
                    self.instance
                    .attribute_values
                    .select_related(
                        "attribute",
                        "value",
                    )
                )
            }

        for category_attribute in (
            category_attributes
        ):

            attribute = (
                category_attribute.attribute
            )

            field_name = (
                f"attribute_{attribute.pk}"
            )

            value_queryset = (
                ProductAttributeValue.objects
                .filter(
                    attribute=attribute
                )
                .order_by(
                    "order",
                    "value",
                )
            )

            self.fields[
                field_name
            ] = forms.ModelChoiceField(
                queryset=value_queryset,
                required=(
                    category_attribute
                    .is_required
                ),
                label=attribute.name,
                empty_label=(
                    f"Select {attribute.name}"
                ),
                widget=forms.Select(
                    attrs={
                        "class": INPUT_CLASS,
                        "data-variant-attribute": (
                            "true"
                        ),
                    }
                ),
            )

            if (
                attribute.pk
                in existing_values
            ):
                self.fields[
                    field_name
                ].initial = (
                    existing_values[
                        attribute.pk
                    ]
                )

    # ========================================================
    # CATEGORY ATTRIBUTES
    # ========================================================

    def get_category_attributes(self):

        if (
            not self.product
            or not self.product.category_id
        ):
            return []

        return (
            get_inherited_category_attributes(
                self.product.category,
                variant_only=True,
            )
        )

    # ========================================================
    # SELECTED ATTRIBUTES
    # ========================================================

    def get_selected_attributes(self):

        selected = []

        for category_attribute in (
            self.get_category_attributes()
        ):

            attribute = (
                category_attribute.attribute
            )

            field_name = (
                f"attribute_{attribute.pk}"
            )

            value = (
                self.cleaned_data.get(
                    field_name
                )
            )

            if value:

                selected.append(
                    (
                        attribute,
                        value,
                    )
                )

        return selected

    def get_selected_attribute_map(self):

        return {
            attribute.pk: value.pk
            for attribute, value
            in self.get_selected_attributes()
        }

    # ========================================================
    # SKU
    # ========================================================

    def clean_sku(self):

        sku = (
            self.cleaned_data
            .get("sku", "")
            .strip()
            .upper()
        )

        if not sku:
            return ""

        duplicate = (
            ProductVariant.objects
            .filter(
                sku__iexact=sku
            )
        )

        if self.instance.pk:

            duplicate = (
                duplicate.exclude(
                    pk=self.instance.pk
                )
            )

        if duplicate.exists():

            raise ValidationError(
                "This SKU already exists."
            )

        return sku

    # ========================================================
    # DUPLICATE COMBINATION
    # ========================================================

    def validate_variant_combination(self):

        if not self.product:
            return

        selected_map = (
            self.get_selected_attribute_map()
        )

        existing_variants = (
            ProductVariant.objects
            .filter(
                product=self.product
            )
            .prefetch_related(
                "attribute_values"
            )
        )

        if self.instance.pk:

            existing_variants = (
                existing_variants.exclude(
                    pk=self.instance.pk
                )
            )

        for existing in existing_variants:

            existing_map = {
                assignment.attribute_id:
                    assignment.value_id

                for assignment in (
                    existing.attribute_values.all()
                )
            }

            if existing_map == selected_map:

                combination = ", ".join(
                    (
                        f"{attribute.name}: "
                        f"{value.value}"
                    )
                    for attribute, value
                    in self.get_selected_attributes()
                )

                raise ValidationError(
                    (
                        "This exact variant already "
                        "exists"
                        + (
                            f": {combination}."
                            if combination
                            else "."
                        )
                    )
                )

    # ========================================================
    # VALIDATION
    # ========================================================

    def clean(self):

        cleaned_data = super().clean()

        price = cleaned_data.get(
            "price"
        )

        sale_price = cleaned_data.get(
            "sale_price"
        )

        stock_quantity = (
            cleaned_data.get(
                "stock_quantity"
            )
        )

        low_stock_threshold = (
            cleaned_data.get(
                "low_stock_threshold"
            )
        )

        track_stock = (
            cleaned_data.get(
                "track_stock"
            )
        )

        # ----------------------------------------------------
        # Pricing
        # ----------------------------------------------------

        if (
            price is not None
            and price <= 0
        ):
            self.add_error(
                "price",
                (
                    "Price must be greater "
                    "than zero."
                ),
            )

        if (
            sale_price is not None
            and sale_price <= 0
        ):
            self.add_error(
                "sale_price",
                (
                    "Sale price must be greater "
                    "than zero."
                ),
            )

        if (
            price is not None
            and sale_price is not None
            and sale_price >= price
        ):
            self.add_error(
                "sale_price",
                (
                    "Sale price must be lower "
                    "than the regular price."
                ),
            )

        # ----------------------------------------------------
        # Stock
        # ----------------------------------------------------

        if (
            stock_quantity is not None
            and stock_quantity < 0
        ):
            self.add_error(
                "stock_quantity",
                (
                    "Stock quantity cannot "
                    "be negative."
                ),
            )

        if (
            low_stock_threshold is not None
            and low_stock_threshold < 0
        ):
            self.add_error(
                "low_stock_threshold",
                (
                    "Low-stock threshold cannot "
                    "be negative."
                ),
            )

        if (
            track_stock
            and stock_quantity is None
        ):
            self.add_error(
                "stock_quantity",
                (
                    "Enter stock quantity when "
                    "stock tracking is enabled."
                ),
            )

        # ----------------------------------------------------
        # Dynamic attributes
        # ----------------------------------------------------

        for category_attribute in (
            self.get_category_attributes()
        ):

            attribute = (
                category_attribute.attribute
            )

            field_name = (
                f"attribute_{attribute.pk}"
            )

            selected_value = (
                cleaned_data.get(
                    field_name
                )
            )

            if (
                category_attribute.is_required
                and not selected_value
            ):
                self.add_error(
                    field_name,
                    (
                        f"Please select "
                        f"{attribute.name}."
                    ),
                )

                continue

            if not selected_value:
                continue

            if (
                selected_value.attribute_id
                != attribute.pk
            ):
                self.add_error(
                    field_name,
                    (
                        "The selected value does "
                        "not belong to "
                        f"{attribute.name}."
                    ),
                )

        if not self.errors:

            try:

                self.validate_variant_combination()

            except ValidationError as error:

                self.add_error(
                    None,
                    error,
                )

        return cleaned_data

    # ========================================================
    # SAVE ATTRIBUTES
    # ========================================================

    def save_attributes(
        self,
        variant,
    ):

        if not variant.pk:

            raise ValueError(
                (
                    "Variant must be saved before "
                    "saving its attributes."
                )
            )

        category_attributes = (
            self.get_category_attributes()
        )

        if not category_attributes:

            ProductVariantAttribute.objects.filter(
                variant=variant
            ).delete()

            return

        allowed_attribute_ids = [
            item.attribute_id
            for item in category_attributes
        ]

        for category_attribute in (
            category_attributes
        ):

            attribute = (
                category_attribute.attribute
            )

            field_name = (
                f"attribute_{attribute.pk}"
            )

            value = (
                self.cleaned_data.get(
                    field_name
                )
            )

            if value:

                ProductVariantAttribute.objects.update_or_create(
                    variant=variant,
                    attribute=attribute,
                    defaults={
                        "value": value,
                    },
                )

            else:

                ProductVariantAttribute.objects.filter(
                    variant=variant,
                    attribute=attribute,
                ).delete()

        # Remove assignments that no longer belong
        # to this product's category configuration.
        ProductVariantAttribute.objects.filter(
            variant=variant
        ).exclude(
            attribute_id__in=(
                allowed_attribute_ids
            )
        ).delete()

    # ========================================================
    # SAVE
    # ========================================================

    def save(
        self,
        commit=True,
    ):

        variant = super().save(
            commit=False
        )

        if self.product:

            variant.product = (
                self.product
            )

        sku = (
            self.cleaned_data
            .get("sku", "")
            .strip()
            .upper()
        )

        if not sku:

            selected_values = [
                value
                for attribute, value
                in self.get_selected_attributes()
            ]

            sku = (
                generate_unique_variant_sku(
                    self.product,
                    selected_values,
                    exclude_variant_pk=(
                        self.instance.pk
                        if self.instance.pk
                        else None
                    ),
                )
            )

        variant.sku = sku

        if commit:

            variant.save()

            self.save_m2m()

            self.save_attributes(
                variant
            )

        return variant
    


# ============================================================
# BULK PRODUCT VARIANT CREATE FORM
# ============================================================


class ProductVariantBulkCreateForm(
    forms.ModelForm
):

    class Meta:
        model = ProductVariant

        fields = [
            "unit",
            "price",
            "sale_price",
            "stock_quantity",
            "low_stock_threshold",
            "track_stock",
            "is_active",
        ]

        widgets = {
            "unit": forms.Select(
                attrs={
                    "class": INPUT_CLASS,
                }
            ),

            "price": forms.NumberInput(
                attrs={
                    "class": INPUT_CLASS,
                    "step": "0.01",
                    "min": "0.01",
                    "placeholder": "0.00",
                }
            ),

            "sale_price": forms.NumberInput(
                attrs={
                    "class": INPUT_CLASS,
                    "step": "0.01",
                    "min": "0.01",
                    "placeholder": (
                        "Optional sale price"
                    ),
                }
            ),

            "stock_quantity": forms.NumberInput(
                attrs={
                    "class": INPUT_CLASS,
                    "min": "0",
                    "placeholder": "0",
                }
            ),

            "low_stock_threshold": forms.NumberInput(
                attrs={
                    "class": INPUT_CLASS,
                    "min": "0",
                    "placeholder": "5",
                }
            ),
        }

    def __init__(
        self,
        *args,
        product=None,
        **kwargs,
    ):

        self.product = product

        super().__init__(
            *args,
            **kwargs,
        )

        self.fields[
            "sale_price"
        ].required = False

        self.fields[
            "track_stock"
        ].widget.attrs.update({
            "class": CHECKBOX_CLASS,
        })

        self.fields[
            "is_active"
        ].widget.attrs.update({
            "class": CHECKBOX_CLASS,
        })

        # Keep category attributes so we don't
        # repeatedly query them.
        self.category_attributes = []

        if (
            not self.product
            or not self.product.category_id
        ):
            return

        self.category_attributes = (
            get_inherited_category_attributes(
                self.product.category,
                variant_only=True,
            )
        )

        # ----------------------------------------------------
        # MULTI-SELECT ATTRIBUTE FIELDS
        # ----------------------------------------------------

        for category_attribute in (
            self.category_attributes
        ):

            attribute = (
                category_attribute.attribute
            )

            field_name = (
                f"attribute_{attribute.pk}"
            )

            value_queryset = (
                ProductAttributeValue.objects
                .filter(
                    attribute=attribute
                )
                .order_by(
                    "order",
                    "value",
                )
            )

            self.fields[
                field_name
            ] = forms.ModelMultipleChoiceField(
                queryset=value_queryset,
                required=(
                    category_attribute
                    .is_required
                ),
                label=attribute.name,
                widget=forms.CheckboxSelectMultiple(
                    attrs={
                        "class": CHECKBOX_CLASS,
                        "data-variant-attribute": (
                            "true"
                        ),
                    }
                ),
                help_text=(
                    f"Select one or more "
                    f"{attribute.name} options."
                ),
            )

    # ========================================================
    # ATTRIBUTE HELPERS
    # ========================================================

    def get_category_attributes(self):

        return self.category_attributes

    def get_selected_attribute_groups(self):
        """
        Return:

        [
            (ColorAttribute, [Black, Blue]),
            (StorageAttribute, [128GB, 256GB]),
        ]
        """

        groups = []

        for category_attribute in (
            self.get_category_attributes()
        ):

            attribute = (
                category_attribute.attribute
            )

            field_name = (
                f"attribute_{attribute.pk}"
            )

            values = (
                self.cleaned_data.get(
                    field_name
                )
            )

            if values:

                values = list(
                    values
                )

            else:

                values = []

            if values:

                groups.append(
                    (
                        attribute,
                        values,
                    )
                )

        return groups

    # ========================================================
    # COMBINATIONS
    # ========================================================

    def get_combinations(self):
        """
        Convert:

            Color   = [Black, Blue]
            Storage = [128GB, 256GB]

        into:

            Black + 128GB
            Black + 256GB
            Blue  + 128GB
            Blue  + 256GB

        Each returned item is:

        [
            (attribute, value),
            (attribute, value),
        ]
        """

        groups = (
            self.get_selected_attribute_groups()
        )

        if not groups:
            return [
                []
            ]

        combination_options = []

        for attribute, values in groups:

            combination_options.append(
                [
                    (
                        attribute,
                        value,
                    )
                    for value in values
                ]
            )

        combinations = []

        for combination in cartesian_product(
            *combination_options
        ):

            combinations.append(
                list(combination)
            )

        return combinations

    # ========================================================
    # EXISTING VARIANT MAPS
    # ========================================================

    def get_existing_combination_maps(self):

        if not self.product:
            return []

        existing_variants = (
            ProductVariant.objects
            .filter(
                product=self.product
            )
            .prefetch_related(
                "attribute_values"
            )
        )

        existing_maps = []

        for variant in existing_variants:

            attribute_map = {
                assignment.attribute_id:
                    assignment.value_id

                for assignment in (
                    variant.attribute_values.all()
                )
            }

            existing_maps.append(
                attribute_map
            )

        return existing_maps

    # ========================================================
    # VALIDATION
    # ========================================================

    def clean(self):

        cleaned_data = super().clean()

        price = cleaned_data.get(
            "price"
        )

        sale_price = cleaned_data.get(
            "sale_price"
        )

        stock_quantity = (
            cleaned_data.get(
                "stock_quantity"
            )
        )

        low_stock_threshold = (
            cleaned_data.get(
                "low_stock_threshold"
            )
        )

        track_stock = (
            cleaned_data.get(
                "track_stock"
            )
        )

        # ----------------------------------------------------
        # PRICE
        # ----------------------------------------------------

        if (
            price is not None
            and price <= 0
        ):

            self.add_error(
                "price",
                (
                    "Price must be greater "
                    "than zero."
                ),
            )

        if (
            sale_price is not None
            and sale_price <= 0
        ):

            self.add_error(
                "sale_price",
                (
                    "Sale price must be greater "
                    "than zero."
                ),
            )

        if (
            price is not None
            and sale_price is not None
            and sale_price >= price
        ):

            self.add_error(
                "sale_price",
                (
                    "Sale price must be lower "
                    "than the regular price."
                ),
            )

        # ----------------------------------------------------
        # STOCK
        # ----------------------------------------------------

        if (
            stock_quantity is not None
            and stock_quantity < 0
        ):

            self.add_error(
                "stock_quantity",
                (
                    "Stock quantity cannot "
                    "be negative."
                ),
            )

        if (
            low_stock_threshold is not None
            and low_stock_threshold < 0
        ):

            self.add_error(
                "low_stock_threshold",
                (
                    "Low-stock threshold cannot "
                    "be negative."
                ),
            )

        if (
            track_stock
            and stock_quantity is None
        ):

            self.add_error(
                "stock_quantity",
                (
                    "Enter stock quantity when "
                    "stock tracking is enabled."
                ),
            )

        # ----------------------------------------------------
        # ATTRIBUTE VALIDATION
        # ----------------------------------------------------

        for category_attribute in (
            self.get_category_attributes()
        ):

            attribute = (
                category_attribute.attribute
            )

            field_name = (
                f"attribute_{attribute.pk}"
            )

            selected_values = (
                cleaned_data.get(
                    field_name
                )
            )

            if (
                category_attribute.is_required
                and not selected_values
            ):

                self.add_error(
                    field_name,
                    (
                        f"Select at least one "
                        f"{attribute.name}."
                    ),
                )

                continue

            if not selected_values:
                continue

            for selected_value in (
                selected_values
            ):

                if (
                    selected_value.attribute_id
                    != attribute.pk
                ):

                    self.add_error(
                        field_name,
                        (
                            "One of the selected "
                            "values does not belong "
                            f"to {attribute.name}."
                        ),
                    )

                    break

        # ----------------------------------------------------
        # LIMIT ACCIDENTAL HUGE CREATION
        # ----------------------------------------------------

        if not self.errors:

            combinations = (
                self.get_combinations()
            )

            if len(combinations) > 200:

                raise ValidationError(
                    (
                        "This selection would create "
                        f"{len(combinations)} variants. "
                        "Please reduce the number of "
                        "selected options to 200 or fewer."
                    )
                )

        return cleaned_data

    # ========================================================
    # CREATE VARIANTS
    # ========================================================

    @transaction.atomic
    def save(self):
        """
        Create every missing Cartesian-product variant.

        Returns:
            created_variants, skipped_count
        """

        if not self.product:

            raise ValueError(
                (
                    "A product is required before "
                    "creating variants."
                )
            )

        combinations = (
            self.get_combinations()
        )

        existing_maps = (
            self.get_existing_combination_maps()
        )

        created_variants = []

        skipped_count = 0

        # Shared values entered once in the form.
        unit = (
            self.cleaned_data.get(
                "unit"
            )
        )

        price = (
            self.cleaned_data.get(
                "price"
            )
        )

        sale_price = (
            self.cleaned_data.get(
                "sale_price"
            )
        )

        stock_quantity = (
            self.cleaned_data.get(
                "stock_quantity"
            )
        )

        low_stock_threshold = (
            self.cleaned_data.get(
                "low_stock_threshold"
            )
        )

        track_stock = (
            self.cleaned_data.get(
                "track_stock"
            )
        )

        is_active = (
            self.cleaned_data.get(
                "is_active"
            )
        )

        for combination in combinations:

            combination_map = {
                attribute.pk:
                    value.pk

                for attribute, value
                in combination
            }

            # --------------------------------------------
            # SKIP DUPLICATE COMBINATIONS
            # --------------------------------------------

            if combination_map in existing_maps:

                skipped_count += 1

                continue

            selected_values = [
                value
                for attribute, value
                in combination
            ]

            sku = (
                generate_unique_variant_sku(
                    self.product,
                    selected_values,
                )
            )

            # --------------------------------------------
            # CREATE VARIANT
            # --------------------------------------------

            variant = (
                ProductVariant.objects.create(
                    product=self.product,
                    sku=sku,
                    unit=unit,
                    price=price,
                    sale_price=sale_price,
                    stock_quantity=stock_quantity,
                    low_stock_threshold=(
                        low_stock_threshold
                    ),
                    track_stock=track_stock,
                    is_active=is_active,
                )
            )

            # --------------------------------------------
            # CREATE ATTRIBUTE ASSIGNMENTS
            # --------------------------------------------

            assignments = []

            for attribute, value in combination:

                assignments.append(
                    ProductVariantAttribute(
                        variant=variant,
                        attribute=attribute,
                        value=value,
                    )
                )

            if assignments:

                ProductVariantAttribute.objects.bulk_create(
                    assignments
                )

            created_variants.append(
                variant
            )

            # Prevent duplicates within this same
            # bulk operation as well.
            existing_maps.append(
                combination_map
            )

        return (
            created_variants,
            skipped_count,
        )    
    

# ============================================================
# SUPERMARKET CHECKOUT FORM
# ============================================================

class SupermarketCheckoutForm(forms.Form):

    customer_name = forms.CharField(
        max_length=150,
        label="Full Name",
        widget=forms.TextInput(
            attrs={
                "class": INPUT_CLASS,
                "placeholder": "Enter your full name",
                "autocomplete": "name",
            }
        ),
    )

    phone = forms.CharField(
        max_length=30,
        label="Phone Number",
        widget=forms.TextInput(
            attrs={
                "class": INPUT_CLASS,
                "placeholder": "e.g. 08012345678",
                "autocomplete": "tel",
            }
        ),
    )

    email = forms.EmailField(
        required=False,
        label="Email Address",
        widget=forms.EmailInput(
            attrs={
                "class": INPUT_CLASS,
                "placeholder": "Optional",
                "autocomplete": "email",
            }
        ),
    )

    address = forms.CharField(
        label="Delivery Address",
        widget=forms.Textarea(
            attrs={
                "class": INPUT_CLASS,
                "placeholder": (
                    "Enter the complete delivery address"
                ),
                "rows": 4,
                "autocomplete": "street-address",
            }
        ),
    )

    note = forms.CharField(
        required=False,
        label="Order Note",
        widget=forms.Textarea(
            attrs={
                "class": INPUT_CLASS,
                "placeholder": (
                    "Optional delivery instructions"
                ),
                "rows": 3,
            }
        ),
    )

    def clean_customer_name(self):

        value = (
            self.cleaned_data
            .get("customer_name", "")
            .strip()
        )

        if len(value) < 2:
            raise forms.ValidationError(
                "Please enter your full name."
            )

        return value

    def clean_phone(self):

        value = (
            self.cleaned_data
            .get("phone", "")
            .strip()
        )

        cleaned = (
            value
            .replace(" ", "")
            .replace("-", "")
            .replace("(", "")
            .replace(")", "")
        )

        if cleaned.startswith("+"):
            digits = cleaned[1:]
        else:
            digits = cleaned

        if not digits.isdigit():
            raise forms.ValidationError(
                "Enter a valid phone number."
            )

        if len(digits) < 7:
            raise forms.ValidationError(
                "Enter a valid phone number."
            )

        return value

    def clean_address(self):

        value = (
            self.cleaned_data
            .get("address", "")
            .strip()
        )

        if len(value) < 5:
            raise forms.ValidationError(
                "Please enter a complete delivery address."
            )

        return value

    def clean_note(self):

        return (
            self.cleaned_data
            .get("note", "")
            .strip()
        )    