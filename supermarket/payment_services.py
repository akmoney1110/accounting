
import uuid
import logging
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.urls import reverse

from .models import SupermarketPaystackPayment

# Reuse the authenticated Paystack request helper
# from your existing shared payment module.
from eatery.views import paystack_request


logger = logging.getLogger(__name__)


def supermarket_naira_to_kobo(amount):
    amount = Decimal(str(amount)).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )
    return int(amount * 100)


def initialize_supermarket_payment(request, order):
    """Initialize Paystack for an unpaid supermarket order."""

    if order.payment_status == "paid":
        return None

    if not order.email:
        raise ValueError(
            "A customer email is required for online payment."
        )

    amount_kobo = supermarket_naira_to_kobo(
        order.total_amount
    )

    if amount_kobo <= 0:
        raise ValueError(
            "The order total must be greater than zero."
        )

    payment = SupermarketPaystackPayment.objects.create(
        order=order,
        reference=uuid.uuid4().hex,
        amount_kobo=amount_kobo,
        currency="NGN",
        status="pending",
    )

    callback_url = request.build_absolute_uri(
        reverse("supermarket:paystack_callback")
    )

    try:
        data = paystack_request(
            "POST",
            "/transaction/initialize",
            json={
                "email": order.email,
                "amount": str(payment.amount_kobo),
                "currency": "NGN",
                "reference": payment.reference,
                "callback_url": callback_url,
                "metadata": {
    "payment_type": "supermarket",
    "business": "supermarket",
    "order_id": order.pk,
    "order_number": str(order.order_number),
    "payment_id": payment.pk,
},
            },
        )

        authorization_url = data.get("authorization_url")

        if not authorization_url:
            raise RuntimeError(
                "Paystack did not return a checkout URL."
            )

        payment.authorization_url = authorization_url
        payment.save(
            update_fields=[
                "authorization_url",
                "updated_at",
            ]
        )

        if order.payment_status != "paid":
            order.payment_status = "pending"
            order.save(
                update_fields=[
                    "payment_status",
                    "updated_at",
                ]
            )

        return payment

    except Exception:
        payment.status = "failed"
        payment.save(
            update_fields=["status", "updated_at"]
        )
        raise




from django.db import transaction
from django.utils import timezone

from .models import SupermarketOrder, SupermarketPaystackPayment


def verify_supermarket_payment(reference):
    payment = SupermarketPaystackPayment.objects.get(
        reference=reference
    )

    if payment.status == "success":
        return True, payment.order

    data = paystack_request(
        "GET",
        f"/transaction/verify/{payment.reference}",
    )

    valid = (
        data.get("status") == "success"
        and data.get("reference") == payment.reference
        and data.get("currency") == payment.currency
        and data.get("amount") == payment.amount_kobo
    )

    if not valid:
        if data.get("status") in ("failed", "abandoned"):
            SupermarketPaystackPayment.objects.filter(
                pk=payment.pk,
                status="pending",
            ).update(status="failed")

        return False, payment.order

    with transaction.atomic():
        locked_payment = (
            SupermarketPaystackPayment.objects
            .select_for_update()
            .select_related("order")
            .get(pk=payment.pk)
        )

        order = (
            SupermarketOrder.objects
            .select_for_update()
            .get(pk=locked_payment.order_id)
        )

        # A callback or webhook may already have processed it.
        if locked_payment.status == "success":
            return True, order

        # Do not accept a second payment against an already-paid order.
        if order.payment_status == "paid":
            return False, order

        locked_payment.status = "success"
        locked_payment.gateway_transaction_id = str(
            data.get("id", "")
        )
        locked_payment.paid_at = timezone.now()
        locked_payment.save(
            update_fields=[
                "status",
                "gateway_transaction_id",
                "paid_at",
                "updated_at",
            ]
        )

        order.payment_status = "paid"

        # Only set the order to confirmed if this is the correct
        # initial status for your supermarket workflow.
        if order.status == "pending":
            order.status = "confirmed"

        order.save(
            update_fields=[
                "payment_status",
                "status",
                "updated_at",
            ]
        )

    return True, order
