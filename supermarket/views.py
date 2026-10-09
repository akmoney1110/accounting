from django.shortcuts import render
from .services import (
    get_category_chain,
    get_inherited_category_attributes,
)
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import F, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from .models import (
    ProductVariant,
    SupermarketOrder,
)
from urllib.parse import quote
from decimal import Decimal

from django.contrib import messages
from django.db import transaction
from django.db.models import F
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.views import View
from .cart import Cart

from .forms import SupermarketCheckoutForm

from .models import (
    ProductVariant,
    SupermarketOrder,
    SupermarketOrderItem,
)
# Create your views here.
from django.contrib import messages
from .models import (
    ProductCategory,
    Brand,
    Product,
    ProductImage,
    ProductVariant,
    ProductAttribute,
    ProductAttributeValue,
)

from .forms import (
    ProductImageForm,
    ProductGalleryUploadForm,
)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from .models import (
    ProductCategory,
    Brand,
    Product,
    ProductVariant,
    ProductAttribute,
    ProductAttributeValue,
)
from .forms import (
    ProductCategoryForm,
    BrandForm,
    ProductAttributeForm,
    ProductAttributeValueForm,
    ProductForm,
    ProductVariantForm,
)
from django.db.models import Q
from account.views import SupermarketManagerRequiredMixin

from .forms import ProductCategoryForm
from .models import ProductCategory


class SupermarketManagerDashboardView(
    LoginRequiredMixin,
    SupermarketManagerRequiredMixin,
    View,
):
    def get(self, request):
        context = {
            "category_count": (
                ProductCategory.objects.count()
            ),
        }

        return render(
            request,
            "supermarket/manager/dashboard.html",
            context,
        )


class CategoryListView(
    LoginRequiredMixin,
    SupermarketManagerRequiredMixin,
    View,
):
    def get(self, request):

        categories = (
            ProductCategory.objects
            .select_related("parent")
            .prefetch_related(
                "subcategories"
            )
            .order_by(
                "parent__name",
                "order",
                "name",
            )
        )

        context = {
            "categories": categories,
        }

        return render(
            request,
            (
                "supermarket/manager/"
                "category_list.html"
            ),
            context,
        )


class CategoryCreateView(
    LoginRequiredMixin,
    SupermarketManagerRequiredMixin,
    View,
):
    def get(self, request):

        form = ProductCategoryForm()

        parent_id = request.GET.get(
            "parent"
        )

        if parent_id:
            parent = (
                ProductCategory.objects
                .filter(pk=parent_id)
                .first()
            )

            if parent:
                form.fields[
                    "parent"
                ].initial = parent

        return render(
            request,
            (
                "supermarket/manager/"
                "category_form.html"
            ),
            {
                "form": form,
                "title": "Add Category",
            },
        )

    def post(self, request):

        form = ProductCategoryForm(
            request.POST,
            request.FILES,
        )

        if form.is_valid():

            category = form.save()

            messages.success(
                request,
                (
                    f'"{category.name}" '
                    f"was created successfully."
                ),
            )

            return redirect(
                "supermarket:category_list"
            )

        return render(
            request,
            (
                "supermarket/manager/"
                "category_form.html"
            ),
            {
                "form": form,
                "title": "Add Category",
            },
        )


class CategoryUpdateView(
    LoginRequiredMixin,
    SupermarketManagerRequiredMixin,
    View,
):
    def get(self, request, pk):

        category = get_object_or_404(
            ProductCategory,
            pk=pk,
        )

        form = ProductCategoryForm(
            instance=category
        )

        return render(
            request,
            (
                "supermarket/manager/"
                "category_form.html"
            ),
            {
                "form": form,
                "category": category,
                "title": "Edit Category",
            },
        )

    def post(self, request, pk):

        category = get_object_or_404(
            ProductCategory,
            pk=pk,
        )

        form = ProductCategoryForm(
            request.POST,
            request.FILES,
            instance=category,
        )

        if form.is_valid():

            category = form.save()

            messages.success(
                request,
                (
                    f'"{category.name}" '
                    f"was updated successfully."
                ),
            )

            return redirect(
                "supermarket:category_list"
            )

        return render(
            request,
            (
                "supermarket/manager/"
                "category_form.html"
            ),
            {
                "form": form,
                "category": category,
                "title": "Edit Category",
            },
        )


class CategoryDeleteView(
    LoginRequiredMixin,
    SupermarketManagerRequiredMixin,
    View,
):
    def post(self, request, pk):

        category = get_object_or_404(
            ProductCategory,
            pk=pk,
        )

        name = category.name

        category.delete()

        messages.success(
            request,
            f'"{name}" was deleted.',
        )

        return redirect(
            "supermarket:category_list"
        )
    

from .forms import (
    ProductCategoryForm,
    BrandForm,
    ProductAttributeForm,
    ProductAttributeValueForm,
)

from .models import (
    ProductCategory,
    Brand,
    ProductAttribute,
    ProductAttributeValue,
)



# ============================================================
# BRANDS
# ============================================================

class BrandListView(
    LoginRequiredMixin,
    SupermarketManagerRequiredMixin,
    View,
):
    def get(self, request):

        brands = (
            Brand.objects
            .order_by("name")
        )

        return render(
            request,
            "supermarket/manager/brand_list.html",
            {
                "brands": brands,
            },
        )


class BrandCreateView(
    LoginRequiredMixin,
    SupermarketManagerRequiredMixin,
    View,
):
    def get(self, request):

        form = BrandForm()

        return render(
            request,
            "supermarket/manager/brand_form.html",
            {
                "form": form,
                "title": "Add Brand",
            },
        )

    def post(self, request):

        form = BrandForm(
            request.POST,
            request.FILES,
        )

        if form.is_valid():

            brand = form.save()

            messages.success(
                request,
                f'"{brand.name}" was created.',
            )

            return redirect(
                "supermarket:brand_list"
            )

        return render(
            request,
            "supermarket/manager/brand_form.html",
            {
                "form": form,
                "title": "Add Brand",
            },
        )


class BrandUpdateView(
    LoginRequiredMixin,
    SupermarketManagerRequiredMixin,
    View,
):
    def get(self, request, pk):

        brand = get_object_or_404(
            Brand,
            pk=pk,
        )

        form = BrandForm(
            instance=brand
        )

        return render(
            request,
            "supermarket/manager/brand_form.html",
            {
                "form": form,
                "brand": brand,
                "title": "Edit Brand",
            },
        )

    def post(self, request, pk):

        brand = get_object_or_404(
            Brand,
            pk=pk,
        )

        form = BrandForm(
            request.POST,
            request.FILES,
            instance=brand,
        )

        if form.is_valid():

            brand = form.save()

            messages.success(
                request,
                f'"{brand.name}" was updated.',
            )

            return redirect(
                "supermarket:brand_list"
            )

        return render(
            request,
            "supermarket/manager/brand_form.html",
            {
                "form": form,
                "brand": brand,
                "title": "Edit Brand",
            },
        )


class BrandDeleteView(
    LoginRequiredMixin,
    SupermarketManagerRequiredMixin,
    View,
):
    def post(self, request, pk):

        brand = get_object_or_404(
            Brand,
            pk=pk,
        )

        name = brand.name

        brand.delete()

        messages.success(
            request,
            f'"{name}" was deleted.',
        )

        return redirect(
            "supermarket:brand_list"
        )
    


# ============================================================
# PRODUCT ATTRIBUTES
# ============================================================

class AttributeListView(
    LoginRequiredMixin,
    SupermarketManagerRequiredMixin,
    View,
):
    def get(self, request):

        attributes = (
            ProductAttribute.objects
            .prefetch_related("values")
            .order_by("order", "name")
        )

        return render(
            request,
            (
                "supermarket/manager/"
                "attribute_list.html"
            ),
            {
                "attributes": attributes,
            },
        )


class AttributeCreateView(
    LoginRequiredMixin,
    SupermarketManagerRequiredMixin,
    View,
):
    def get(self, request):

        form = ProductAttributeForm()

        return render(
            request,
            (
                "supermarket/manager/"
                "attribute_form.html"
            ),
            {
                "form": form,
                "title": "Add Attribute",
            },
        )

    def post(self, request):

        form = ProductAttributeForm(
            request.POST
        )

        if form.is_valid():

            attribute = form.save()

            messages.success(
                request,
                (
                    f'"{attribute.name}" '
                    f"was created."
                ),
            )

            return redirect(
                "supermarket:attribute_list"
            )

        return render(
            request,
            (
                "supermarket/manager/"
                "attribute_form.html"
            ),
            {
                "form": form,
                "title": "Add Attribute",
            },
        )


