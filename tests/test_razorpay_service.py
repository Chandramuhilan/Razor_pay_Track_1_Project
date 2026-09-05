"""
Unit tests for Razorpay Service integration and signature verification.
"""

import pytest
from app.models import Cart, CartItem, PaymentVerification
from app.services.razorpay_service import RazorpayService

def test_razorpay_order_creation_and_verification():
    service = RazorpayService()
    cart = Cart(
        items=[CartItem(product_id="laptop", name="Dev Laptop", price_inr=67999.0)],
        base_subtotal_inr=65000.0,
        upsell_subtotal_inr=2999.0,
        total_amount_inr=67999.0
    )

    order = service.create_order(cart, buyer_id="buyer_01")
    assert order.order_id.startswith("order_")
    assert order.amount_paise == 6799900
    assert order.amount_inr == 67999.0

    payment_id, signature = service.generate_simulated_payment(order.order_id)
    verification = PaymentVerification(
        razorpay_order_id=order.order_id,
        razorpay_payment_id=payment_id,
        razorpay_signature=signature
    )

    assert service.verify_payment_signature(verification) is True

def test_live_payment_errors_do_not_fall_back_to_simulation(monkeypatch):
    service = RazorpayService(key_id="rzp_test_example", key_secret="secret")
    service.client = object()

    with pytest.raises(RuntimeError, match="Standard Checkout"):
        service.execute_payment("order_real", 100)

def test_authorized_payment_uses_sdk_capture_amount_position():
    class FakePayment:
        def __init__(self):
            self.capture_args = None

        def fetch(self, payment_id):
            assert payment_id == "pay_authorized"
            return {"status": "authorized", "currency": "INR"}

        def capture(self, *args):
            self.capture_args = args
            return {"status": "captured", "captured": True, "currency": "INR"}

    class FakeClient:
        def __init__(self):
            self.payment = FakePayment()

    service = RazorpayService(key_id="rzp_test_example", key_secret="secret")
    service.client = FakeClient()
    result = service.get_payment_status("pay_authorized", 299800)
    assert result["status"] == "captured"
    assert service.client.payment.capture_args == (
        "pay_authorized", 299800, {"currency": "INR"}
    )

def test_order_requests_automatic_capture(monkeypatch):
    class FakeOrders:
        def __init__(self):
            self.data = None

        def create(self, data):
            self.data = data
            return {"id": "order_auto", "amount": data["amount"], "currency": "INR", "status": "created"}

    class FakeClient:
        def __init__(self):
            self.order = FakeOrders()

    service = RazorpayService(key_id="rzp_test_example", key_secret="secret")
    fake_client = FakeClient()
    service.client = fake_client
    cart = Cart(items=[CartItem(product_id="p", name="Item", price_inr=10)], total_amount_inr=10)
    service.create_order(cart, "buyer")
    assert fake_client.order.data["payment_capture"] == 1
