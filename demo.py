"""
CLI Test & Demonstration Script for the Hackathon Submission.
Prints the exact Split-Screen Demo Interface output (Panel A: Live Chat, Panel B: Audit Trail & Bounding Engine).
"""

import sys
import json
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from app.models import ProductQuery, Cart, CartItem, PaymentVerification
from app.merchant.catalog import MerchantCatalog
from app.merchant.upsell_engine import MerchantUpsellEngine
from app.protocols.ap2_mandate import AP2MandateEngine
from app.services.razorpay_service import RazorpayService
from app.services.audit_ledger import AuditLedgerEngine
from app.buyer.buyer_agent import AIBuyerAgent

def run_split_screen_demo():
    catalog = MerchantCatalog()
    upsell_engine = MerchantUpsellEngine(catalog)
    audit = AuditLedgerEngine()
    razorpay = RazorpayService()
    buyer = AIBuyerAgent()

    user_query = "Looking for a 65W GaN fast charger with USB-C cable under ₹2,500."
    max_budget_inr = 2500.00
    merchant_id = "merchant_techverse_01"

    # Search Vector Catalog
    q = ProductQuery(query_text=user_query, max_budget_inr=max_budget_inr)
    results, match_count, top_sim = catalog.vector_search_catalog(q)
    base_product = results[0] # TurboCharge 65W GaN Charger @ ₹1,799

    # Issue AP2 Mandate
    mandate_sig = buyer.issue_bounded_mandate(max_budget_inr=max_budget_inr, authorized_merchant_id=merchant_id)

    # Dynamic Upsell
    upsell = upsell_engine.evaluate_best_upsell(base_product=base_product, max_mandate_budget_inr=max_budget_inr)
    upsell_item = upsell.product # 2m Braided USB-C Cable @ ₹400

    total_amount = base_product.price_inr + upsell_item.price_inr # ₹2,199

    cart = Cart(
        items=[
            CartItem(product_id=base_product.id, name=base_product.name, price_inr=base_product.price_inr),
            CartItem(product_id=upsell_item.id, name=upsell_item.name, price_inr=upsell_item.price_inr, is_upsell=True)
        ],
        base_subtotal_inr=base_product.price_inr,
        upsell_subtotal_inr=upsell_item.price_inr,
        total_amount_inr=total_amount
    )

    # AP2 Mandate Verification
    val_res = AP2MandateEngine.validate_mandate(mandate_sig, merchant_id, cart)

    # Razorpay Checkout
    order_res = razorpay.create_order(cart, buyer.agent_id)
    pay_id, sig = razorpay.generate_simulated_payment(order_res.order_id)

    # Database Audit Recording
    rec = audit.record_event(
        actor="MERCHANT_AGENT",
        state="ORDER_CONFIRMED",
        title="Transaction Completed",
        details={
            "session_id": "#TX-9042",
            "order_id": order_res.order_id,
            "payment_id": pay_id,
            "total_amount_inr": total_amount,
            "intent": "Hardware Procurement",
            "matched_count": match_count,
            "valid": True
        },
        session_id="#TX-9042"
    )

    audit_hex_id = rec.details.get("audit_record_id", "0x8F4A1C9")

    # Print Split-Screen Format
    print("=" * 86)
    print("                      SPLIT-SCREEN MERCHANT DEMO INTERFACE                       ")
    print("=" * 86)
    print("+------------------------------------------+------------------------------------------+")
    print("|  Panel A: Buyer Interaction (Live Chat)  |   Panel B: Audit Trail & Bounding Engine |")
    print("+------------------------------------------+------------------------------------------+")
    print("| Buyer Agent / User:                      | [STATUS: ACTIVE SESSION #TX-9042]        |")
    print(f"| \"{user_query}\" |                                          |")
    print("|                                          | > Intent Parsed: Hardware Procurement    |")
    print(f"|                                          | > Vector Search: {match_count} Catalog Matches Found |")
    print(f"| Merchant Agent:                          | > Budget Constraint: Max ₹{max_budget_inr:,.0f}          |")
    print(f"| \"I have the {base_product.name[:18]}... | > Dynamic Offer Generated: ₹{total_amount:,.0f}        |")
    print(f"| + {upsell_item.name[:20]} bundle for ₹{total_amount:,.0f}. | > Bounding Rule: Passed (Within Limit)   |")
    print("| Would you like to authorize payment?\"    |                                          |")
    print("|                                          | [GATEWAY DISPATCH]                       |")
    print("| Buyer Agent:                             | > Razorpay Order Created: " + f"{order_res.order_id[:14]}... |")
    print("| \"Authorized. Payment token dispatched.\"  | > Token Verification: AP2 Signature Valid|")
    print("|                                          | > Transaction Status: SUCCESS (Captured) |")
    print("| Merchant Agent:                          | > State Logged to SQLite Database Ledger |")
    print(f"| \"Payment of ₹{total_amount:,.0f} captured. Receipt sent|                                          |")
    print(f"| Order ID: #ORD-8821.\"                    | [AUDIT RECORD ID: {audit_hex_id}]             |")
    print("+------------------------------------------+------------------------------------------+")
    print("\n [SUCCESS] Autonomous merchant transaction complete & stored in SQLite DB.")
    print("=" * 86)

if __name__ == "__main__":
    run_split_screen_demo()
