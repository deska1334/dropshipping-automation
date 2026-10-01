import time
import random
import logging
from typing import Dict, Optional, List
from config import cfg

logger = logging.getLogger("StealthManager")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36 Edg/127.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:130.0) Gecko/20100101 Firefox/130.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_6_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
]

class CircuitBreakerException(Exception):
    pass

class StealthManager:
    """
    Gestionnaire anti-detection centralise :
    - Pauses humaines gaussiennes (Jitter non lineaire)
    - Persistance SQLite des quotas journaliers et horaires (resiste aux arrets du script)
    - Rotation d'en-tetes navigateurs modernes
    - Coupe-circuit automatique en cas de CAPTCHA / 429 / 403
    """
    def __init__(self):
        self.circuit_tripped: Dict[str, float] = {}

    def get_random_headers(self, referer: Optional[str] = None) -> Dict[str, str]:
        ua = random.choice(USER_AGENTS)
        is_chrome = "Chrome" in ua
        
        headers = {
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        if is_chrome:
            headers["Sec-CH-UA"] = '"Chromium";v="128", "Not;A=Brand";v="24", "Google Chrome";v="128"'
            headers["Sec-CH-UA-Mobile"] = "?0"
            headers["Sec-CH-UA-Platform"] = '"Windows"'
            headers["Sec-Fetch-Dest"] = "document"
            headers["Sec-Fetch-Mode"] = "navigate"
            headers["Sec-Fetch-Site"] = "none" if not referer else "cross-site"
            headers["Sec-Fetch-User"] = "?1"
        
        if referer:
            headers["Referer"] = referer
            
        return headers

    def jitter_delay(self, min_sec: float, max_sec: float, action_desc: str = "Operation") -> float:
        mean = (min_sec + max_sec) / 2.0
        std_dev = (max_sec - min_sec) / 6.0
        delay = random.gauss(mean, std_dev)
        delay = max(min_sec, min(delay, max_sec))
        delay += random.uniform(0.05, 0.4)
        
        logger.info(f"[ANTI-BAN] Pause de temporisation ({action_desc}): {delay:.2f}s...")
        time.sleep(delay)
        return delay

    def delay_for_scraping(self, platform: str = "Fournisseur") -> float:
        self.check_circuit_breaker(platform)
        self._enforce_hourly_scrape_limit(platform)
        return self.jitter_delay(cfg.DELAY_SCRAPE_MIN, cfg.DELAY_SCRAPE_MAX, f"Recherche {platform}")

    def delay_for_listing(self) -> float:
        self.check_circuit_breaker("ebay")
        self._enforce_daily_listing_limit()
        return self.jitter_delay(cfg.DELAY_LISTING_MIN, cfg.DELAY_LISTING_MAX, "Publication eBay")

    def delay_for_fulfillment(self, supplier: str = "Fournisseur") -> float:
        self.check_circuit_breaker(supplier)
        return self.jitter_delay(cfg.DELAY_FULFILLMENT_MIN, cfg.DELAY_FULFILLMENT_MAX, f"Achat auto {supplier}")

    def check_circuit_breaker(self, platform: str):
        trip_time = self.circuit_tripped.get(platform)
        if trip_time:
            elapsed = time.time() - trip_time
            if elapsed < cfg.CIRCUIT_BREAKER_COOLDOWN_SEC:
                remaining = int(cfg.CIRCUIT_BREAKER_COOLDOWN_SEC - elapsed)
                raise CircuitBreakerException(
                    f"Coupe-circuit actif pour '{platform}' suite a detection de blocage/CAPTCHA. "
                    f"Cooldown restant: {remaining}s pour proteger votre compte."
                )
            else:
                del self.circuit_tripped[platform]
                logger.info(f"[ANTI-BAN] Coupe-circuit rearme pour '{platform}'. Reprise normale.")

    def trip_circuit_breaker(self, platform: str, reason: str):
        self.circuit_tripped[platform] = time.time()
        logger.error(
            f"[ALERTE ANTI-BAN] Declenchement coupe-circuit pour '{platform}'! Raison: {reason}. "
            f"Requêtes suspendues pendant {cfg.CIRCUIT_BREAKER_COOLDOWN_SEC}s."
        )

    def _enforce_hourly_scrape_limit(self, platform: str):
        from database import count_recent_scrapes, log_activity
        scrapes_in_last_hour = count_recent_scrapes(platform, hours=1)
        if scrapes_in_last_hour >= cfg.MAX_SCRAPES_PER_HOUR:
            wait_sec = 60.0
            logger.warning(
                f"[ANTI-BAN] Quota horaire atteint pour {platform} ({scrapes_in_last_hour}/{cfg.MAX_SCRAPES_PER_HOUR}). "
                f"Pause de securite obligatoire de {wait_sec}s."
            )
            time.sleep(wait_sec)
        log_activity("INFO", f"scrape_{platform}", f"Requete de sourcage sur {platform}")

    def _enforce_daily_listing_limit(self):
        from database import count_recent_listings
        listings_24h = count_recent_listings(hours=24)
        if listings_24h >= cfg.MAX_LISTINGS_PER_DAY:
            raise PermissionError(
                f"[ANTI-BAN] Quota journalier atteint ({listings_24h}/{cfg.MAX_LISTINGS_PER_DAY} annonces/24h). "
                "Publier davantage sur un compte eBay risque de declencher une suspension de compte MC011."
            )

stealth = StealthManager()
