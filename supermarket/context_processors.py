from .cart import Cart


def supermarket_cart(request):
    """
    Make the supermarket cart available
    to every Django template.
    """

    cart = Cart(request)

    return {
        "supermarket_cart": cart,
        "supermarket_cart_count": len(cart),
    }