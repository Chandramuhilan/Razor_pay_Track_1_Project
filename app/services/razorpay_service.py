"""
Razorpay Payment API Integration Service — Real Test Mode.

With real keys set in .env:
  1. create_order()          → Real POST /v1/orders      → real order_id on dashboard
    2. checkout_options()       → Browser Standard Checkout configuration
    3. verify_checkout_payment() → SDK HMAC-SHA256 verification

Without keys (demo mode):
  All three steps produce locally-signed simulated data. Tests pass.
  Razorpay dashboard shows nothing (expected — no API calls made).
"""

import hmac
import hashlib
import time
import uuid
import logging
import razorpay
from typing import Tuple
from app.models import Cart, RazorpayOrderResponse, PaymentVerification
from app.config import settings

logger = logging.getLogger(__name__)


class RazorpayService:
    def __init__(self, key_id: str = None, key_secret: str = None):
        self.key_id = key_id or settings.RAZORPAY_KEY_ID
        self.key_secret = key_secret or settings.RAZORPAY_KEY_SECRET
        self.client = None
        self.pending_checkouts = {}
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
        return "test-live" if self.client else "simulated"

    # ── Order Creation ────────────────────────────────────────────────────────

    def create_order(self, cart: Cart, buyer_id: str) -> RazorpayOrderResponse:
        """
        Creates a real Razorpay order via POST /v1/orders.
        With real keys → appears on Razorpay dashboard immediately.
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
                logger.info("Razorpay order created: %s  ₹%.2f", res["id"], cart.total_amount_inr)
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

        # Simulated fallback
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

    # ── Standard Checkout ─────────────────────────────────────────────────────

    def checkout_options(self, order: RazorpayOrderResponse, name: str = "TechVerse Systems") -> dict:
        """Builds the browser Checkout configuration for a server-created order."""
        if not self.client:
            raise RuntimeError("Razorpay Checkout requires configured test keys")
        return {
            "key": self.key_id,
            "amount": order.amount_paise,
            "currency": order.currency,
            "name": name,
            "description": "Agentic Commerce purchase",
            "order_id": order.order_id,
            "method": {
                "card": True,
                "upi": True,
                "netbanking": True,
                "wallet": True,
            },
            "prefill": {"email": "aibuyer@agentcommerce.test", "contact": "9999999999"},
            "notes": {"test_upi": "success@razorpay"},
        }

    def verify_checkout_payment(self, verification: PaymentVerification) -> bool:
        """Verifies the signature returned by Razorpay Standard Checkout."""
        if self.client:
            try:
                self.client.utility.verify_payment_signature({
                    "razorpay_order_id": verification.razorpay_order_id,
                    "razorpay_payment_id": verification.razorpay_payment_id,
                    "razorpay_signature": verification.razorpay_signature,
                })
                return True
            except Exception:
                return False
        return self.verify_payment_signature(verification)

    def register_checkout(self, order: RazorpayOrderResponse, context: dict) -> None:
        """Keeps the validated cart context until Checkout returns its callback."""
        self.pending_checkouts[order.order_id] = context

    def get_payment_status(self, payment_id: str, amount_paise: int) -> dict:
        """Fetches and, when necessary, captures a verified Checkout payment."""
        if not self.client:
            return {"status": "captured", "captured": True}
        payment = None
        for attempt in range(5):
            payment = self.client.payment.fetch(payment_id)
            status = payment.get("status")
            if status == "authorized":
                payment = self.client.payment.capture(
                    payment_id,
                    amount_paise,
                    {"currency": payment.get("currency", "INR")},
                )
                break
            if status == "captured":
                break
            if status in {"failed", "refunded"}:
                break
            if attempt < 4:
                time.sleep(1)
        if payment.get("status") != "captured" or not payment.get("captured", False):
            raise RuntimeError(f"Razorpay payment is not captured (status={payment.get('status')}).")
        return payment

    # ── Legacy direct payment API ────────────────────────────────────────────

    def execute_payment(self, order_id: str, amount_paise: int) -> Tuple[str, str]:
        """
                Generates a simulated payment only in demo mode. Live payments must use
                Standard Checkout because Razorpay does not expose a server-side
                `/v1/payments/create/json` endpoint for this flow.
        """
        if not self.client or not self.key_id or not self.key_secret:
            return self._simulated_payment(order_id)

        # Only call the real payment API for real Razorpay orders (not simulated ones)
        if order_id.startswith("order_sim_"):
            return self._simulated_payment(order_id)

        raise RuntimeError(
            "Live Razorpay payments require Standard Checkout. "
            "Create an order, open Checkout, then verify its callback."
        )

    # ── Demo compatibility helper ────────────────────────────────────────────

    def generate_simulated_payment(self, order_id: str) -> Tuple[str, str]:
        """
        Generates a local payment token for simulated demo mode only.
        """
        return self._simulated_payment(order_id)

    # ── Signature Helpers ─────────────────────────────────────────────────────

    def _generate_hmac(self, order_id: str, payment_id: str) -> str:
        msg = f"{order_id}|{payment_id}"
        secret_bytes = (self.key_secret or "simulated_secret").encode("utf-8")
        return hmac.new(secret_bytes, msg.encode("utf-8"), hashlib.sha256).hexdigest()

    def _simulated_payment(self, order_id: str) -> Tuple[str, str]:
        """Locally generates a fake pay_xxx + valid HMAC for demo/test purposes."""
        payment_id = f"pay_{uuid.uuid4().hex[:14]}"
        signature = self._generate_hmac(order_id, payment_id)
        logger.info("Simulated payment generated: %s", payment_id)
        return payment_id, signature

    # ── Payment Verification ──────────────────────────────────────────────────

    def verify_payment_signature(self, verification: PaymentVerification) -> bool:
        """
        Verifies HMAC-SHA256 signature: hmac(order_id|payment_id, key_secret).
        Works for both real Razorpay payments and simulated ones.
        """
        expected = self._generate_hmac(
            verification.razorpay_order_id,
            verification.razorpay_payment_id,
        )
        return hmac.compare_digest(verification.razorpay_signature, expected)