class AttributeUpdateView(
    LoginRequiredMixin,
    SupermarketManagerRequiredMixin,
    View,
):
    def get(self, request, pk):

        attribute = get_object_or_404(
            ProductAttribute,
            pk=pk,
        )

        form = ProductAttributeForm(
            instance=attribute
        )

        return render(
            request,
            (
                "supermarket/manager/"
                "attribute_form.html"
            ),
            {
                "form": form,
                "attribute": attribute,
                "title": "Edit Attribute",
            },
        )

    def post(self, request, pk):

        attribute = get_object_or_404(
            ProductAttribute,
            pk=pk,
        )

        form = ProductAttributeForm(
            request.POST,
            instance=attribute,
        )

        if form.is_valid():

            attribute = form.save()

            messages.success(
                request,
                (
                    f'"{attribute.name}" '
                    f"was updated."
                ),
            )

            return redirect(
                "supermarket:attribute_list"
            )

        return render(
            request,
            (
                "supermarket/manager/"
                "attribute_form.html"
            ),
            {
                "form": form,
                "attribute": attribute,
                "title": "Edit Attribute",
            },
        )


class AttributeDeleteView(
    LoginRequiredMixin,
    SupermarketManagerRequiredMixin,
    View,
):
    def post(self, request, pk):

        attribute = get_object_or_404(
            ProductAttribute,
            pk=pk,
        )

        name = attribute.name

        attribute.delete()

        messages.success(
            request,
            f'"{name}" was deleted.',
        )

        return redirect(
            "supermarket:attribute_list"
        )    
    



# ============================================================
# ATTRIBUTE VALUES
# ============================================================

class AttributeValueCreateView(
    LoginRequiredMixin,
    SupermarketManagerRequiredMixin,
    View,
):
    def get(self, request, pk):

        attribute = get_object_or_404(
            ProductAttribute,
            pk=pk,
        )

        form = ProductAttributeValueForm(
            attribute=attribute,
        )

        return render(
            request,
            (
                "supermarket/manager/"
                "attribute_value_form.html"
            ),
            {
                "form": form,
                "attribute": attribute,
                "title": (
                    f"Add {attribute.name} Value"
                ),
            },
        )

    def post(self, request, pk):

        attribute = get_object_or_404(
            ProductAttribute,
            pk=pk,
        )

        form = ProductAttributeValueForm(
            request.POST,
            attribute=attribute,
        )

        if form.is_valid():

            value = form.save(
                commit=False
            )

            value.attribute = attribute

            value.save()

            messages.success(
                request,
                (
                    f'"{value.value}" added '
                    f'to "{attribute.name}".'
                ),
            )

            return redirect(
                "supermarket:attribute_list"
            )

        return render(
            request,
            (
                "supermarket/manager/"
                "attribute_value_form.html"
            ),
            {
                "form": form,
                "attribute": attribute,
                "title": (
                    f"Add {attribute.name} Value"
                ),
            },
        )


class AttributeValueDeleteView(
    LoginRequiredMixin,
    SupermarketManagerRequiredMixin,
    View,
):
    def post(
        self,
        request,
        pk,
    ):

        value = get_object_or_404(
            ProductAttributeValue,
            pk=pk,
        )

        value_name = value.value

        value.delete()

        messages.success(
            request,
            f'"{value_name}" was removed.',
        )

        return redirect(
            "supermarket:attribute_list"
        )    
    


# ============================================================
# PRODUCTS
# ============================================================

class ProductListView(
    LoginRequiredMixin,
    SupermarketManagerRequiredMixin,
    View,
):
    def get(self, request):

        products = (
            Product.objects
            .select_related(
                "category",
                "brand",
            )
            .prefetch_related(
                "variants"
            )
            .order_by("-created_at")
        )

        search = (
            request.GET.get("q", "")
            .strip()
        )

        category = (
            request.GET.get(
                "category",
                ""
            )
            .strip()
        )

        brand = (
            request.GET.get(
                "brand",
                ""
            )
            .strip()
        )

        if search:
            products = products.filter(
                Q(name__icontains=search)
                |
                Q(
                    variants__sku__icontains=
                    search
                )
            ).distinct()

        if category.isdigit():
            products = products.filter(
                category_id=category
            )

        if brand.isdigit():
            products = products.filter(
                brand_id=brand
            )

        categories = (
            ProductCategory.objects
            .filter(is_active=True)
            .order_by("name")
        )

        brands = (
            Brand.objects
            .filter(is_active=True)
            .order_by("name")
        )

        return render(
            request,
            (
                "supermarket/manager/"
                "product_list.html"
            ),
            {
                "products": products,
                "categories": categories,
                "brands": brands,
                "search": search,
                "selected_category": category,
                "selected_brand": brand,
            },
        )


class ProductCreateView(
    LoginRequiredMixin,
    SupermarketManagerRequiredMixin,
    View,
):
    def get(self, request):

        form = ProductForm()

        return render(
            request,
            (
                "supermarket/manager/"
                "product_form.html"
            ),
            {
                "form": form,
                "title": "Add Product",
            },
        )

    def post(self, request):

        form = ProductForm(
            request.POST,
            request.FILES,
        )

        if form.is_valid():

            product = form.save()

            messages.success(
                request,
                (
                    f'"{product.name}" was created. '
                    f"Now add its first variant."
                ),
            )

            return redirect(
                "supermarket:variant_add",
                product_pk=product.pk,
            )

        return render(
            request,
            (
                "supermarket/manager/"
                "product_form.html"
            ),
            {
                "form": form,
                "title": "Add Product",
            },
        )


class ProductUpdateView(
    LoginRequiredMixin,
    SupermarketManagerRequiredMixin,
    View,
):
    def get(self, request, pk):

        product = get_object_or_404(
            Product,
            pk=pk,
        )

        form = ProductForm(
            instance=product
        )

        return render(
            request,
            (
                "supermarket/manager/"
                "product_form.html"
            ),
            {
                "form": form,
                "product": product,
                "title": "Edit Product",
            },
        )

    def post(self, request, pk):

        product = get_object_or_404(
            Product,
            pk=pk,
        )

        form = ProductForm(
            request.POST,
            request.FILES,
            instance=product,
        )

        if form.is_valid():

            product = form.save()

            messages.success(
                request,
                (
                    f'"{product.name}" '
                    f"was updated."
                ),
            )

            return redirect(
                "supermarket:product_detail",
                pk=product.pk,
            )

        return render(
            request,
            (
                "supermarket/manager/"
                "product_form.html"
            ),
            {
                "form": form,
                "product": product,
                "title": "Edit Product",
            },
        )

from django.views.generic import View, ListView, DetailView
class ProductDetailView(
    LoginRequiredMixin,
    SupermarketManagerRequiredMixin,
    DetailView,
):
    model = Product

    template_name = (
        "supermarket/manager/"
        "product_detail.html"
    )

    context_object_name = "product"

    def get_queryset(self):

        return (
            Product.objects
            .select_related(
                "category",
                "brand",
            )
            .prefetch_related(
                "images",
                "variants__attribute_values__attribute",
                "variants__attribute_values__value",
            )
        )



# ============================================================
# PRODUCT IMAGE GALLERY
# ============================================================


class ProductGalleryUploadView(
    LoginRequiredMixin,
    SupermarketManagerRequiredMixin,
    View,
):

    def post(
        self,
        request,
        product_pk,
    ):

        product = get_object_or_404(
            Product,
            pk=product_pk,
        )

        form = ProductGalleryUploadForm(
            request.POST,
            request.FILES,
        )

        if not form.is_valid():

            for field_errors in form.errors.values():
                for error in field_errors:
                    messages.error(
                        request,
                        error,
                    )

            return redirect(
                "supermarket:product_detail",
                pk=product.pk,
            )

        images = form.cleaned_data[
            "images"
        ]

        current_max_order = (
            product.images
            .order_by("-order")
            .values_list(
                "order",
                flat=True,
            )
            .first()
        )

        next_order = (
            current_max_order + 1
            if current_max_order is not None
            else 0
        )

        created_count = 0

        for image in images:

            ProductImage.objects.create(
                product=product,
                image=image,
                alt_text=product.name,
                order=next_order,
            )

            next_order += 1
            created_count += 1

        messages.success(
            request,
            (
                f"{created_count} gallery "
                f'image{"s" if created_count != 1 else ""} '
                f"added to "
                f'"{product.name}".'
            ),
        )

        return redirect(
            "supermarket:product_detail",
            pk=product.pk,
        )


class ProductImageUpdateView(
    LoginRequiredMixin,
    SupermarketManagerRequiredMixin,
    View,
):

    template_name = (
        "supermarket/manager/"
        "product_image_form.html"
    )

    def get_image(
        self,
        pk,
    ):

        return get_object_or_404(
            ProductImage.objects
            .select_related("product"),
            pk=pk,
        )

    def get(
        self,
        request,
        pk,
    ):

        product_image = self.get_image(
            pk
        )

        form = ProductImageForm(
            instance=product_image
        )

        return render(
            request,
            self.template_name,
            {
                "form": form,
                "product_image": product_image,
                "product": product_image.product,
                "title": "Edit Product Image",
            },
        )

    def post(
        self,
        request,
        pk,
    ):

        product_image = self.get_image(
            pk
        )

        product = product_image.product

        form = ProductImageForm(
            request.POST,
            request.FILES,
            instance=product_image,
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                "Product image updated.",
            )

            return redirect(
                "supermarket:product_detail",
                pk=product.pk,
            )

        return render(
            request,
            self.template_name,
            {
                "form": form,
                "product_image": product_image,
                "product": product,
                "title": "Edit Product Image",
            },
        )


