"""
Centralised application configuration using pydantic-settings.
All secrets are loaded from the .env file at the project root.

Usage anywhere in the project:
    from app.config import settings
    settings.GEMINI_API_KEY
    settings.is_razorpay_configured()
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── Razorpay ─────────────────────────────────────────────────────────────
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""

    # ── Google AI (Gemini) ────────────────────────────────────────────────────
    GEMINI_API_KEY: str = ""

    # ── Agent Network ─────────────────────────────────────────────────────────
    MERCHANT_AGENT_URL: str = "http://localhost:8000"
    BUYER_AGENT_URL: str = "http://localhost:8001"
    MERCHANT_AGENT_PORT: int = 8000
    BUYER_AGENT_PORT: int = 8001

    # ── AP2 Mandate Cryptography ──────────────────────────────────────────────
    AP2_MANDATE_SECRET: str = "AP2_MANDATE_SECRET_AUTHORIZATION_KEY_2026"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Helpers ───────────────────────────────────────────────────────────────

    def is_razorpay_configured(self) -> bool:
        """True when real (non-placeholder) Razorpay test keys are present."""
        return bool(
            self.RAZORPAY_KEY_ID
            and self.RAZORPAY_KEY_SECRET
            and self.RAZORPAY_KEY_ID.startswith("rzp_test_")
            and not self.RAZORPAY_KEY_ID.startswith("rzp_test_MerchantAgent")
        )

    def is_gemini_configured(self) -> bool:
        """True when a real Gemini API key is set."""
        return bool(self.GEMINI_API_KEY and len(self.GEMINI_API_KEY) > 10)

    def get_missing_keys(self) -> list[str]:
        """Returns a list of keys that are not properly configured."""
        missing: list[str] = []
        if not self.is_gemini_configured():
            missing.append("GEMINI_API_KEY")
        if not self.is_razorpay_configured():
            missing.append("RAZORPAY_KEY_ID + RAZORPAY_KEY_SECRET")
        return missing

    def razorpay_mode(self) -> str:
        return "live" if self.is_razorpay_configured() else "simulated"

    def gemini_mode(self) -> str:
        return "live" if self.is_gemini_configured() else "unavailable"

    def ap2_secret(self) -> str:
        return self.AP2_MANDATE_SECRET


@lru_cache
def get_settings() -> Settings:
    return Settings()


# Singleton — import this everywhere
settings = get_settings()
