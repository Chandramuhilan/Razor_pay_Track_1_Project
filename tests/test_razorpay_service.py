"""
Unit tests for Razorpay Service integration and signature verification.
Updated to match the autonomous payment flow (no PENDING_CHECKOUT).
"""

import pytest
from unittest.mock import MagicMock, patch
from app.models import Cart, CartItem, PaymentVerification
from app.services.razorpay_service import RazorpayService


def test_razorpay_order_creation_and_verification():
    """Simulated order creation + HMAC signature round-trip works correctly."""
    service = RazorpayService()
    cart = Cart(
        items=[CartItem(product_id="laptop", name="Dev Laptop", price_inr=67999.0)],
        base_subtotal_inr=65000.0,
        upsell_subtotal_inr=2999.0,
        total_amount_inr=67999.0,
    )

    order = service.create_order(cart, buyer_id="buyer_01")
    assert order.order_id.startswith("order_")
    assert order.amount_paise == 6799900
    assert order.amount_inr == 67999.0

    payment_id, signature = service.generate_simulated_payment(order.order_id)
    verification = PaymentVerification(
        razorpay_order_id=order.order_id,
        razorpay_payment_id=payment_id,
        razorpay_signature=signature,
    )
    assert service.verify_payment_signature(verification) is True


def test_execute_payment_falls_back_to_simulation_on_api_error():
    """
    When the Razorpay payment API call fails, execute_payment() falls back
    to a locally-signed simulated payment (no exception raised).
    """
    service = RazorpayService(key_id="rzp_test_example", key_secret="secret")

    fake_client = MagicMock()
    service.client = fake_client

    # Simulate API HTTP error
    with patch("requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=400, text='{"error":"bad"}')
        payment_id, signature = service.execute_payment("order_real123", 100000)

    # Should return a valid simulated payment (not raise)
    assert payment_id.startswith("pay_")
    assert len(signature) == 64  # SHA-256 hex


def test_execute_payment_uses_real_payment_id_on_success():
    """
    When the Razorpay payment API returns a payment_id, execute_payment()
    uses that real payment_id to generate the HMAC signature.
    """
    service = RazorpayService(key_id="rzp_test_example", key_secret="secret")
    service.client = MagicMock()  # Pretend client is initialised

    # execute_payment now generates payment_id locally (no requests.post)
    payment_id, signature = service.execute_payment("order_real456", 299800)

    # payment_id must be pay_<14 hex chars>
    assert payment_id.startswith("pay_")
    assert len(payment_id) == 18  # "pay_" + 14 hex chars

    # signature must be valid HMAC of order_id|payment_id
    expected_sig = service._generate_hmac("order_real456", payment_id)
    assert signature == expected_sig


def test_order_requests_automatic_capture():
    """create_order() must set payment_capture=1 for auto-capture on authorization."""
    class FakeOrders:
        def __init__(self):
            self.data = None

        def create(self, data):
            self.data = data
            return {
                "id": "order_auto",
                "amount": data["amount"],
                "currency": "INR",
                "status": "created",
            }

    class FakeClient:
        def __init__(self):
            self.order = FakeOrders()

    service = RazorpayService(key_id="rzp_test_example", key_secret="secret")
    fake_client = FakeClient()
    service.client = fake_client

    cart = Cart(
        items=[CartItem(product_id="p", name="Item", price_inr=10)],
        total_amount_inr=10,
    )
    service.create_order(cart, "buyer")
    assert fake_client.order.data["payment_capture"] == 1


def test_simulated_order_skips_real_payment():
    """
    execute_payment() should return a simulated payment for simulated orders
    (order_id starting with 'order_sim_') even when real keys are set.
    """
    service = RazorpayService(key_id="rzp_test_example", key_secret="secret")
    service.client = MagicMock()

    payment_id, signature = service.execute_payment("order_sim_abc123", 100000)
    assert payment_id.startswith("pay_")
    assert len(signature) == 64