class ProductImageDeleteView(
    LoginRequiredMixin,
    SupermarketManagerRequiredMixin,
    View,
):

    def post(
        self,
        request,
        pk,
    ):

        product_image = get_object_or_404(
            ProductImage.objects
            .select_related("product"),
            pk=pk,
        )

        product = product_image.product

        # Keep a reference to the storage file
        # so we can remove it after deleting
        # the database record.
        image_file = product_image.image

        product_image.delete()

        if image_file:
            image_file.delete(
                save=False
            )

        messages.success(
            request,
            "Gallery image deleted.",
        )

        return redirect(
            "supermarket:product_detail",
            pk=product.pk,
        )





class ProductDeleteView(
    LoginRequiredMixin,
    SupermarketManagerRequiredMixin,
    View,
):
    def post(self, request, pk):

        product = get_object_or_404(
            Product,
            pk=pk,
        )

        name = product.name

        product.delete()

        messages.success(
            request,
            f'"{name}" was deleted.',
        )

        return redirect(
            "supermarket:product_list"
        )

# ============================================================
# PRODUCT VARIANTS
# ============================================================

# ============================================================
# PRODUCT VARIANT BULK CREATE
# ============================================================

from .forms import ProductVariantBulkCreateForm
class ProductVariantCreateView(
    LoginRequiredMixin,
    SupermarketManagerRequiredMixin,
    View,
):

    template_name = (
        "supermarket/manager/"
        "variant_form.html"
    )

    def get_product(
        self,
        product_pk,
    ):

        return get_object_or_404(
            Product.objects
            .select_related(
                "category",
                "brand",
            ),
            pk=product_pk,
        )

    def get(
        self,
        request,
        product_pk,
    ):

        product = self.get_product(
            product_pk
        )

        form = (
            ProductVariantBulkCreateForm(
                product=product,
            )
        )

        return render(
            request,
            self.template_name,
            {
                "form": form,
                "product": product,
                "variant": None,
                "is_bulk_create": True,
                "title": (
                    f"Add Variants — "
                    f"{product.name}"
                ),
            },
        )

    def post(
        self,
        request,
        product_pk,
    ):

        product = self.get_product(
            product_pk
        )

        form = (
            ProductVariantBulkCreateForm(
                request.POST,
                product=product,
            )
        )

        if form.is_valid():

            (
                created_variants,
                skipped_count,
            ) = form.save()

            created_count = len(
                created_variants
            )

            if created_count:

                messages.success(
                    request,
                    (
                        f"{created_count} variant"
                        f"{'' if created_count == 1 else 's'} "
                        f"created successfully."
                    ),
                )

            if skipped_count:

                messages.warning(
                    request,
                    (
                        f"{skipped_count} existing "
                        f"variant combination"
                        f"{'' if skipped_count == 1 else 's'} "
                        f"were skipped."
                    ),
                )

            if (
                not created_count
                and not skipped_count
            ):

                messages.warning(
                    request,
                    (
                        "No variants were created."
                    ),
                )

            return redirect(
                "supermarket:product_detail",
                pk=product.pk,
            )

        return render(
            request,
            self.template_name,
            {
                "form": form,
                "product": product,
                "variant": None,
                "is_bulk_create": True,
                "title": (
                    f"Add Variants — "
                    f"{product.name}"
                ),
            },
        )

# ============================================================
# PRODUCT VARIANT UPDATE
# ============================================================


class ProductVariantUpdateView(
    LoginRequiredMixin,
    SupermarketManagerRequiredMixin,
    View,
):

    template_name = (
        "supermarket/manager/"
        "variant_form.html"
    )

    def get_variant(
        self,
        pk,
    ):

        return get_object_or_404(
            ProductVariant.objects
            .select_related(
                "product",
                "product__category",
                "product__brand",
            )
            .prefetch_related(
                "attribute_values",
                "attribute_values__attribute",
                "attribute_values__value",
            ),
            pk=pk,
        )

    def get(
        self,
        request,
        pk,
    ):

        variant = self.get_variant(
            pk
        )

        product = (
            variant.product
        )

        form = ProductVariantForm(
            instance=variant,
            product=product,
        )

        return render(
            request,
            self.template_name,
            {
                "form": form,
                "product": product,
                "variant": variant,
                "is_bulk_create": False,
                "title": (
                    f"Edit Variant — "
                    f"{product.name}"
                ),
            },
        )

    def post(
        self,
        request,
        pk,
    ):

        variant = self.get_variant(
            pk
        )

        product = (
            variant.product
        )

        form = ProductVariantForm(
            request.POST,
            instance=variant,
            product=product,
        )

        if form.is_valid():

            variant = form.save()

            messages.success(
                request,
                (
                    f'Variant "{variant.sku}" '
                    f"was updated successfully."
                ),
            )

            return redirect(
                "supermarket:product_detail",
                pk=product.pk,
            )

        return render(
            request,
            self.template_name,
            {
                "form": form,
                "product": product,
                "variant": variant,
                "is_bulk_create": False,
                "title": (
                    f"Edit Variant — "
                    f"{product.name}"
                ),
            },
        )

class ProductVariantDeleteView(
    LoginRequiredMixin,
    SupermarketManagerRequiredMixin,
    View,
):
    def post(self, request, pk):

        variant = get_object_or_404(
            ProductVariant.objects
            .select_related("product"),
            pk=pk,
        )

        product_pk = (
            variant.product.pk
        )

        sku = variant.sku

        variant.delete()

        messages.success(
            request,
            (
                f'Variant "{sku}" '
                f"was deleted."
            ),
        )

        return redirect(
            "supermarket:product_detail",
            pk=product_pk,
        )        



# ============================================================
# CATEGORY ATTRIBUTE MANAGEMENT
# ============================================================
from .models import CategoryAttribute
from .forms import CategoryAttributeForm
class CategoryAttributeListView(
    LoginRequiredMixin,
    SupermarketManagerRequiredMixin,
    View,
):
    def get(
        self,
        request,
        category_pk,
    ):

        category = get_object_or_404(
            ProductCategory.objects
            .select_related("parent"),
            pk=category_pk,
        )

        direct_attributes = (
            CategoryAttribute.objects
            .filter(
                category=category
            )
            .select_related(
                "attribute",
                "category",
            )
            .prefetch_related(
                "attribute__values"
            )
            .order_by(
                "order",
                "attribute__order",
                "attribute__name",
            )
        )

        effective_attributes = (
            get_inherited_category_attributes(
                category
            )
        )

        direct_ids = {
            item.attribute_id
            for item in direct_attributes
        }

        inherited_attributes = [
            item
            for item in effective_attributes
            if item.attribute_id
            not in direct_ids
        ]

        category_chain = (
            get_category_chain(
                category
            )
        )

        context = {
            "category": category,

            "direct_attributes": (
                direct_attributes
            ),

            "inherited_attributes": (
                inherited_attributes
            ),

            "effective_attributes": (
                effective_attributes
            ),

            "category_chain": (
                category_chain
            ),
        }

        return render(
            request,
            (
                "supermarket/manager/"
                "category_attribute_list.html"
            ),
            context,
        )

class CategoryAttributeCreateView(
    LoginRequiredMixin,
    SupermarketManagerRequiredMixin,
    View,
):
    def get(self, request, category_pk):

        category = get_object_or_404(
            ProductCategory,
            pk=category_pk,
        )

        initial = {}

        attribute_id = (
            request.GET.get(
        "attribute",
        ""
            )
            .strip()
        )

        if attribute_id.isdigit():

            attribute = (
        ProductAttribute.objects
        .filter(
            pk=attribute_id,
            is_active=True,
        )
        .first()
    )

            if attribute:
                initial[
            "attribute"
        ] = attribute

        form = CategoryAttributeForm(
    category=category,
    initial=initial,
)

        return render(
            request,
            (
                "supermarket/manager/"
                "category_attribute_form.html"
            ),
            {
                "form": form,
                "category": category,
                "title": "Assign Attribute",
            },
        )

    def post(self, request, category_pk):

        category = get_object_or_404(
            ProductCategory,
            pk=category_pk,
        )

        form = CategoryAttributeForm(
            request.POST,
            category=category,
        )

        if form.is_valid():

            category_attribute = (
                form.save(
                    commit=False
                )
            )

            category_attribute.category = (
                category
            )

            category_attribute.save()

            messages.success(
                request,
                (
                    f'"{category_attribute.attribute.name}" '
                    f'was assigned to '
                    f'"{category.name}".'
                ),
            )

            return redirect(
                "supermarket:category_attribute_list",
                category_pk=category.pk,
            )

        return render(
            request,
            (
                "supermarket/manager/"
                "category_attribute_form.html"
            ),
            {
                "form": form,
                "category": category,
                "title": "Assign Attribute",
            },
        )


