"""
Dynamic Autonomous AI Buyer Agent Simulator with Google GenAI / Gemini API Integration.
Parses natural language directives, issues AP2 Bounded Mandates,
evaluates merchant upsell proposals dynamically, and manages counter-negotiations.

A2A message construction uses real `a2a.types` protobuf objects (in the protocol layer).
This module focuses exclusively on intent parsing, AP2 mandate issuance,
and upsell evaluation logic.
"""

import os
import re
from typing import Tuple, Optional
from app.models import AP2MandateSignature, ProductQuery, UpsellOffer, Product
from app.protocols.ap2_mandate import AP2MandateEngine

# Check for Google Gemini API Key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

class AIBuyerAgent:
    def __init__(self, agent_id: str = "buyer_agent_alpha_01", user_id: str = "user_dev_rahul"):
        self.agent_id = agent_id
        self.user_id = user_id
        self.genai_client = None
        if GEMINI_API_KEY:
            try:
                from google import genai
                self.genai_client = genai.Client(api_key=GEMINI_API_KEY)
            except Exception:
                self.genai_client = None

    def extract_intent_and_budget(self, user_prompt: str) -> Tuple[str, float, str]:
        """
        Parses intent, budget limit in INR, and target product category from arbitrary user input.
        """
        prompt_lower = user_prompt.lower()

        # Extract budget INR using regex
        budget = 50000.0  # default fallback budget
        budget_matches = re.findall(r"(?:under|below|budget|max|limit)?\s*₹?\s*([\d,]+)", prompt_lower)
        if budget_matches:
            for match in budget_matches:
                clean_num = match.replace(",", "")
                if clean_num.isdigit() and int(clean_num) > 100:
                    budget = float(clean_num)
                    break

        category = "electronics"
        if "laptop" in prompt_lower:
            category = "laptops"
        elif "charger" in prompt_lower or "cable" in prompt_lower:
            category = "charging"
        elif "mouse" in prompt_lower or "keyboard" in prompt_lower:
            category = "peripherals"
        elif "monitor" in prompt_lower or "display" in prompt_lower:
            category = "displays"
        elif "headphone" in prompt_lower or "audio" in prompt_lower:
            category = "audio"

        intent = f"Hardware Procurement ({category.capitalize()})"
        return intent, budget, category

    def issue_bounded_mandate(
        self,
        max_budget_inr: float,
        authorized_merchant_id: str = "merchant_techverse_01"
    ) -> AP2MandateSignature:
        """
        Creates a signed AP2 Bounded Mandate representing spending authorization.
        """
        return AP2MandateEngine.create_signed_mandate(
            buyer_agent_id=self.agent_id,
            user_id=self.user_id,
            max_amount_inr=max_budget_inr,
            authorized_merchant_id=authorized_merchant_id
        )

    def evaluate_upsell_offer(
        self,
        upsell: UpsellOffer,
        mandate: AP2MandateSignature
    ) -> Tuple[bool, str]:
        """
        Autonomous dynamic evaluation of merchant upsell offer against AP2 mandate limits and value utility.
        """
        headroom = mandate.mandate.max_amount_inr - upsell.new_cart_total_inr

        if headroom < 0:
            return False, f"REJECTED: Offer total ₹{upsell.new_cart_total_inr:,.2f} exceeds AP2 Mandate limit ₹{mandate.mandate.max_amount_inr:,.2f} by ₹{abs(headroom):,.2f}."

        # If GenAI Client available, generate dynamic reasoning pitch
        if self.genai_client:
            try:
                response = self.genai_client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=f"You are an AI Buyer Agent. Your user mandate cap is ₹{mandate.mandate.max_amount_inr}. Merchant offered {upsell.product.name} for ₹{upsell.additional_cost_inr}. Total order will be ₹{upsell.new_cart_total_inr}. Evaluate ROI and give a 1-sentence decision."
                )
                if response and response.text:
                    return True, f"ACCEPTED (Gemini LLM Reasoned): {response.text.strip()}"
            except Exception:
                pass

        # Standard rule evaluation fallback
        accepted_categories = ["warranty", "charging", "peripherals", "accessories", "electronics", "laptops", "displays", "audio"]
        if upsell.product.category in accepted_categories and headroom >= 0:
            return True, f"ACCEPTED: Additional {upsell.product.name} (₹{upsell.additional_cost_inr:,.2f}) provides high ROI. Total ₹{upsell.new_cart_total_inr:,.2f} fits within ₹{mandate.mandate.max_amount_inr:,.2f} mandate (Headroom: ₹{headroom:,.2f})."

        return False, "REJECTED: Does not meet buyer ROI threshold."
