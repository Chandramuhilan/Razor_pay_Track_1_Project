"""
Razorpay Payment API Integration Service.
Handles Razorpay Order Creation (`/v1/orders`), Payment Link/Payload Generation,
and HMAC-SHA256 Signature Verification in Test Mode.
Supports real Razorpay credentials or automatic fallback test mode.
"""

import hmac
import hashlib
import time
import uuid
import logging
import razorpay
from typing import Dict, Any, Tuple
from app.models import Cart, RazorpayOrderResponse, PaymentVerification
from app.config import settings

logger = logging.getLogger(__name__)

class RazorpayService:
    def __init__(self, key_id: str = None, key_secret: str = None):
        self.key_id = key_id or settings.RAZORPAY_KEY_ID
        self.key_secret = key_secret or settings.RAZORPAY_KEY_SECRET
        self._init_client()

    def _init_client(self):
        try:
            if self.key_id and self.key_secret:
                self.client = razorpay.Client(auth=(self.key_id, self.key_secret))
            else:
                self.client = None
        except Exception:
            self.client = None

    @property
    def mode(self) -> str:
        return 'live' if self.client and settings.is_razorpay_configured() else 'simulated'

    def create_order(self, cart: Cart, buyer_id: str) -> RazorpayOrderResponse:
        """
        Creates a Razorpay order for the specified cart total amount in INR.
        Converts INR to paise (1 INR = 100 Paise).
        """
        amount_paise = int(round(cart.total_amount_inr * 100))
        receipt_id = f"rcpt_{cart.cart_id}"

        notes = {
            "buyer_id": buyer_id,
            "cart_id": cart.cart_id,
            "item_count": str(len(cart.items)),
            "protocol": "A2A_AP2_COMMERCE"
        }

        # Attempt real API call via Razorpay SDK if valid credentials provided
        if self.client and settings.is_razorpay_configured():
            try:
                order_data = {
                    "amount": amount_paise,
                    "currency": "INR",
                    "receipt": receipt_id,
                    "notes": notes
                }
                res = self.client.order.create(data=order_data)
                return RazorpayOrderResponse(
                    order_id=res["id"],
                    amount_inr=cart.total_amount_inr,
                    amount_paise=res["amount"],
                    currency=res.get("currency", "INR"),
                    status=res.get("status", "created"),
                    receipt=res.get("receipt", receipt_id),
                    created_at=res.get("created_at", int(time.time()))
                )
            except Exception as e:
                logger.warning(f"Razorpay API call failed, falling back to simulated mode: {e}")

        # Fallback Test Mode order generation
        simulated_order_id = f"order_sim_{uuid.uuid4().hex[:14]}"
        return RazorpayOrderResponse(
            order_id=simulated_order_id,
            amount_inr=cart.total_amount_inr,
            amount_paise=amount_paise,
            currency="INR",
            status="created",
            receipt=receipt_id,
            created_at=int(time.time())
        )

    def generate_simulated_payment(self, order_id: str) -> Tuple[str, str]:
        """
        Generates a valid test payment ID and corresponding HMAC signature for automated testing.
        """
        payment_id = f"pay_{uuid.uuid4().hex[:14]}"
        msg = f"{order_id}|{payment_id}"
        secret_bytes = self.key_secret.encode('utf-8') if self.key_secret else b"simulated_secret"
        sig = hmac.new(
            secret_bytes,
            msg.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return payment_id, sig

    def verify_payment_signature(self, verification: PaymentVerification) -> bool:
        """
        Verifies the HMAC-SHA256 signature sent back after Razorpay payment authorization.
        `generated_signature = hmac_sha256(order_id + "|" + payment_id, secret)`
        """
        msg = f"{verification.razorpay_order_id}|{verification.razorpay_payment_id}"
        secret_bytes = self.key_secret.encode('utf-8') if self.key_secret else b"simulated_secret"
        expected_sig = hmac.new(
            secret_bytes,
            msg.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(verification.razorpay_signature, expected_sig)