class CategoryAttributeUpdateView(
    LoginRequiredMixin,
    SupermarketManagerRequiredMixin,
    View,
):
    def get(self, request, pk):

        category_attribute = (
            get_object_or_404(
                CategoryAttribute.objects
                .select_related(
                    "category",
                    "attribute",
                ),
                pk=pk,
            )
        )

        form = CategoryAttributeForm(
            instance=category_attribute,
            category=(
                category_attribute.category
            ),
        )

        return render(
            request,
            (
                "supermarket/manager/"
                "category_attribute_form.html"
            ),
            {
                "form": form,
                "category": (
                    category_attribute.category
                ),
                "category_attribute": (
                    category_attribute
                ),
                "title": "Edit Category Attribute",
            },
        )

    def post(self, request, pk):

        category_attribute = (
            get_object_or_404(
                CategoryAttribute.objects
                .select_related(
                    "category",
                    "attribute",
                ),
                pk=pk,
            )
        )

        category = (
            category_attribute.category
        )

        form = CategoryAttributeForm(
            request.POST,
            instance=category_attribute,
            category=category,
        )

        if form.is_valid():

            category_attribute = (
                form.save()
            )

            messages.success(
                request,
                (
                    f'"{category_attribute.attribute.name}" '
                    f"was updated."
                ),
            )

            return redirect(
                "supermarket:category_attribute_list",
                category_pk=category.pk,
            )

        return render(
            request,
            (
                "supermarket/manager/"
                "category_attribute_form.html"
            ),
            {
                "form": form,
                "category": category,
                "category_attribute": (
                    category_attribute
                ),
                "title": (
                    "Edit Category Attribute"
                ),
            },
        )


class CategoryAttributeDeleteView(
    LoginRequiredMixin,
    SupermarketManagerRequiredMixin,
    View,
):
    def post(self, request, pk):

        category_attribute = (
            get_object_or_404(
                CategoryAttribute.objects
                .select_related(
                    "category",
                    "attribute",
                ),
                pk=pk,
            )
        )

        category = (
            category_attribute.category
        )

        attribute_name = (
            category_attribute
            .attribute
            .name
        )

        category_attribute.delete()

        messages.success(
            request,
            (
                f'"{attribute_name}" was removed '
                f'from "{category.name}".'
            ),
        )

        return redirect(
            "supermarket:category_attribute_list",
            category_pk=category.pk,
        )        
    


# ============================================================
# PUBLIC SUPERMARKET STOREFRONT
# ============================================================


class SupermarketStoreView(View):

    template_name = (
        "supermarket/store/index.html"
    )

    def get(self, request):

        products = (
            Product.objects
            .filter(
                is_active=True,
                variants__is_active=True,
            )
            .select_related(
                "category",
                "brand",
            )
            .prefetch_related(
                "images",
                "variants",
            )
            .distinct()
            .order_by(
                "-is_featured",
                "-created_at",
            )
        )

        categories = (
            ProductCategory.objects
            .filter(
                is_active=True,
            )
            .order_by(
                "order",
                "name",
            )
        )

        brands = (
            Brand.objects
            .filter(
                is_active=True,
            )
            .order_by("name")
        )

        search = (
            request.GET.get(
                "q",
                ""
            )
            .strip()
        )

        category_id = (
            request.GET.get(
                "category",
                ""
            )
            .strip()
        )

        brand_id = (
            request.GET.get(
                "brand",
                ""
            )
            .strip()
        )

        if search:

            products = products.filter(
                Q(
                    name__icontains=search
                )
                |
                Q(
                    description__icontains=search
                )
                |
                Q(
                    brand__name__icontains=search
                )
                |
                Q(
                    variants__sku__icontains=search
                )
            ).distinct()

        if category_id.isdigit():

            products = products.filter(
                category_id=category_id
            )

        if brand_id.isdigit():

            products = products.filter(
                brand_id=brand_id
            )

        context = {
            "products": products,
            "categories": categories,
            "brands": brands,
            "search": search,
            "selected_category": category_id,
            "selected_brand": brand_id,
        }

        return render(
            request,
            self.template_name,
            context,
        )


class SupermarketProductDetailView(View):

    template_name = (
        "supermarket/store/"
        "product_detail.html"
    )

    def get(
        self,
        request,
        pk,
    ):

        product = get_object_or_404(
            Product.objects
            .select_related(
                "category",
                "brand",
            )
            .prefetch_related(
                "images",
                "variants__attribute_values__attribute",
                "variants__attribute_values__value",
            ),
            pk=pk,
            is_active=True,
        )

        variants = (
            product.variants
            .filter(
                is_active=True,
            )
            .prefetch_related(
                "attribute_values__attribute",
                "attribute_values__value",
            )
            .order_by(
                "price",
                "id",
            )
        )

        # Build the available options for the
        # customer product selector.
        #
        # Example:
        # {
        #     Color: [Blue, Black],
        #     Storage: [128GB, 256GB]
        # }

        attribute_options = {}

        for variant in variants:

            for assignment in (
                variant.attribute_values.all()
            ):

                attribute = (
                    assignment.attribute
                )

                value = assignment.value

                if attribute.pk not in (
                    attribute_options
                ):

                    attribute_options[
                        attribute.pk
                    ] = {
                        "attribute": attribute,
                        "values": {},
                    }

                attribute_options[
                    attribute.pk
                ]["values"][
                    value.pk
                ] = value

        # Convert value dictionaries to lists.
        for item in (
            attribute_options.values()
        ):

            item["values"] = list(
                item["values"].values()
            )

            item["values"].sort(
                key=lambda value: (
                    value.order,
                    value.value.lower(),
                )
            )

        attribute_options = list(
            attribute_options.values()
        )

        attribute_options.sort(
            key=lambda item: (
                item["attribute"].order,
                item["attribute"].name.lower(),
            )
        )

        # Variant information for JavaScript.
        variant_data = []

        for variant in variants:

            attributes = {}

            for assignment in (
                variant.attribute_values.all()
            ):

                attributes[
                    str(
                        assignment.attribute_id
                    )
                ] = (
                    assignment.value_id
                )

            variant_data.append({
                "id": variant.pk,
                "sku": variant.sku,

                "price": str(
                    variant.price
                ),

                "sale_price": (
                    str(variant.sale_price)
                    if variant.sale_price
                    else None
                ),

                "current_price": str(
                    variant.current_price
                ),

                "stock_quantity": (
                    variant.stock_quantity
                ),

                "track_stock": (
                    variant.track_stock
                ),

                "in_stock": (
                    variant.in_stock
                ),

                "description": (
                    variant.variant_full_description
                ),

                "attributes": attributes,
            })

        context = {
            "product": product,
            "variants": variants,
            "attribute_options": (
                attribute_options
            ),
            "variant_data": variant_data,
        }

        return render(
            request,
            self.template_name,
            context,
        )    
    


from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator

from .cart import Cart


# ============================================================
# CUSTOMER CART
# ============================================================


class SupermarketCartView(View):

    template_name = (
        "supermarket/store/cart.html"
    )

    def get(self, request):

        cart = Cart(request)

        context = {
            "cart": cart,
        }

        return render(
            request,
            self.template_name,
            context,
        )


class SupermarketCartAddView(View):

    def post(
        self,
        request,
        variant_pk,
    ):

        variant = get_object_or_404(
            ProductVariant.objects
            .select_related(
                "product",
            ),
            pk=variant_pk,
            is_active=True,
            product__is_active=True,
        )

        try:
            quantity = int(
                request.POST.get(
                    "quantity",
                    1,
                )
            )

        except (
            TypeError,
            ValueError,
        ):
            quantity = 1


        if quantity < 1:
            quantity = 1


        cart = Cart(request)


        # --------------------------------------------
        # Stock validation
        # --------------------------------------------

        existing_quantity = 0

        variant_id = str(
            variant.pk
        )

        if variant_id in cart.cart:
            existing_quantity = (
                cart.cart[
                    variant_id
                ]["quantity"]
            )


        requested_quantity = (
            existing_quantity
            +
            quantity
        )


        if (
            variant.track_stock
            and
            requested_quantity
            >
            variant.stock_quantity
        ):

            return JsonResponse(
                {
                    "success": False,
                    "message": (
                        "The requested quantity "
                        "is not available."
                    ),
                    "available_quantity": (
                        variant.stock_quantity
                    ),
                },
                status=400,
            )


        cart.add(
            variant=variant,
            quantity=quantity,
        )


        return JsonResponse({
            "success": True,

            "message": (
                f"{variant.product.name} "
                "added to cart."
            ),

            "cart_count": len(cart),

            "variant_id": (
                variant.pk
            ),
        })


class SupermarketCartUpdateView(View):

    def post(
        self,
        request,
        variant_pk,
    ):

        variant = get_object_or_404(
            ProductVariant.objects
            .select_related(
                "product",
            ),
            pk=variant_pk,
            is_active=True,
            product__is_active=True,
        )

        try:
            quantity = int(
                request.POST.get(
                    "quantity",
                    1,
                )
            )

        except (
            TypeError,
            ValueError,
        ):

            return JsonResponse(
                {
                    "success": False,
                    "message": (
                        "Invalid quantity."
                    ),
                },
                status=400,
            )


        cart = Cart(request)


        if quantity <= 0:

            cart.remove(
                variant
            )

            return JsonResponse({
                "success": True,
                "removed": True,
                "cart_count": len(cart),
            })


        if (
            variant.track_stock
            and
            quantity
            >
            variant.stock_quantity
        ):

            return JsonResponse(
                {
                    "success": False,

                    "message": (
                        "The requested quantity "
                        "is not available."
                    ),

                    "available_quantity": (
                        variant.stock_quantity
                    ),
                },
                status=400,
            )


        cart.add(
            variant=variant,
            quantity=quantity,
            override_quantity=True,
        )


        return JsonResponse({
            "success": True,

            "removed": False,

            "quantity": quantity,

            "item_total": str(
                variant.current_price
                *
                quantity
            ),

            "cart_total": str(
                cart.get_total_price()
            ),

            "cart_count": len(cart),
        })


