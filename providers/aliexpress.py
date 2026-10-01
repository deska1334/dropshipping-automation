import random
import logging
from typing import List, Dict, Any, Optional
from config import cfg
from stealth import stealth
from providers.base import BaseProvider, SourcedProduct, PurchaseResult

logger = logging.getLogger("AliExpressProvider")

class AliExpressProvider(BaseProvider):
    name = "aliexpress"

    def search_products(self, query: str, limit: int = 5) -> List[SourcedProduct]:
        stealth.delay_for_scraping("aliexpress")
        
        mock_catalog = [
            SourcedProduct(
                provider="aliexpress",
                source_id="10050063214589",
                source_url="https://fr.aliexpress.com/item/10050063214589.html",
                title=f"Montre Connectée Sport Smartwatch Écran HD Cardio ({query})",
                description="Capteur fréquence cardiaque, étanche IP68, autonomie 10 jours, iOS/Android.",
                price_eur=12.40,
                shipping_eur=1.99, # AliExpress Standard Shipping
                in_stock=True,
                category="Montres",
                images=["https://ae01.alicdn.com/kf/S1.jpg"]
            ),
            SourcedProduct(
                provider="aliexpress",
                source_id="10050058741230",
                source_url="https://fr.aliexpress.com/item/10050058741230.html",
                title=f"Lampe LED Solaire Extérieure Détecteur Mouvement ({query})",
                description="Éclairage puissant jardin, étanche IP65, panneau solaire monocristallin.",
                price_eur=6.20,
                shipping_eur=0.90,
                in_stock=True,
                category="Maison & Jardin",
                images=["https://ae01.alicdn.com/kf/S2.jpg"]
            )
        ]
        return mock_catalog[:limit]

    def get_product_details(self, source_id: str) -> Optional[SourcedProduct]:
        stealth.delay_for_scraping("aliexpress")
        return SourcedProduct(
            provider="aliexpress",
            source_id=source_id,
            source_url=f"https://fr.aliexpress.com/item/{source_id}.html",
            title="Article AliExpress Vérifié",
            description="Description détaillée de l'article AliExpress.",
            price_eur=12.40,
            shipping_eur=1.99,
            in_stock=True,
            category="Général",
            images=["https://ae01.alicdn.com/kf/sample.jpg"]
        )

    def order_and_ship(self, source_id: str, quantity: int, shipping_address: Dict[str, Any]) -> PurchaseResult:
        stealth.delay_for_fulfillment("aliexpress")
        
        recipient = shipping_address.get("name", "Client")
        street = shipping_address.get("street1", "")
        city = shipping_address.get("city", "")
        postal_code = shipping_address.get("postal_code", "")
        country = shipping_address.get("country_code", "FR")
        
        order_num = f"818{random.randint(10000000000, 99999999999)}"
        simulated_cost = round((12.40 + 1.99) * quantity, 2)
        
        logger.info(
            f"[COMMANDE FOURNISSEUR ALIEXPRESS] Commande passée avec succès !\n"
            f"  -> Réf Commande : {order_num}\n"
            f"  -> Expédition à : {recipient}, {street}, {postal_code} {city} ({country})\n"
            f"  -> Coût Total   : {simulated_cost} €"
        )
        
        return PurchaseResult(
            success=True,
            source_order_id=order_num,
            total_charged_eur=simulated_cost,
            estimated_delivery="Sous 7 à 12 jours (AliExpress Standard Shipping)"
        )
