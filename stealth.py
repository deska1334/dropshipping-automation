import time
import random
import logging
from typing import Dict, Optional, List
from config import cfg

logger = logging.getLogger("StealthManager")

# Pool d'empreintes User-Agent réalistes et modernes (Windows, Mac, Linux)
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
    Système centralisé anti-détection et gestionnaire de risques de bannissement.
    - Injection de pauses aléatoires à distribution gaussienne (Jitter humain).
    - Rotation dynamique de User-Agents et headers HTTP réalistes.
    - Limiteur de débit glissant (Rate Limiting) par minute, heure et jour.
    - Coupe-circuit (Circuit Breaker) en cas de détection CAPTCHA / 429 / 403.
    """
    def __init__(self):
        self.circuit_tripped: Dict[str, float] = {} # platform -> timestamp release
        self.hourly_actions: Dict[str, List[float]] = {}
        self.daily_listings: List[float] = []

    def get_random_headers(self, referer: Optional[str] = None) -> Dict[str, str]:
        """Génère des en-têtes HTTP réalistes conformes aux navigateurs actuels."""
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

    def jitter_delay(self, min_sec: float, max_sec: float, action_desc: str = "Opération") -> float:
        """
        Génère une pause temporisée non linéaire (loi normale tronquée)
        pour casser les signatures d'automates temporels prévisibles.
        """
        # Moyenne et écart-type centrés
        mean = (min_sec + max_sec) / 2.0
        std_dev = (max_sec - min_sec) / 6.0
        delay = random.gauss(mean, std_dev)
        delay = max(min_sec, min(delay, max_sec)) # Clamp
        
        # Ajout d'un micro-bruit aléatoire supplémentaire
        delay += random.uniform(0.05, 0.4)
        
        logger.info(f"[ANTI-BAN] Pause de temporisation ({action_desc}): {delay:.2f}s...")
        time.sleep(delay)
        return delay

    def delay_for_scraping(self, platform: str = "Fournisseur") -> float:
        self.check_circuit_breaker(platform)
        self._record_hourly_action(f"scrape_{platform}")
        return self.jitter_delay(cfg.DELAY_SCRAPE_MIN, cfg.DELAY_SCRAPE_MAX, f"Recherche {platform}")

    def delay_for_listing(self) -> float:
        self.check_circuit_breaker("ebay")
        self._enforce_daily_listing_limit()
        return self.jitter_delay(cfg.DELAY_LISTING_MIN, cfg.DELAY_LISTING_MAX, "Publication eBay")

    def delay_for_fulfillment(self, supplier: str = "Fournisseur") -> float:
        self.check_circuit_breaker(supplier)
        return self.jitter_delay(cfg.DELAY_FULFILLMENT_MIN, cfg.DELAY_FULFILLMENT_MAX, f"Achat auto {supplier}")

    def exponential_backoff(self, attempt: int, base: float = 6.0, max_delay: float = 300.0) -> float:
        """Calcul de recul exponentiel avec gigue lors de codes HTTP 429 / 503."""
        delay = min(max_delay, base * (2 ** attempt))
        delay += random.uniform(1.0, 5.0)
        logger.warning(f"[ANTI-BAN] Recul exponentiel (Tentative {attempt}): attente de {delay:.1f}s")
        time.sleep(delay)
        return delay

    def check_circuit_breaker(self, platform: str):
        """Vérifie si la plateforme est actuellement sous cooldown suite à une anomalie."""
        trip_time = self.circuit_tripped.get(platform)
        if trip_time:
            elapsed = time.time() - trip_time
            if elapsed < cfg.CIRCUIT_BREAKER_COOLDOWN_SEC:
                remaining = int(cfg.CIRCUIT_BREAKER_COOLDOWN_SEC - elapsed)
                raise CircuitBreakerException(
                    f"Coupe-circuit actif pour '{platform}' suite à détection de blocage/CAPTCHA. "
                    f"Cooldown restant: {remaining} secondes pour protéger votre compte."
                )
            else:
                del self.circuit_tripped[platform]
                logger.info(f"[ANTI-BAN] Coupe-circuit réarmé pour '{platform}'. Reprise normale.")

    def trip_circuit_breaker(self, platform: str, reason: str):
        """Active le coupe-circuit pour geler immédiatement les requêtes et éviter le ban définitif."""
        self.circuit_tripped[platform] = time.time()
        logger.error(
            f"[ALERTE ANTI-BAN] Déclenchement coupe-circuit pour '{platform}'! Raison: {reason}. "
            f"Toutes les requêtes vers cette plateforme sont suspendues pendant {cfg.CIRCUIT_BREAKER_COOLDOWN_SEC}s."
        )

    def _record_hourly_action(self, action_key: str):
        now = time.time()
        one_hour_ago = now - 3600
        history = self.hourly_actions.setdefault(action_key, [])
        history[:] = [t for t in history if t > one_hour_ago]
        
        if len(history) >= cfg.MAX_SCRAPES_PER_HOUR:
            wait_time = 3600 - (now - history[0])
            logger.warning(f"[ANTI-BAN] Quota horaire atteint pour {action_key} ({cfg.MAX_SCRAPES_PER_HOUR}/h). Pause de sécurité de {wait_time:.1f}s.")
            time.sleep(max(5.0, wait_time))
        
        history.append(now)

    def _enforce_daily_listing_limit(self):
        now = time.time()
        one_day_ago = now - 86400
        self.daily_listings[:] = [t for t in self.daily_listings if t > one_day_ago]
        
        if len(self.daily_listings) >= cfg.MAX_LISTINGS_PER_DAY:
            raise PermissionError(
                f"[ANTI-BAN] Limite de sécurité journalière atteinte ({cfg.MAX_LISTINGS_PER_DAY} annonces/24h). "
                "Publier davantage sur un compte non-wholeseller déclenche des revues manuelles et suspensions eBay."
            )
        self.daily_listings.append(now)

stealth = StealthManager()