class SupermarketCartRemoveView(View):

    def post(
        self,
        request,
        variant_pk,
    ):

        variant = get_object_or_404(
            ProductVariant,
            pk=variant_pk,
        )

        cart = Cart(request)

        cart.remove(
            variant
        )

        return JsonResponse({
            "success": True,

            "cart_count": len(cart),

            "cart_total": str(
                cart.get_total_price()
            ),
        })
    

# ============================================================
# CHECKOUT
# ============================================================

class SupermarketCheckoutView(View):

    template_name = (
        "supermarket/store/checkout.html"
    )

    # WhatsApp number must contain country code
    # and digits only.
    WHATSAPP_NUMBER = "2347062548298"


    # ========================================================
    # GET
    # ========================================================

    def get(self, request):

        cart = Cart(request)

        if len(cart) == 0:

            messages.info(
                request,
                "Your cart is empty.",
            )

            return redirect(
                "supermarket:cart"
            )

        form = SupermarketCheckoutForm()

        return render(
            request,
            self.template_name,
            {
                "form": form,
                "cart": cart,
            },
        )


    # ========================================================
    # POST
    # ========================================================

    def post(self, request):

        cart = Cart(request)

        # ----------------------------------------------------
        # CART MUST NOT BE EMPTY
        # ----------------------------------------------------

        if len(cart) == 0:

            messages.error(
                request,
                "Your cart is empty.",
            )

            return redirect(
                "supermarket:cart"
            )


        # ----------------------------------------------------
        # VALIDATE CHECKOUT FORM
        # ----------------------------------------------------

        form = SupermarketCheckoutForm(
            request.POST
        )

        if not form.is_valid():

            return render(
                request,
                self.template_name,
                {
                    "form": form,
                    "cart": cart,
                },
            )


        # These variables are intentionally created outside
        # the transaction so they are available only after
        # the transaction completes successfully.

        order = None
        order_lines = []


        try:

            # =================================================
            # DATABASE TRANSACTION
            # =================================================

            with transaction.atomic():

                # =============================================
                # READ CART SESSION DATA
                # =============================================

                cart_data = {}

                for (
                    variant_id,
                    cart_item,
                ) in cart.cart.items():

                    # -----------------------------------------
                    # VALIDATE VARIANT ID
                    # -----------------------------------------

                    try:

                        normalized_variant_id = (
                            str(
                                int(
                                    variant_id
                                )
                            )
                        )

                    except (
                        TypeError,
                        ValueError,
                    ):

                        raise ValueError(
                            (
                                "Your cart contains an "
                                "invalid product. Please "
                                "refresh your cart and "
                                "try again."
                            )
                        )


                    # -----------------------------------------
                    # VALIDATE QUANTITY
                    # -----------------------------------------

                    try:

                        quantity = int(
                            cart_item.get(
                                "quantity",
                                0,
                            )
                        )

                    except (
                        TypeError,
                        ValueError,
                        AttributeError,
                    ):

                        raise ValueError(
                            (
                                "A product in your cart "
                                "has an invalid quantity."
                            )
                        )


                    if quantity < 1:

                        raise ValueError(
                            (
                                "A product in your cart "
                                "has an invalid quantity."
                            )
                        )


                    cart_data[
                        normalized_variant_id
                    ] = {
                        "quantity": quantity,
                    }


                # ---------------------------------------------
                # CART MUST STILL CONTAIN ITEMS
                # ---------------------------------------------

                if not cart_data:

                    raise ValueError(
                        "Your cart is empty."
                    )


                # =============================================
                # VARIANT IDS
                # =============================================

                variant_ids = [

                    int(variant_id)

                    for variant_id
                    in cart_data.keys()
                ]


                # =============================================
                # LOCK ALL PRODUCT VARIANTS
                #
                # This protects inventory from concurrent
                # checkouts.
                # =============================================

                variants = (
    ProductVariant.objects
    .select_for_update(of=("self",))
    .select_related(
        "product",
        "product__brand",
        "product__category",
    )
    .prefetch_related(
        "attribute_values__attribute",
        "attribute_values__value",
    )
    .filter(
        pk__in=variant_ids,
    )
)


                variants_by_id = {

                    str(variant.pk): variant

                    for variant
                    in variants
                }


                # =============================================
                # MAKE SURE EVERY CART VARIANT STILL EXISTS
                # =============================================

                if (
                    len(variants_by_id)
                    !=
                    len(cart_data)
                ):

                    raise ValueError(
                        (
                            "One or more products in your "
                            "cart are no longer available. "
                            "Please review your cart and "
                            "try again."
                        )
                    )


                # =============================================
                # VALIDATE ITEMS + CALCULATE TOTAL
                # =============================================

                order_lines = []

                subtotal = Decimal(
                    "0.00"
                )


                for (
                    variant_id,
                    cart_item,
                ) in cart_data.items():

                    variant = (
                        variants_by_id.get(
                            variant_id
                        )
                    )


                    # -----------------------------------------
                    # VARIANT EXISTS
                    # -----------------------------------------

                    if variant is None:

                        raise ValueError(
                            (
                                "A product in your cart "
                                "is no longer available."
                            )
                        )


                    # -----------------------------------------
                    # PRODUCT ACTIVE
                    # -----------------------------------------

                    if not variant.product.is_active:

                        raise ValueError(
                            (
                                f"{variant.product.name} "
                                "is no longer available."
                            )
                        )


                    # -----------------------------------------
                    # VARIANT ACTIVE
                    # -----------------------------------------

                    if not variant.is_active:

                        variant_name = (
                            variant.variant_description
                            or
                            variant.sku
                        )

                        raise ValueError(
                            (
                                f"{variant.product.name} "
                                f"({variant_name}) is no "
                                "longer available."
                            )
                        )


                    # -----------------------------------------
                    # QUANTITY
                    # -----------------------------------------

                    quantity = int(
                        cart_item[
                            "quantity"
                        ]
                    )


                    if quantity < 1:

                        raise ValueError(
                            "Invalid cart quantity."
                        )


                    # =========================================
                    # FINAL STOCK CHECK
                    # =========================================

                    if variant.track_stock:

                        if (
                            variant.stock_quantity
                            < quantity
                        ):

                            variant_name = (
                                variant.variant_description
                                or
                                variant.sku
                            )

                            raise ValueError(
                                (
                                    f"Only "
                                    f"{variant.stock_quantity} "
                                    f"unit(s) of "
                                    f"{variant.product.name} "
                                    f"({variant_name}) "
                                    f"are currently available."
                                )
                            )


                    # =========================================
                    # ALWAYS USE SERVER-SIDE PRICE
                    # =========================================

                    unit_price = Decimal(
                        str(
                            variant.current_price
                        )
                    )


                    # -----------------------------------------
                    # SAFETY CHECK
                    # -----------------------------------------

                    if unit_price < 0:

                        raise ValueError(
                            (
                                f"{variant.product.name} "
                                "currently has an invalid "
                                "price."
                            )
                        )


                    # =========================================
                    # LINE TOTAL
                    # =========================================

                    line_total = (
                        unit_price
                        *
                        quantity
                    )


                    subtotal += (
                        line_total
                    )


                    # =========================================
                    # VARIANT DESCRIPTION SNAPSHOT
                    # =========================================

                    variant_description = (
                        variant
                        .variant_full_description
                        or
                        ""
                    )


                    # =========================================
                    # STORE TRUSTED ORDER LINE
                    # =========================================

                    order_lines.append({

                        "variant": variant,

                        "product": (
                            variant.product
                        ),

                        "product_name": (
                            variant.product.name
                        ),

                        "sku": (
                            variant.sku
                            or
                            ""
                        ),

                        "variant_description": (
                            variant_description
                        ),

                        "quantity": quantity,

                        "unit_price": (
                            unit_price
                        ),

                        "subtotal": (
                            line_total
                        ),
                    })


                # ---------------------------------------------
                # MUST HAVE ORDER LINES
                # ---------------------------------------------

                if not order_lines:

                    raise ValueError(
                        "Your cart is empty."
                    )


                # ---------------------------------------------
                # TOTAL MUST BE VALID
                # ---------------------------------------------

                if subtotal < 0:

                    raise ValueError(
                        "Invalid order total."
                    )


                # =============================================
                # CREATE ORDER
                # =============================================

                order = (
                    SupermarketOrder.objects.create(

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
                            or
                            None
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
                            or
                            ""
                        ),

                        subtotal=(
                            subtotal
                        ),

                        total_amount=(
                            subtotal
                        ),

                        status=(
                            "pending"
                        ),

                        payment_status=(
                            "unpaid"
                        ),
                    )
                )


                # =============================================
                # PREPARE ORDER ITEM SNAPSHOTS
                # =============================================

                order_items = []


                for line in order_lines:

                    variant = (
                        line[
                            "variant"
                        ]
                    )


                    order_items.append(
    SupermarketOrderItem(
        order=order,
        product=line["product"],
        variant=line["variant"],
        product_name=line["product_name"],
        sku=line["sku"],
        size="",
        color="",
        variant_description=line["variant_description"],
        unit_price=line["unit_price"],
        quantity=line["quantity"],
        subtotal=line["subtotal"],
        stock_deducted=line["variant"].track_stock,
    )
)


                # =============================================
                # CREATE ORDER ITEMS
                # =============================================

                SupermarketOrderItem.objects.bulk_create(
                    order_items
                )


                # =============================================
                # REDUCE INVENTORY
                # =============================================

                for line in order_lines:

                    variant = (
                        line[
                            "variant"
                        ]
                    )

                    quantity = (
                        line[
                            "quantity"
                        ]
                    )


                    if variant.track_stock:

                        ProductVariant.objects.filter(
                            pk=variant.pk
                        ).update(

                            stock_quantity=(

                                F(
                                    "stock_quantity"
                                )

                                -

                                quantity
                            )
                        )


                # =============================================
                # TRANSACTION ENDS HERE
                #
                # If anything above raises an exception,
                # Django rolls the entire order back.
                # =============================================


            # =================================================
            # TRANSACTION SUCCESSFUL
            # =================================================

            if order is None:

                raise ValueError(
                    (
                        "We could not create your order. "
                        "Please try again."
                    )
                )


            # =================================================
            # CLEAR CART
            #
            # Only after the transaction has successfully
            # committed.
            # =================================================

            cart.clear()


            # =================================================
            # BUILD WHATSAPP MESSAGE
            #
            # IMPORTANT:
            # Use the trusted order_lines calculated from the
            # database, NOT browser supplied prices.
            # =================================================

            whatsapp_lines = [

                "🛒 *NEW SUPERMARKET ORDER*",

                "",

                (
                    f"*Order:* "
                    f"#{order.order_number}"
                ),

                "",

                "👤 *CUSTOMER DETAILS*",

                (
                    f"Name: "
                    f"{order.customer_name}"
                ),

                (
                    f"Phone: "
                    f"{order.phone}"
                ),
            ]


            # -------------------------------------------------
            # OPTIONAL EMAIL
            # -------------------------------------------------

            if order.email:

                whatsapp_lines.append(
                    f"Email: {order.email}"
                )


            # -------------------------------------------------
            # ITEMS
            # -------------------------------------------------

            whatsapp_lines.extend([

                "",

                "🛍️ *ORDER ITEMS*",

                "",
            ])


            for line in order_lines:

                product_name = (
                    line[
                        "product_name"
                    ]
                )

                quantity = (
                    line[
                        "quantity"
                    ]
                )

                unit_price = (
                    line[
                        "unit_price"
                    ]
                )

                line_total = (
                    line[
                        "subtotal"
                    ]
                )

                sku = (
                    line[
                        "sku"
                    ]
                )

                variant_description = (
                    line[
                        "variant_description"
                    ]
                )


                # ---------------------------------------------
                # PRODUCT
                # ---------------------------------------------

                whatsapp_lines.append(
                    (
                        f"• {quantity} × "
                        f"{product_name}"
                    )
                )


                # ---------------------------------------------
                # VARIANT ATTRIBUTES
                # ---------------------------------------------

                if variant_description:

                    whatsapp_lines.append(
                        (
                            f"  "
                            f"{variant_description}"
                        )
                    )


                # ---------------------------------------------
                # SKU
                # ---------------------------------------------

                if sku:

                    whatsapp_lines.append(
                        f"  SKU: {sku}"
                    )


                # ---------------------------------------------
                # PRICE
                # ---------------------------------------------

                whatsapp_lines.append(
                    (
                        f"  ₦{unit_price:,.2f} each "
                        f"= ₦{line_total:,.2f}"
                    )
                )


                whatsapp_lines.append("")


            # =================================================
            # ORDER TOTAL
            # =================================================

            whatsapp_lines.extend([

                "━━━━━━━━━━━━━━━━━━",

                (
                    f"💰 *TOTAL: "
                    f"₦{order.total_amount:,.2f}*"
                ),

                "━━━━━━━━━━━━━━━━━━",

                "",

                "📍 *DELIVERY ADDRESS*",

                str(
                    order.address
                ),
            ])


            # =================================================
            # CUSTOMER NOTE
            # =================================================

            if order.note:

                whatsapp_lines.extend([

                    "",

                    "📝 *CUSTOMER NOTE*",

                    str(
                        order.note
                    ),
                ])


            # =================================================
            # PAYMENT
            # =================================================

            whatsapp_lines.extend([

                "",

                "💳 *PAYMENT STATUS*",

                order.get_payment_status_display(),

                "",

                (
                    "Please confirm availability, "
                    "payment and delivery details."
                ),
            ])


            # =================================================
            # CREATE WHATSAPP MESSAGE
            # =================================================

            whatsapp_message = "\n".join(
                whatsapp_lines
            )


            # =================================================
            # CREATE WHATSAPP URL
            # =================================================

            whatsapp_url = (

                f"https://wa.me/"
                f"{self.WHATSAPP_NUMBER}"
                f"?text={quote(whatsapp_message)}"
            )


            # =================================================
            # STORE ORDER OWNERSHIP IN SESSION
            #
            # The success/WhatsApp views can use this to stop
            # another visitor from guessing an order number.
            # =================================================

            request.session[
                "latest_supermarket_order"
            ] = order.pk


            request.session[
                "supermarket_whatsapp_url"
            ] = whatsapp_url


            # =================================================
            # SUCCESS MESSAGE
            # =================================================

            messages.success(
                request,
                (
                    f"Order "
                    f"{order.order_number} "
                    f"was placed successfully."
                ),
            )


            # =================================================
            # SUCCESS PAGE
            # =================================================

            return redirect(
                "supermarket:order_success",
                order_number=(
                    order.order_number
                ),
            )


        # =====================================================
        # CUSTOMER / CART VALIDATION ERRORS
        # =====================================================

        except ValueError as error:

            messages.error(
                request,
                str(error),
            )

            return render(
                request,
                self.template_name,
                {
                    "form": form,
                    "cart": cart,
                },
            )


        # =====================================================
        # UNEXPECTED ERROR
        #
        # Do not expose database/internal errors to customers.
        # =====================================================

        except Exception as error:

            print(
                "\n"
                "========== SUPERMARKET CHECKOUT ERROR =========="
            )

            print(
                type(error).__name__
            )

            print(
                str(error)
            )

            print(
                "================================================"
                "\n"
            )


            messages.error(
                request,
                (
                    "We could not place your order "
                    "right now. Your cart has not "
                    "been cleared. Please try again."
                ),
            )


            return render(
                request,
                self.template_name,
                {
                    "form": form,
                    "cart": cart,
                },
            )


