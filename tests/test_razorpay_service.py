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

    def fail(*args, **kwargs):
        raise RuntimeError("gateway unavailable")

    monkeypatch.setattr("app.services.razorpay_service.requests.post", fail)
    with pytest.raises(RuntimeError, match="Razorpay payment execution failed"):
        service.execute_payment("order_real", 100)
