from django import forms

from .models import FoodCategory, FoodItem


INPUT_CLASS = (
    "w-full rounded-xl border border-gray-300 bg-white px-4 py-3 "
    "text-gray-900 outline-none transition "
    "focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100"
)

CHECKBOX_CLASS = (
    "h-5 w-5 rounded border-gray-300 "
    "text-emerald-600 focus:ring-emerald-500"
)


# ============================================================
# FOOD CATEGORY FORM
# ============================================================
class FoodCategoryForm(forms.ModelForm):

    class Meta:
        model = FoodCategory

        fields = [
            "name",
            "description",
            "is_active",
            "order",
        ]

        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": INPUT_CLASS,
                    "placeholder": "e.g. Rice Meals",
                }
            ),

            "description": forms.Textarea(
                attrs={
                    "class": INPUT_CLASS,
                    "rows": 4,
                    "placeholder": "Optional category description",
                }
            ),

            "is_active": forms.CheckboxInput(
                attrs={
                    "class": CHECKBOX_CLASS,
                }
            ),

            "order": forms.NumberInput(
                attrs={
                    "class": INPUT_CLASS,
                    "min": "0",
                    "placeholder": "0",
                }
            ),
        }

    def clean_name(self):
        name = self.cleaned_data.get("name", "").strip()

        if not name:
            raise forms.ValidationError(
                "Category name is required."
            )

        existing = FoodCategory.objects.filter(
            name__iexact=name
        )

        if self.instance.pk:
            existing = existing.exclude(
                pk=self.instance.pk
            )

        if existing.exists():
            raise forms.ValidationError(
                "A category with this name already exists."
            )

        return name


# ============================================================
# FOOD ITEM FORM
# ============================================================
class FoodItemForm(forms.ModelForm):

    class Meta:
        model = FoodItem

        fields = [
            "category",
            "name",
            "description",
            "price",
            "image",
            "is_available",
            "is_featured",
        ]

        widgets = {
            "category": forms.Select(
                attrs={
                    "class": INPUT_CLASS,
                }
            ),

            "name": forms.TextInput(
                attrs={
                    "class": INPUT_CLASS,
                    "placeholder": "e.g. Jollof Rice & Chicken",
                }
            ),

            "description": forms.Textarea(
                attrs={
                    "class": INPUT_CLASS,
                    "rows": 5,
                    "placeholder": (
                        "Describe the meal, portion, "
                        "ingredients, or what comes with it."
                    ),
                }
            ),

            "price": forms.NumberInput(
                attrs={
                    "class": INPUT_CLASS,
                    "placeholder": "0.00",
                    "step": "0.01",
                    "min": "0",
                }
            ),

            "image": forms.ClearableFileInput(
                attrs={
                    "class": INPUT_CLASS,
                    "accept": "image/*",
                }
            ),

            "is_available": forms.CheckboxInput(
                attrs={
                    "class": CHECKBOX_CLASS,
                }
            ),

            "is_featured": forms.CheckboxInput(
                attrs={
                    "class": CHECKBOX_CLASS,
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["category"].queryset = (
            FoodCategory.objects
            .order_by("order", "name")
        )

        self.fields["category"].empty_label = (
            "Select a food category"
        )

    def clean_name(self):
        name = self.cleaned_data.get("name", "").strip()

        if not name:
            raise forms.ValidationError(
                "Food name is required."
            )

        return name

    def clean_price(self):
        price = self.cleaned_data.get("price")

        if price is None:
            return price

        if price <= 0:
            raise forms.ValidationError(
                "Food price must be greater than zero."
            )

        return price
    


class CustomerCheckoutForm(forms.Form):

    customer_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(
            attrs={
                "class": INPUT_CLASS,
                "placeholder": "Your full name",
            }
        ),
    )

    phone = forms.CharField(
        max_length=30,
        widget=forms.TextInput(
            attrs={
                "class": INPUT_CLASS,
                "placeholder": "e.g. 08012345678",
                "type": "tel",
            }
        ),
    )

    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(
            attrs={
                "class": INPUT_CLASS,
                "placeholder": "Email address (optional)",
            }
        ),
    )

    address = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "class": INPUT_CLASS,
                "rows": 3,
                "placeholder": "Delivery address",
            }
        ),
    )

    note = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": INPUT_CLASS,
                "rows": 3,
                "placeholder": (
                    "Any special instructions? (optional)"
                ),
            }
        ),
    )

    def clean_customer_name(self):
        return self.cleaned_data["customer_name"].strip()

    def clean_phone(self):
        phone = self.cleaned_data["phone"].strip()

        if len(phone) < 7:
            raise forms.ValidationError(
                "Please enter a valid phone number."
            )

        return phone

    def clean_address(self):
        address = self.cleaned_data["address"].strip()

        if len(address) < 5:
            raise forms.ValidationError(
                "Please enter a valid delivery address."
            )

        return address    