# ============================================================
# ORDER SUCCESS
# ============================================================
# ============================================================
# ORDER SUCCESS
# ============================================================

# ============================================================
# SUPERMARKET ORDER SUCCESS
# ============================================================

class SupermarketOrderSuccessView(View):

    template_name = (
        "supermarket/store/order_success.html"
    )

    def get(self, request, order_number):

        # ----------------------------------------------------
        # GET ORDER
        # ----------------------------------------------------

        order = get_object_or_404(
            SupermarketOrder.objects.prefetch_related(
                "items"
            ),
            order_number=order_number,
        )

        # ----------------------------------------------------
        # SESSION SECURITY
        # ----------------------------------------------------

        latest_order_id = request.session.get(
            "latest_supermarket_order"
        )

        if latest_order_id != order.pk:

            messages.error(
                request,
                "You cannot access this order."
            )

            return redirect(
                "supermarket:store"
            )

        # ----------------------------------------------------
        # GET WHATSAPP URL ONCE
        # ----------------------------------------------------

        whatsapp_url = request.session.pop(
            "supermarket_whatsapp_url",
            None,
        )

        # ----------------------------------------------------
        # RENDER SUCCESS PAGE
        # ----------------------------------------------------

        return render(
            request,
            self.template_name,
            {
                "order": order,
                "whatsapp_url": whatsapp_url,
            },
        )   
# ============================================================
# SUPERMARKET ORDER WHATSAPP
# ============================================================

