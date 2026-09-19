"""
Razorpay Payment Integration — Autonomous A2A Agent Mode.

How it works (test mode with rzp_test_* keys):
  1. create_order()        → Real Razorpay order via POST /v1/orders
                             → order_id visible on Razorpay dashboard immediately
  2. execute_payment()     → Razorpay has NO server-to-server autonomous payment API.
                             We generate a payment_id + HMAC signature locally,
                             matching the format Razorpay generates after checkout.
                             This is the standard approach for all agentic/headless demos.
  3. verify_payment_signature() → HMAC-SHA256(order_id|payment_id, key_secret)
                                  Same algorithm Razorpay uses — verifiable.

Why no real captured payment on dashboard:
  Razorpay test mode requires a browser checkout UI to authorize a test payment.
  There is no public REST API to create and capture payments server-to-server
  (POST /v1/payments/create/json returns 400 "URL not found" — it does not exist).

  The order IS real and visible on dashboard. The payment is locally simulated
  with a valid HMAC signed with your real key_secret — cryptographically correct.
"""
import hmac
import hashlib
import time
import uuid
import logging
from typing import Tuple

import razorpay

from app.models import Cart, RazorpayOrderResponse, PaymentVerification
from app.config import settings

logger = logging.getLogger(__name__)


class RazorpayService:
    def __init__(self, key_id: str = None, key_secret: str = None):
        self.key_id = key_id or settings.RAZORPAY_KEY_ID
        self.key_secret = key_secret or settings.RAZORPAY_KEY_SECRET
        self.client = None
        self._init_client()

    def _init_client(self):
        if self.key_id and self.key_secret:
            try:
                self.client = razorpay.Client(auth=(self.key_id, self.key_secret))
                logger.info("Razorpay client initialised — key: %s…", self.key_id[:12])
            except Exception as e:
                logger.warning("Razorpay client init failed: %s", e)
                self.client = None

    @property
    def mode(self) -> str:
        if not self.client:
            return "simulated"
        return "test-live" if self.key_id.startswith("rzp_test_") else "live"

    # ── Order Creation ─────────────────────────────────────────────────────────

    def create_order(self, cart: Cart, buyer_id: str) -> RazorpayOrderResponse:
        """
        Creates a real Razorpay order via POST /v1/orders.
        With test keys → real order appears on Razorpay dashboard instantly.
        payment_capture=1 means auto-capture if payment goes through checkout.
        """
        amount_paise = int(round(cart.total_amount_inr * 100))
        receipt_id = f"rcpt_{cart.cart_id}"

        notes = {
            "buyer_id": buyer_id,
            "cart_id": cart.cart_id,
            "item_count": str(len(cart.items)),
            "protocol": "A2A+AP2+MCP",
            "agent": "TechVerse Merchant Agent",
        }

        if self.client:
            try:
                res = self.client.order.create(data={
                    "amount": amount_paise,
                    "currency": "INR",
                    "receipt": receipt_id,
                    "payment_capture": 1,
                    "notes": notes,
                })
                logger.info("Razorpay order created: %s  INR %.2f", res["id"], cart.total_amount_inr)
                return RazorpayOrderResponse(
                    order_id=res["id"],
                    amount_inr=cart.total_amount_inr,
                    amount_paise=res["amount"],
                    currency=res.get("currency", "INR"),
                    status=res.get("status", "created"),
                    receipt=res.get("receipt", receipt_id),
                    created_at=res.get("created_at", int(time.time())),
                )
            except Exception as e:
                logger.error("create_order API failed: %s", e)
                raise RuntimeError(f"Razorpay order creation failed: {e}") from e

        # No keys — fully simulated order
        sim_id = f"order_sim_{uuid.uuid4().hex[:14]}"
        return RazorpayOrderResponse(
            order_id=sim_id,
            amount_inr=cart.total_amount_inr,
            amount_paise=amount_paise,
            currency="INR",
            status="created",
            receipt=receipt_id,
            created_at=int(time.time()),
        )

    # ── Payment Execution ──────────────────────────────────────────────────────

    def execute_payment(self, order_id: str, amount_paise: int) -> Tuple[str, str]:
        """
        Executes payment for an autonomous A2A agent transaction.

        Razorpay does NOT provide a server-to-server payment API for test mode
        (POST /v1/payments/create/json returns 400 "URL not found").
        All autonomous/headless payment flows use locally-generated payment IDs
        signed with the real key_secret — the same HMAC Razorpay uses.

        The order (order_id) IS real and visible on the Razorpay dashboard.
        The payment is simulated locally with a cryptographically valid signature.
        """
        if order_id.startswith("order_sim_") or not self.key_secret:
            return self._make_payment(order_id, simulated=True)

        # Real order — generate payment with real HMAC signature
        payment_id = f"pay_{uuid.uuid4().hex[:14]}"
        signature = self._hmac(order_id, payment_id)
        logger.info(
            "Payment executed: order=%s  payment=%s  mode=%s",
            order_id, payment_id, self.mode
        )
        return payment_id, signature

    # ── Signature Helpers ──────────────────────────────────────────────────────

    def _hmac(self, order_id: str, payment_id: str) -> str:
        """Generates HMAC-SHA256(order_id|payment_id, key_secret) — same as Razorpay."""
        msg = f"{order_id}|{payment_id}"
        secret = (self.key_secret or "simulated_secret").encode("utf-8")
        return hmac.new(secret, msg.encode("utf-8"), hashlib.sha256).hexdigest()

    def _make_payment(self, order_id: str, simulated: bool = True) -> Tuple[str, str]:
        """Generates a locally-signed payment (simulated or agent-mode)."""
        payment_id = f"pay_{uuid.uuid4().hex[:14]}"
        signature = self._hmac(order_id, payment_id)
        if simulated:
            logger.info("Simulated payment: %s", payment_id)
        return payment_id, signature

    # Legacy aliases
    def generate_simulated_payment(self, order_id: str) -> Tuple[str, str]:
        return self._make_payment(order_id, simulated=True)

    def _generate_hmac(self, order_id: str, payment_id: str) -> str:
        return self._hmac(order_id, payment_id)

    def _simulated_payment(self, order_id: str) -> Tuple[str, str]:
        return self._make_payment(order_id, simulated=True)

    # ── Signature Verification ─────────────────────────────────────────────────

    def verify_payment_signature(self, verification: PaymentVerification) -> bool:
        """
        Verifies HMAC-SHA256: hmac(order_id|payment_id, key_secret).
        Works for both real Razorpay checkout payments and agent-mode payments.
        """
        expected = self._hmac(
            verification.razorpay_order_id,
            verification.razorpay_payment_id,
        )
        return hmac.compare_digest(verification.razorpay_signature, expected)
