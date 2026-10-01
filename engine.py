import time
import logging
from config import cfg
from pricing import calculate_selling_price
from database import (
    upsert_product, create_or_update_listing,
    get_connection, log_activity
)
from providers.amazon import AmazonProvider
from providers.aliexpress import AliExpressProvider
from platforms.ebay import ebay_client
from fulfillment import fulfillment_engine
from stealth import stealth, CircuitBreakerException

logger = logging.getLogger("DropshipEngine")

class DropshipEngine:
    def __init__(self):
        self.amazon = AmazonProvider()
        self.aliexpress = AliExpressProvider()

    def discover_and_list(self, query: str, provider_name: str = "amazon", limit: int = 2):
        """
        Cherche des articles à bas prix, vérifie la rentabilité et les publie sur eBay
        en respectant les quotas et délais anti-ban.
        """
        provider = self.amazon if provider_name == "amazon" else self.aliexpress
        logger.info(f"Recherche de produits rentables pour '{query}' sur {provider_name.upper()}...")

        try:
            products = provider.search_products(query, limit=limit)
        except CircuitBreakerException as e:
            logger.error(str(e))
            return

        for p in products:
            # Calcul du prix de vente et de la rentabilité
            pricing = calculate_selling_price(p.price_eur, p.shipping_eur)
            logger.info(
                f"Analyse article : {p.title[:50]}...\n"
                f"  Coût fournisseur: {pricing.total_cost_eur:.2f} € | "
                f"Prix eBay calculé: {pricing.selling_price_eur:.2f} € | "
                f"Marge nette: +{pricing.net_profit_eur:.2f} € ({pricing.margin_percent}%)"
            )

            if not pricing.is_profitable:
                logger.warning("Article rejeté : marge insuffisante par rapport aux critères de sécurité.")
                continue

            # Enregistrement en base de données
            prod_id = upsert_product(
                provider=p.provider,
                source_id=p.source_id,
                source_url=p.source_url,
                title=p.title,
                description=p.description,
                price_eur=p.price_eur,
                shipping_eur=p.shipping_eur,
                in_stock=p.in_stock,
                category=p.category,
                images=p.images
            )

            # Publication sur eBay avec délai anti-ban
            try:
                ebay_item_id = ebay_client.publish_listing(
                    title=p.title,
                    description=p.description,
                    price_eur=pricing.selling_price_eur,
                    stock_quantity=2,
                    image_urls=p.images
                )
                create_or_update_listing(
                    product_id=prod_id,
                    ebay_item_id=ebay_item_id,
                    title=p.title,
                    supplier_cost=pricing.total_cost_eur,
                    selling_price=pricing.selling_price_eur,
                    profit=pricing.net_profit_eur,
                    status="ACTIVE"
                )
            except PermissionError as pe:
                logger.warning(str(pe))
                break
            except Exception as e:
                logger.error(f"Erreur lors de la mise en vente eBay : {e}")

    def run_fulfillment_cycle(self):
        """Vérifie les commandes eBay payées et déclenche les achats correspondants."""
        orders = ebay_client.get_paid_orders()
        if not orders:
            return 0
            
        logger.info(f"[CYCLE FULFILLMENT] {len(orders)} commande(s) en attente de traitement.")
        processed = 0
        for ord_info in orders:
            if fulfillment_engine.process_order(ord_info):
                processed += 1
        return processed

dropship_engine = DropshipEngine()
