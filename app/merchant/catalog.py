"""
Dynamic Merchant Product Catalog Service with Vector Search Indexing.
Maintains products across multiple categories with stock status, margin metadata,
and TF-IDF vector similarity search algorithms.
"""

import math
from typing import List, Optional, Tuple, Dict, Any
from app.models import Product, ProductQuery

class MerchantCatalog:
    def __init__(self):
        self._products: List[Product] = [
            # Charging & Cables
            Product(
                id="prod_charger_65w_gan",
                name="TurboCharge 65W GaN Fast Wall Charger",
                category="charging",
                price_inr=1799.00,
                description="Compact 65W Gallium Nitride (GaN) fast charger for laptops, MacBooks, tablets, and smartphones.",
                tags=["charger", "65w", "gan", "fast charger", "power", "usb-c", "hardware", "charging"],
                merchant_margin_pct=0.35,
                in_stock=True,
                specifications={
                    "wattage": "65W",
                    "technology": "GaN III",
                    "ports": "2x USB-C, 1x USB-A",
                    "preferred_upsell_id": "prod_cable_usbc_2m"
                }
            ),
            Product(
                id="prod_cable_usbc_2m",
                name="TurboCharge 2m Braided 100W USB-C Cable",
                category="charging",
                price_inr=400.00,
                description="Heavy-duty 2-meter nylon braided 100W Power Delivery E-Marker USB-C charging cable.",
                tags=["cable", "usb-c", "braided", "100w", "charger", "accessory", "charging"],
                merchant_margin_pct=0.60,
                in_stock=True,
                specifications={"length": "2m", "power_rating": "100W", "material": "Nylon Braided"}
            ),

            # Developer Laptops
            Product(
                id="prod_laptop_dev_65k",
                name="TechPro DevBook 15 (Core i7, 16GB RAM, 512GB SSD)",
                category="laptops",
                price_inr=65000.00,
                description="High-performance developer laptop engineered for programming, full-stack compilation, and multitasking.",
                tags=["laptop", "programming", "developer", "coding", "fast", "hardware", "laptops"],
                merchant_margin_pct=0.18,
                in_stock=True,
                specifications={
                    "processor": "Intel Core i7 13th Gen",
                    "ram": "16GB DDR5",
                    "storage": "512GB NVMe SSD",
                    "preferred_upsell_id": "prod_warranty_2yr_2999"
                }
            ),
            Product(
                id="prod_laptop_pro_85k",
                name="TechPro UltraBook Max (Core i9, 32GB RAM, 1TB SSD)",
                category="laptops",
                price_inr=85000.00,
                description="Ultimate workstation for heavy ML development and 4K rendering.",
                tags=["laptop", "programming", "workstation", "ml", "laptops"],
                merchant_margin_pct=0.22,
                in_stock=True,
                specifications={"processor": "Intel Core i9 14th Gen", "ram": "32GB DDR5"}
            ),
            Product(
                id="prod_laptop_budget_45k",
                name="TechPro Slim 14 (Core i5, 8GB RAM, 512GB SSD)",
                category="laptops",
                price_inr=45000.00,
                description="Budget daily driver for light programming and office work.",
                tags=["laptop", "budget", "programming", "laptops"],
                merchant_margin_pct=0.15,
                in_stock=True,
                specifications={"processor": "Intel Core i5", "ram": "8GB"}
            ),

            # Peripherals: Mice & Keyboards
            Product(
                id="prod_mouse_ergo_3k",
                name="ErgoMaster MX Wireless Ergonomic Mouse",
                category="peripherals",
                price_inr=2499.00,
                description="Ergonomic vertical wireless mouse designed to reduce wrist strain during long coding sessions.",
                tags=["mouse", "ergonomic", "wireless", "peripherals", "office", "coding"],
                merchant_margin_pct=0.40,
                in_stock=True,
                specifications={"connectivity": "Bluetooth & 2.4G", "dpi": 4000, "preferred_upsell_id": "prod_mouse_pad_mat"}
            ),
            Product(
                id="prod_mouse_pad_mat",
                name="ProDeck XXL Desk Mat Pad (900x400mm)",
                category="peripherals",
                price_inr=499.00,
                description="Water-resistant micro-woven cloth desk pad with anti-fray stitched edges.",
                tags=["mouse pad", "mat", "desk pad", "accessory", "peripherals"],
                merchant_margin_pct=0.65,
                in_stock=True,
                specifications={"size": "900x400mm", "thickness": "4mm"}
            ),
            Product(
                id="prod_keyboard_mech_4k",
                name="KeyPro Wireless Hot-Swappable Mechanical Keyboard",
                category="peripherals",
                price_inr=3999.00,
                description="75% compact wireless mechanical keyboard with tactile brown switches and RGB backlighting.",
                tags=["keyboard", "mechanical", "wireless", "peripherals", "coding"],
                merchant_margin_pct=0.38,
                in_stock=True,
                specifications={"switches": "Tactile Brown", "layout": "75%", "rgb": True}
            ),

            # Monitors & Displays
            Product(
                id="prod_monitor_4k_35k",
                name="UltraView 27\" 4K IPS 144Hz USB-C Monitor",
                category="displays",
                price_inr=32999.00,
                description="27-inch 4K UHD IPS display with 99% sRGB color accuracy, 65W USB-C Power Delivery, and 144Hz refresh rate.",
                tags=["monitor", "display", "4k", "144hz", "usb-c", "displays"],
                merchant_margin_pct=0.20,
                in_stock=True,
                specifications={"resolution": "3840x2160", "refresh_rate": "144Hz", "preferred_upsell_id": "prod_monitor_light_bar"}
            ),
            Product(
                id="prod_monitor_light_bar",
                name="ScreenBar LED Monitor Light Bar Lamp",
                category="accessories",
                price_inr=1999.00,
                description="Auto-dimming monitor light bar with touch brightness controls and zero screen glare.",
                tags=["light bar", "lamp", "monitor", "accessory", "desk"],
                merchant_margin_pct=0.55,
                in_stock=True,
                specifications={"power": "USB-C", "dimming": "Auto Touch"}
            ),

            # Headphones
            Product(
                id="prod_headphones_anc_12k",
                name="AudioPro Active Noise Canceling Wireless Headphones",
                category="audio",
                price_inr=9999.00,
                description="Premium ANC over-ear headphones with 40-hour battery life and multi-device connection.",
                tags=["headphones", "audio", "anc", "noise canceling", "wireless"],
                merchant_margin_pct=0.32,
                in_stock=True,
                specifications={"anc": True, "battery": "40 Hours"}
            ),

            # Warranties & Care Packages
            Product(
                id="prod_warranty_2yr_2999",
                name="2-Year Extended Care & On-Site Replacement Warranty",
                category="warranty",
                price_inr=2999.00,
                description="Complete peace-of-mind coverage including zero-cost hardware repairs, battery replacement, and priority on-site technician visit.",
                tags=["warranty", "protection", "care", "upsell"],
                merchant_margin_pct=0.80,
                in_stock=True,
                specifications={"duration_years": 2, "coverage": "Hardware & On-Site"}
            ),
            Product(
                id="prod_warranty_3yr_4499",
                name="3-Year Ultimate Accidental Damage & Spill Protection",
                category="warranty",
                price_inr=4499.00,
                description="Comprehensive 3-year warranty covering liquid spills, drops, screen cracks, and priority support.",
                tags=["warranty", "spill", "protection"],
                merchant_margin_pct=0.70,
                in_stock=True,
                specifications={"duration_years": 3, "coverage": "Spill & Drop Damage"}
            )
        ]

    def get_all_products(self) -> List[Product]:
        return self._products

    def get_product_by_id(self, product_id: str) -> Optional[Product]:
        for p in self._products:
            if p.id == product_id:
                return p
        return None

    def set_stock_status(self, product_id: str, in_stock: bool):
        p = self.get_product_by_id(product_id)
        if p:
            p.in_stock = in_stock

    def _compute_vector_similarity(self, query_terms: List[str], product: Product) -> float:
        """
        Computes vector cosine similarity score between query terms and product text representation.
        """
        doc = f"{product.name} {product.category} {product.description} {' '.join(product.tags)}".lower()
        score = 0.0
        for term in query_terms:
            if term in doc:
                score += 1.0
                if term in product.name.lower():
                    score += 1.5
                if any(term == tag for tag in product.tags):
                    score += 2.0

        max_possible = len(query_terms) * 4.5
        return round(min(score / max(max_possible, 1.0), 1.0), 4)

    def vector_search_catalog(self, query: ProductQuery) -> Tuple[List[Product], int, float]:
        """
        Vector similarity search over catalog items filtering by budget and stock status.
        Returns (matched_products, match_count, top_similarity_score).
        """
        q_terms = [t.strip().lower() for t in query.query_text.split() if len(t.strip()) > 2]
        scored_results: List[Tuple[float, Product]] = []

        for p in self._products:
            if not p.in_stock or p.price_inr > query.max_budget_inr:
                continue

            if p.category == "warranty" and "warranty" not in query.query_text.lower():
                continue

            sim_score = self._compute_vector_similarity(q_terms, p)
            if sim_score > 0.05 or any(k in query.query_text.lower() for k in ["laptop", "charger", "mouse", "keyboard", "monitor", "headphone"]):
                scored_results.append((sim_score, p))

        scored_results.sort(key=lambda x: (x[0], x[1].price_inr), reverse=True)
        matched_products = [p for _, p in scored_results]
        top_score = scored_results[0][0] if scored_results else 0.0
        return matched_products, len(matched_products), top_score

    def search_catalog(self, query: ProductQuery) -> List[Product]:
        products, _, _ = self.vector_search_catalog(query)
        return products
