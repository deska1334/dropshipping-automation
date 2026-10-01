import os
from dataclasses import dataclass, field
from typing import List
from pathlib import Path

# Chargement du fichier .env
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path)
    except ImportError:
        pass

def get_env_bool(key: str, default: bool) -> bool:
    val = os.getenv(key)
    if val is None:
        return default
    return val.strip().lower() in ("true", "1", "yes", "on")

def get_env_float(key: str, default: float) -> float:
    try:
        return float(os.getenv(key, str(default)))
    except ValueError:
        return default

def get_env_int(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, str(default)))
    except ValueError:
        return default

@dataclass
class Config:
    SIMULATION_MODE: bool = get_env_bool("SIMULATION_MODE", True)

    # eBay
    EBAY_ENVIRONMENT: str = os.getenv("EBAY_ENVIRONMENT", "SANDBOX")
    EBAY_APP_ID: str = os.getenv("EBAY_APP_ID", "")
    EBAY_CERT_ID: str = os.getenv("EBAY_CERT_ID", "")
    EBAY_DEV_ID: str = os.getenv("EBAY_DEV_ID", "")
    EBAY_USER_TOKEN: str = os.getenv("EBAY_USER_TOKEN", "")
    EBAY_MARKETPLACE_ID: str = os.getenv("EBAY_MARKETPLACE_ID", "EBAY_FR")

    # Fournisseurs
    AMAZON_PAAPI_KEY: str = os.getenv("AMAZON_PAAPI_KEY", "")
    AMAZON_PAAPI_SECRET: str = os.getenv("AMAZON_PAAPI_SECRET", "")
    AMAZON_ASSOCIATE_TAG: str = os.getenv("AMAZON_ASSOCIATE_TAG", "")
    ALIEXPRESS_APP_KEY: str = os.getenv("ALIEXPRESS_APP_KEY", "")
    ALIEXPRESS_APP_SECRET: str = os.getenv("ALIEXPRESS_APP_SECRET", "")

    # Marges et Frais
    DEFAULT_CURRENCY: str = os.getenv("DEFAULT_CURRENCY", "EUR")
    MIN_PROFIT_MARGIN_PERCENT: float = get_env_float("MIN_PROFIT_MARGIN_PERCENT", 25.0)
    MIN_PROFIT_ABSOLUTE_EUR: float = get_env_float("MIN_PROFIT_ABSOLUTE_EUR", 5.0)
    EBAY_COMMISSION_PERCENT: float = get_env_float("EBAY_COMMISSION_PERCENT", 12.8)
    EBAY_FIXED_FEE_EUR: float = get_env_float("EBAY_FIXED_FEE_EUR", 0.35)
    PAYMENT_PROCESSING_FEE_PERCENT: float = get_env_float("PAYMENT_PROCESSING_FEE_PERCENT", 2.5)
    SAFETY_PRICE_BUFFER_PERCENT: float = get_env_float("SAFETY_PRICE_BUFFER_PERCENT", 5.0)

    # Délais Anti-Ban & Jitter (secondes)
    DELAY_SCRAPE_MIN: float = get_env_float("DELAY_SCRAPE_MIN", 4.0)
    DELAY_SCRAPE_MAX: float = get_env_float("DELAY_SCRAPE_MAX", 12.0)
    DELAY_LISTING_MIN: float = get_env_float("DELAY_LISTING_MIN", 30.0)
    DELAY_LISTING_MAX: float = get_env_float("DELAY_LISTING_MAX", 90.0)
    DELAY_FULFILLMENT_MIN: float = get_env_float("DELAY_FULFILLMENT_MIN", 15.0)
    DELAY_FULFILLMENT_MAX: float = get_env_float("DELAY_FULFILLMENT_MAX", 45.0)

    # Quotas de sécurité
    MAX_LISTINGS_PER_DAY: int = get_env_int("MAX_LISTINGS_PER_DAY", 15)
    MAX_SCRAPES_PER_HOUR: int = get_env_int("MAX_SCRAPES_PER_HOUR", 60)
    CIRCUIT_BREAKER_COOLDOWN_SEC: int = get_env_int("CIRCUIT_BREAKER_COOLDOWN_SEC", 900)

    # Proxies
    PROXIES: List[str] = field(default_factory=lambda: [p.strip() for p in os.getenv("PROXIES", "").split(",") if p.strip()])

cfg = Config()
