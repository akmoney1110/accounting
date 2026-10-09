from decimal import Decimal

from .models import ProductVariant


CART_SESSION_ID = "supermarket_cart"


class Cart:
    """
    Session-based supermarket shopping cart.

    IMPORTANT:
    Only JSON-serializable values are stored in the session.

    Session structure:

    {
        "3": {
            "quantity": 2
        },
        "8": {
            "quantity": 1
        }
    }

    Product, ProductVariant, Decimal and other Django/Python
    objects are NEVER stored directly in the session.
    """

    def __init__(self, request):

        self.session = request.session

        cart = self.session.get(
            CART_SESSION_ID
        )

        if not isinstance(cart, dict):
            cart = {}

            self.session[
                CART_SESSION_ID
            ] = cart

        self.cart = cart


    # =========================================================
    # SAVE
    # =========================================================

    def save(self):

        self.session[
            CART_SESSION_ID
        ] = self.cart

        self.session.modified = True


    # =========================================================
    # ADD ITEM
    # =========================================================

    def add(
        self,
        variant,
        quantity=1,
        override_quantity=False,
    ):

        variant_id = str(
            variant.pk
        )


        try:

            quantity = int(
                quantity
            )

        except (
            TypeError,
            ValueError,
        ):

            quantity = 1


        if quantity < 1:
            quantity = 1


        if variant_id not in self.cart:

            self.cart[
                variant_id
            ] = {
                "quantity": 0,
            }


        if override_quantity:

            self.cart[
                variant_id
            ]["quantity"] = quantity

        else:

            self.cart[
                variant_id
            ]["quantity"] += quantity


        self.save()


    # =========================================================
    # REMOVE ITEM
    # =========================================================

    def remove(
        self,
        variant,
    ):

        variant_id = str(
            variant.pk
        )


        if variant_id in self.cart:

            del self.cart[
                variant_id
            ]

            self.save()


    # =========================================================
    # CLEAR CART
    # =========================================================

    def clear(self):

        self.session.pop(
            CART_SESSION_ID,
            None,
        )

        self.cart = {}

        self.session.modified = True


    # =========================================================
    # NUMBER OF ITEMS
    # =========================================================

    def __len__(self):

        total_quantity = 0


        for item in self.cart.values():

            try:

                quantity = int(
                    item.get(
                        "quantity",
                        0,
                    )
                )

            except (
                TypeError,
                ValueError,
                AttributeError,
            ):

                quantity = 0


            if quantity > 0:

                total_quantity += (
                    quantity
                )


        return total_quantity


    # =========================================================
    # ITERATE CART ITEMS
    # =========================================================

    def __iter__(self):
        """
        Convert session cart entries into rich cart items.

        IMPORTANT:

        We create NEW dictionaries here.

        We never modify the dictionaries stored inside
        request.session.
        """

        variant_ids = list(
            self.cart.keys()
        )


        if not variant_ids:
            return


        variants = (
            ProductVariant.objects
            .filter(
                pk__in=variant_ids,
                is_active=True,
                product__is_active=True,
            )
            .select_related(
                "product",
                "product__brand",
                "product__category",
            )
            .prefetch_related(
                "attribute_values__attribute",
                "attribute_values__value",
                "product__images",
            )
        )


        found_variant_ids = set()


        for variant in variants:

            variant_id = str(
                variant.pk
            )


            found_variant_ids.add(
                variant_id
            )


            session_item = (
                self.cart.get(
                    variant_id,
                    {}
                )
            )


            try:

                quantity = int(
                    session_item.get(
                        "quantity",
                        0,
                    )
                )

            except (
                TypeError,
                ValueError,
                AttributeError,
            ):

                quantity = 0


            if quantity < 1:
                continue


            price = Decimal(
                str(
                    variant.current_price
                )
            )


            total_price = (
                price
                *
                quantity
            )


            # ---------------------------------------------
            # THIS IS A BRAND-NEW DICTIONARY.
            #
            # It is NOT stored in the Django session.
            # ---------------------------------------------

            item = {
                "variant": variant,

                "product": (
                    variant.product
                ),

                "quantity": (
                    quantity
                ),

                "price": (
                    price
                ),

                "total_price": (
                    total_price
                ),
            }


            yield item


        # -------------------------------------------------
        # Remove invalid/deleted/inactive variants
        # from the session.
        # -------------------------------------------------

        missing_ids = (
            set(
                self.cart.keys()
            )
            -
            found_variant_ids
        )


        if missing_ids:

            for variant_id in (
                missing_ids
            ):

                self.cart.pop(
                    variant_id,
                    None,
                )


            self.save()


    # =========================================================
    # TOTAL CART PRICE
    # =========================================================

    def get_total_price(self):

        total = Decimal(
            "0.00"
        )


        for item in self:

            total += (
                item[
                    "total_price"
                ]
            )


        return total


    # =========================================================
    # CHECK IF CART IS EMPTY
    # =========================================================

    def is_empty(self):

        return (
            len(self) == 0
        )


    # =========================================================
    # GET RAW QUANTITY
    # =========================================================

    def get_quantity(
        self,
        variant,
    ):

        variant_id = str(
            variant.pk
        )


        item = self.cart.get(
            variant_id
        )


        if not item:

            return 0


        try:

            return int(
                item.get(
                    "quantity",
                    0,
                )
            )

        except (
            TypeError,
            ValueError,
            AttributeError,
        ):

            return 0