class SupermarketOrderWhatsAppView(View):

    WHATSAPP_NUMBER = (
        "2347062548298"
    )


    def get(
        self,
        request,
        order_number,
    ):

        # ----------------------------------------------------
        # GET ORDER
        # ----------------------------------------------------

        order = get_object_or_404(

            SupermarketOrder.objects
            .prefetch_related(
                "items"
            ),

            order_number=order_number,
        )


        # ----------------------------------------------------
        # SECURITY CHECK
        # ----------------------------------------------------

        latest_order_id = (
            request.session.get(
                "latest_supermarket_order"
            )
        )


        if latest_order_id != order.pk:

            return redirect(
                "supermarket:store"
            )


        # ----------------------------------------------------
        # BUILD TRUSTED MESSAGE
        # ----------------------------------------------------

        lines = [

            "Hello Dikubs Supermarket 👋",

            "",

            "I just placed an order.",

            "",

            (
                f"Order: "
                f"{order.order_number}"
            ),

            "",

            "🛍️ *ORDER ITEMS*",

            "",
        ]


        for item in order.items.all():

            lines.append(
                (
                    f"{item.quantity} × "
                    f"{item.product_name}"
                )
            )


            if item.variant_description:

                lines.append(
                    (
                        f"   "
                        f"{item.variant_description}"
                    )
                )


            if item.sku:

                lines.append(
                    f"   SKU: {item.sku}"
                )


            lines.append(
                (
                    f"   ₦"
                    f"{item.subtotal:,.2f}"
                )
            )

            lines.append("")


        # ----------------------------------------------------
        # TOTAL + CUSTOMER
        # ----------------------------------------------------

        lines.extend([

            "━━━━━━━━━━━━━━━━━━",

            (
                f"*TOTAL: "
                f"₦{order.total_amount:,.2f}*"
            ),

            "━━━━━━━━━━━━━━━━━━",

            "",

            "👤 *CUSTOMER DETAILS*",

            f"Name: {order.customer_name}",

            f"Phone: {order.phone}",

            (
                f"Delivery Address: "
                f"{order.address}"
            ),
        ])


        if order.email:

            lines.append(
                f"Email: {order.email}"
            )


        if order.note:

            lines.extend([

                "",

                "📝 *INSTRUCTIONS*",

                str(
                    order.note
                ),
            ])


        lines.extend([

            "",

            (
                f"Payment Status: "
                f"{order.get_payment_status_display()}"
            ),

            "",

            (
                "Please confirm my order "
                "and delivery details. Thank you."
            ),
        ])


        message = "\n".join(
            lines
        )


        # ----------------------------------------------------
        # WHATSAPP URL
        # ----------------------------------------------------

        whatsapp_url = (

            f"https://wa.me/"
            f"{self.WHATSAPP_NUMBER}"
            f"?text={quote(message)}"
        )


        # ----------------------------------------------------
        # RECORD HANDOFF
        # ----------------------------------------------------

        if not order.whatsapp_opened:

            order.whatsapp_opened = True

            order.save(
                update_fields=[
                    "whatsapp_opened",
                    "updated_at",
                ]
            )


        return redirect(
            whatsapp_url
        )    
    



# ============================================================
# SUPERMARKET MANAGER — ORDER LIST
# ============================================================

class SupermarketOrderListView(
    LoginRequiredMixin,
    SupermarketManagerRequiredMixin,
    View,
):

    template_name = (
        "supermarket/manager/order_list.html"
    )

    def get(self, request):

        orders = SupermarketOrder.objects.all()

        status = request.GET.get(
            "status", ""
        ).strip()

        payment_status = request.GET.get(
            "payment_status", ""
        ).strip()

        search = request.GET.get(
            "search", ""
        ).strip()

        valid_statuses = {
            value
            for value, label
            in SupermarketOrder.STATUS_CHOICES
        }

        valid_payment_statuses = {
            value
            for value, label
            in SupermarketOrder.PAYMENT_STATUS_CHOICES
        }

        if status in valid_statuses:
            orders = orders.filter(
                status=status
            )

        if payment_status in valid_payment_statuses:
            orders = orders.filter(
                payment_status=payment_status
            )

        if search:
            orders = orders.filter(
                Q(order_number__icontains=search)
                | Q(customer_name__icontains=search)
                | Q(phone__icontains=search)
                | Q(email__icontains=search)
            )

        orders = orders.order_by(
            "-created_at"
        )

        paginator = Paginator(
            orders,
            20,
        )

        page_obj = paginator.get_page(
            request.GET.get("page")
        )

        context = {
            "orders": page_obj,
            "page_obj": page_obj,
            "selected_status": status,
            "selected_payment_status": payment_status,
            "search_query": search,

            "status_choices": (
                SupermarketOrder.STATUS_CHOICES
            ),

            "payment_status_choices": (
                SupermarketOrder.PAYMENT_STATUS_CHOICES
            ),

            "total_orders_count": (
                SupermarketOrder.objects.count()
            ),

            "pending_count": (
                SupermarketOrder.objects.filter(
                    status="pending"
                ).count()
            ),

            "processing_count": (
                SupermarketOrder.objects.filter(
                    status="processing"
                ).count()
            ),

            "ready_count": (
                SupermarketOrder.objects.filter(
                    status="ready"
                ).count()
            ),

            "delivery_count": (
                SupermarketOrder.objects.filter(
                    status="out_for_delivery"
                ).count()
            ),

            "delivered_count": (
                SupermarketOrder.objects.filter(
                    status="delivered"
                ).count()
            ),
        }

        return render(
            request,
            self.template_name,
            context,
        )


# ============================================================
# SUPERMARKET MANAGER — ORDER DETAIL
# ============================================================

class SupermarketOrderDetailView(
    LoginRequiredMixin,
    SupermarketManagerRequiredMixin,
    View,
):

    template_name = (
        "supermarket/manager/order_detail.html"
    )

    def get(self, request, pk):

        order = get_object_or_404(
            SupermarketOrder.objects.prefetch_related(
                "items"
            ),
            pk=pk,
        )

        context = {
            "order": order,

            "status_choices": (
                SupermarketOrder.STATUS_CHOICES
            ),

            "payment_status_choices": (
                SupermarketOrder.PAYMENT_STATUS_CHOICES
            ),
        }

        return render(
            request,
            self.template_name,
            context,
        )


# ============================================================
# SUPERMARKET MANAGER — UPDATE ORDER STATUS
# ============================================================
SUPERMARKET_ORDER_TRANSITIONS = {
    "pending": {"confirmed", "cancelled"},
    "confirmed": {"processing", "cancelled"},
    "processing": {"ready", "cancelled"},
    "ready": {"out_for_delivery", "delivered", "cancelled"},
    "out_for_delivery": {"delivered"},
    "delivered": set(),
    "cancelled": set(),
}
# ============================================================
# SUPERMARKET MANAGER — UPDATE ORDER STATUS
# ============================================================

