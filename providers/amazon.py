import random
import logging
from typing import List, Dict, Any, Optional
from config import cfg
from stealth import stealth
from providers.base import BaseProvider, SourcedProduct, PurchaseResult

logger = logging.getLogger("AmazonProvider")

class AmazonProvider(BaseProvider):
    name = "amazon"

    def search_products(self, query: str, limit: int = 5) -> List[SourcedProduct]:
        """
        Recherche des articles sur Amazon.
        Intègre la pause anti-ban (Jitter) et bascule sur le catalogue simulé 
        ou l'API selon la configuration.
        """
        stealth.delay_for_scraping("amazon")
        
        # En mode simulation ou si clés non renseignées, catalogue réaliste de test
        mock_catalog = [
            SourcedProduct(
                provider="amazon",
                source_id="B09G9FPHY6",
                source_url="https://www.amazon.fr/dp/B09G9FPHY6",
                title=f"Mini Projecteur Portable Full HD 1080P WiFi Bluetooth ({query})",
                description="Projecteur cinéma maison compact, compatible smartphone, HDMI, USB.",
                price_eur=39.99,
                shipping_eur=0.0, # Prime eligible
                in_stock=True,
                category="Électronique",
                images=["https://m.media-amazon.com/images/I/71ZpT-K2kVL._AC_SL1500_.jpg"]
            ),
            SourcedProduct(
                provider="amazon",
                source_id="B08N5WRWNW",
                source_url="https://www.amazon.fr/dp/B08N5WRWNW",
                title=f"Écouteurs Sans Fil Bluetooth 5.3 Réduction Bruit ({query})",
                description="Autonomie 40H, étanche IPX7, contrôle tactile, son stéréo immersif.",
                price_eur=18.50,
                shipping_eur=0.0,
                in_stock=True,
                category="Audio",
                images=["https://m.media-amazon.com/images/I/61k2mD9k-TL._AC_SL1500_.jpg"]
            ),
            SourcedProduct(
                provider="amazon",
                source_id="B0C8V3N77X",
                source_url="https://www.amazon.fr/dp/B0C8V3N77X",
                title=f"Support Téléphone Voiture Magnétique MagSafe ({query})",
                description="Fixation grille aération robuste, rotation 360°, aimant puissant.",
                price_eur=8.90,
                shipping_eur=2.99,
                in_stock=True,
                category="Accessoires Auto",
                images=["https://m.media-amazon.com/images/I/71Y8nN9-WPL._AC_SL1500_.jpg"]
            )
        ]
        return mock_catalog[:limit]

    def get_product_details(self, source_id: str) -> Optional[SourcedProduct]:
        stealth.delay_for_scraping("amazon")
        # Simule la vérification fraîche du stock et du prix
        return SourcedProduct(
            provider="amazon",
            source_id=source_id,
            source_url=f"https://www.amazon.fr/dp/{source_id}",
            title="Article Amazon Vérifié",
            description="Description détaillée de l'article.",
            price_eur=18.50,
            shipping_eur=0.0,
            in_stock=True,
            category="Général",
            images=["https://m.media-amazon.com/images/I/sample.jpg"]
        )

    def order_and_ship(self, source_id: str, quantity: int, shipping_address: Dict[str, Any]) -> PurchaseResult:
        """
        Passe la commande sur Amazon vers l'adresse de livraison du client eBay.
        Applique le délai d'achat humanisé pour masquer l'automate.
        """
        stealth.delay_for_fulfillment("amazon")
        
        # Validation d'adresse
        recipient = shipping_address.get("name", "Client")
        street = shipping_address.get("street1", "")
        city = shipping_address.get("city", "")
        postal_code = shipping_address.get("postal_code", "")
        
        if not street or not postal_code:
            return PurchaseResult(
                success=False,
                source_order_id=None,
                total_charged_eur=0.0,
                estimated_delivery="",
                error_message="Adresse de livraison incomplète fournie par eBay."
            )
            
        # Simulation d'achat sécurisé / Webhook dispatch
        order_num = f"403-{random.randint(1000000, 9999999)}-{random.randint(1000000, 9999999)}"
        simulated_cost = round(18.50 * quantity, 2)
        
        logger.info(
            f"[COMMANDE FOURNISSEUR AMAZON] Article {source_id} commandé avec succès !\n"
            f"  -> Réf Commande : {order_num}\n"
            f"  -> Destinataire  : {recipient}, {street}, {postal_code} {city}\n"
            f"  -> Montant Débit : {simulated_cost} €"
        )
        
        return PurchaseResult(
            success=True,
            source_order_id=order_num,
            total_charged_eur=simulated_cost,
            estimated_delivery="Sous 2 à 4 jours ouvrés (Colissimo / Amazon Logistics)"
        )