class SupermarketOrderStatusUpdateView(
    LoginRequiredMixin,
    SupermarketManagerRequiredMixin,
    View,
):

    # ========================================================
    # POST
    # ========================================================

    def post(self, request, pk):

        # ----------------------------------------------------
        # READ REQUESTED STATUS
        # ----------------------------------------------------

        new_status = request.POST.get(
            "status",
            "",
        ).strip()

        # ----------------------------------------------------
        # VALIDATE STATUS
        # ----------------------------------------------------

        valid_statuses = {

            value

            for value, label
            in SupermarketOrder.STATUS_CHOICES
        }

        if new_status not in valid_statuses:

            messages.error(
                request,
                "Invalid order status.",
            )

            return redirect(
                "supermarket:order_detail",
                pk=pk,
            )

        # ----------------------------------------------------
        # VARIABLES USED AFTER SUCCESSFUL TRANSACTION
        # ----------------------------------------------------

        order_number = None

        status_display = None

        restored_items_count = 0

        restored_units_count = 0

        # ====================================================
        # DATABASE TRANSACTION
        # ====================================================

        try:

            with transaction.atomic():

                # ============================================
                # LOCK ORDER
                #
                # Prevent two managers from updating the
                # same order at the same time.
                # ============================================

                order = get_object_or_404(

                    SupermarketOrder.objects
                    .select_for_update(),

                    pk=pk,
                )

                # ============================================
                # CURRENT ORDER STATUS
                # ============================================

                old_status = order.status

                order_number = (
                    order.order_number
                )

                # ============================================
                # NO CHANGE
                # ============================================

                if old_status == new_status:

                    messages.info(
                        request,
                        (
                            "This order already has "
                            "the selected status."
                        ),
                    )

                    return redirect(
                        "supermarket:order_detail",
                        pk=pk,
                    )

                # ============================================
                # VALIDATE STATUS TRANSITION
                # ============================================

                allowed_statuses = (

                    SUPERMARKET_ORDER_TRANSITIONS.get(
                        old_status,
                        set(),
                    )
                )

                if new_status not in allowed_statuses:

                    old_status_display = (
                        order.get_status_display()
                    )

                    new_status_display = dict(
                        SupermarketOrder.STATUS_CHOICES
                    ).get(
                        new_status,
                        new_status,
                    )

                    messages.error(
                        request,
                        (
                            f"Cannot change order "
                            f"{order_number} from "
                            f"{old_status_display} "
                            f"to {new_status_display}."
                        ),
                    )

                    return redirect(
                        "supermarket:order_detail",
                        pk=pk,
                    )

                # ============================================
                # CANCELLATION PAYMENT SAFEGUARD
                #
                # Do not cancel an order with a payment
                # that requires a separate refund workflow.
                # ============================================

                if new_status == "cancelled":

                    if order.payment_status in {
                        "paid",
                        "refunded",
                    }:

                        messages.error(
                            request,
                            (
                                "This order has a paid "
                                "or refunded payment "
                                "status. Complete the "
                                "appropriate refund "
                                "workflow before "
                                "cancelling it."
                            ),
                        )

                        return redirect(
                            "supermarket:order_detail",
                            pk=pk,
                        )

                # ============================================
                # CANCELLATION
                # ============================================

                if new_status == "cancelled":

                    # ----------------------------------------
                    # FETCH ORDER ITEMS
                    # ----------------------------------------

                    items = list(
                        order.items.all()
                    )

                    # ----------------------------------------
                    # VALIDATE INVENTORY SNAPSHOTS
                    #
                    # An item whose stock was deducted
                    # must still have a variant reference.
                    # Otherwise inventory cannot be
                    # restored reliably.
                    # ----------------------------------------

                    for item in items:

                        if not item.stock_deducted:

                            continue

                        if item.variant_id is None:

                            raise ValueError(
                                (
                                    "Cannot cancel this "
                                    "order automatically "
                                    "because a stock-tracked "
                                    "order item no longer "
                                    "has a product variant. "
                                    "Reconcile its inventory "
                                    "before cancelling."
                                )
                            )

                    # ----------------------------------------
                    # GET VARIANTS THAT REQUIRE RESTORATION
                    # ----------------------------------------

                    variant_ids = sorted({

                        item.variant_id

                        for item in items

                        if (
                            item.stock_deducted
                            and
                            item.variant_id is not None
                        )
                    })

                    # ----------------------------------------
                    # LOCK PRODUCT VARIANTS
                    #
                    # Use consistent PK ordering to reduce
                    # deadlock risk when several orders
                    # contain overlapping variants.
                    # ----------------------------------------

                    variants = {

                        variant.pk: variant

                        for variant in (

                            ProductVariant.objects

                            .select_for_update()

                            .filter(
                                pk__in=variant_ids
                            )

                            .order_by("pk")
                        )
                    }

                    # ----------------------------------------
                    # ENSURE ALL REQUIRED VARIANTS EXIST
                    # ----------------------------------------

                    missing_variant_ids = (

                        set(variant_ids)

                        -

                        set(variants.keys())
                    )

                    if missing_variant_ids:

                        raise ValueError(
                            (
                                "Cannot cancel this order "
                                "automatically because "
                                "one or more product "
                                "variants are missing. "
                                "Reconcile inventory "
                                "before cancelling."
                            )
                        )

                    # ========================================
                    # RESTORE INVENTORY
                    # ========================================

                    for item in items:

                        # ------------------------------------
                        # ONLY RESTORE STOCK THAT WAS
                        # ACTUALLY DEDUCTED AT CHECKOUT
                        # ------------------------------------

                        if not item.stock_deducted:

                            continue

                        variant = variants.get(
                            item.variant_id
                        )

                        if variant is None:

                            raise ValueError(
                                (
                                    "A required product "
                                    "variant could not "
                                    "be found."
                                )
                            )

                        # ------------------------------------
                        # VALIDATE QUANTITY
                        # ------------------------------------

                        if item.quantity < 1:

                            raise ValueError(
                                (
                                    "Cannot restore "
                                    "inventory because "
                                    "an order item has "
                                    "an invalid quantity."
                                )
                            )

                        # ------------------------------------
                        # RESTORE INVENTORY
                        #
                        # Do not check variant.track_stock
                        # here. The stock_deducted snapshot
                        # is the source of truth.
                        # ------------------------------------

                        updated_rows = (

                            ProductVariant.objects

                            .filter(
                                pk=variant.pk
                            )

                            .update(

                                stock_quantity=(

                                    F(
                                        "stock_quantity"
                                    )

                                    +

                                    item.quantity
                                )
                            )
                        )

                        # ------------------------------------
                        # VERIFY UPDATE
                        # ------------------------------------

                        if updated_rows != 1:

                            raise ValueError(
                                (
                                    "Inventory restoration "
                                    "failed. The order "
                                    "was not cancelled."
                                )
                            )

                        # ------------------------------------
                        # TRACK RESTORATION
                        # ------------------------------------

                        restored_items_count += 1

                        restored_units_count += (
                            item.quantity
                        )

                # ============================================
                # UPDATE ORDER STATUS
                # ============================================

                order.status = new_status

                order.save(

                    update_fields=[
                        "status",
                        "updated_at",
                    ]
                )

                # ============================================
                # SAVE DISPLAY VALUES
                # ============================================

                status_display = (
                    order.get_status_display()
                )

                # ============================================
                # AUDIT LOG
                #
                # This is an application log, not a
                # permanent database audit record.
                # ============================================

                logger.info(
                    (
                        "Supermarket order status "
                        "updated. "
                        "order_id=%s "
                        "order_number=%s "
                        "old_status=%s "
                        "new_status=%s "
                        "manager_id=%s "
                        "restored_items=%s "
                        "restored_units=%s"
                    ),

                    order.pk,

                    order.order_number,

                    old_status,

                    new_status,

                    request.user.pk,

                    restored_items_count,

                    restored_units_count,
                )

            # =================================================
            # TRANSACTION COMMITTED SUCCESSFULLY
            # =================================================

            if new_status == "cancelled":

                messages.success(
                    request,
                    (
                        f"Order {order_number} "
                        f"was cancelled successfully. "
                        f"{restored_units_count} "
                        f"unit(s) of inventory "
                        f"were restored."
                    ),
                )

            else:

                messages.success(
                    request,
                    (
                        f"Order {order_number} "
                        f"was updated to "
                        f"{status_display}."
                    ),
                )

        # =====================================================
        # INVENTORY / BUSINESS RULE ERRORS
        # =====================================================

        except ValueError as error:

            logger.warning(
                (
                    "Supermarket order status "
                    "update rejected. "
                    "order_id=%s "
                    "requested_status=%s "
                    "manager_id=%s "
                    "reason=%s"
                ),

                pk,

                new_status,

                request.user.pk,

                str(error),
            )

            messages.error(
                request,
                str(error),
            )

        # =====================================================
        # UNEXPECTED ERRORS
        # =====================================================

        except Exception:

            logger.exception(
                (
                    "Unexpected supermarket order "
                    "status update error. "
                    "order_id=%s "
                    "requested_status=%s "
                    "manager_id=%s"
                ),

                pk,

                new_status,

                request.user.pk,
            )

            messages.error(
                request,
                (
                    "The order could not be updated. "
                    "No changes were saved. "
                    "Please try again."
                ),
            )

        # =====================================================
        # RETURN TO ORDER DETAIL
        # =====================================================

        return redirect(
            "supermarket:order_detail",
            pk=pk,
        )


# ============================================================
# SUPERMARKET MANAGER — UPDATE PAYMENT STATUS
# ============================================================

class SupermarketOrderPaymentUpdateView(
    LoginRequiredMixin,
    SupermarketManagerRequiredMixin,
    View,
):

    def post(self, request, pk):

        new_payment_status = request.POST.get(
            "payment_status", ""
        ).strip()

        valid_statuses = {
            value
            for value, label
            in SupermarketOrder.PAYMENT_STATUS_CHOICES
        }

        if new_payment_status not in valid_statuses:

            messages.error(
                request,
                "Invalid payment status.",
            )

            return redirect(
                "supermarket:order_detail",
                pk=pk,
            )

        with transaction.atomic():

            order = get_object_or_404(
                SupermarketOrder.objects
                .select_for_update(),
                pk=pk,
            )

            if order.status == "cancelled":

                messages.error(
                    request,
                    (
                        "Payment status cannot be changed "
                        "for a cancelled order through "
                        "this form."
                    ),
                )

                return redirect(
                    "supermarket:order_detail",
                    pk=pk,
                )

            if (
                order.payment_status == "refunded"
                or new_payment_status == "refunded"
            ):

                messages.error(
                    request,
                    (
                        "Refunds must be handled through "
                        "a separate verified refund process."
                    ),
                )

                return redirect(
                    "supermarket:order_detail",
                    pk=pk,
                )

            if order.payment_status == "paid":

                messages.error(
                    request,
                    (
                        "A paid order cannot be changed "
                        "through this form."
                    ),
                )

                return redirect(
                    "supermarket:order_detail",
                    pk=pk,
                )

            if new_payment_status == "paid":

                messages.error(
                    request,
                    (
                        "Payment must be verified through "
                        "the approved payment process "
                        "before marking it as paid."
                    ),
                )

                return redirect(
                    "supermarket:order_detail",
                    pk=pk,
                )

            if order.payment_status == new_payment_status:

                messages.info(
                    request,
                    "Payment status is unchanged.",
                )

                return redirect(
                    "supermarket:order_detail",
                    pk=pk,
                )

            order.payment_status = new_payment_status

            order.save(
                update_fields=[
                    "payment_status",
                    "updated_at",
                ]
            )

        messages.success(
            request,
            "Payment status updated.",
        )

        return redirect(
            "supermarket:order_detail",
            pk=pk,
        )    