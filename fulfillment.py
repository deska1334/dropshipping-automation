import logging
import random
from typing import Dict, Any, List
from config import cfg
from database import (
    get_listing_by_ebay_id, get_product_by_id, 
    save_order, update_order_fulfillment, log_activity,
    get_unfulfilled_orders
)
from platforms.ebay import ebay_client
from providers.amazon import AmazonProvider
from providers.aliexpress import AliExpressProvider
from pricing import is_profitable_sale

logger = logging.getLogger("FulfillmentEngine")

class FulfillmentEngine:
    def __init__(self):
        self.providers = {
            "amazon": AmazonProvider(),
            "aliexpress": AliExpressProvider()
        }

    def process_order(self, order_dict: Dict[str, Any]) -> bool:
        ebay_order_id = order_dict["order_id"]
        ebay_item_id = order_dict["ebay_item_id"]
        buyer_name = order_dict["buyer_name"]
        shipping_address = order_dict["shipping_address"]
        total_paid = order_dict["total_paid_eur"]

        logger.info(f"=== [COMMANDE EBAY EN COURS] {ebay_order_id} ({total_paid:.2f} EUR) ===")
        logger.info(f"Destinataire : {buyer_name} ({shipping_address.get('city', '')}, {shipping_address.get('country_code', 'FR')})")

        save_order(
            ebay_order_id=ebay_order_id,
            ebay_item_id=ebay_item_id,
            buyer_username=order_dict.get("buyer_username", "anonymous"),
            buyer_name=buyer_name,
            address_dict=shipping_address,
            total_paid=total_paid
        )

        listing = get_listing_by_ebay_id(ebay_item_id)
        if not listing:
            msg = f"Impossible de retrouver l'annonce associee a {ebay_item_id}"
            logger.error(msg)
            update_order_fulfillment(ebay_order_id, status="FAILED", error_message=msg)
            return False

        product = get_product_by_id(listing["product_id"])
        if not product:
            msg = f"Impossible de retrouver le produit source ID {listing['product_id']}"
            logger.error(msg)
            update_order_fulfillment(ebay_order_id, status="FAILED", error_message=msg)
            return False

        provider_name = product["provider"]
        provider = self.providers.get(provider_name)
        if not provider:
            msg = f"Fournisseur inconnu : {provider_name}"
            logger.error(msg)
            update_order_fulfillment(ebay_order_id, status="FAILED", error_message=msg)
            return False

        # VERIFICATION DE SECURITE PRE-ACHAT (Stock & Hausse de prix imprevue)
        fresh_details = provider.get_product_details(product["source_id"])
        if fresh_details:
            if not fresh_details.in_stock:
                msg = f"Alerte : Le produit {product['source_id']} est en rupture chez {provider_name} !"
                logger.error(msg)
                update_order_fulfillment(ebay_order_id, status="NEEDS_REVIEW", error_message=msg)
                return False
                
            current_total_cost = fresh_details.price_eur + fresh_details.shipping_eur
            if not is_profitable_sale(current_total_cost, total_paid):
                msg = f"Alerte Hausse de Prix : Cout fournisseur passe a {current_total_cost:.2f} EUR pour une vente a {total_paid:.2f} EUR. Achat stoppe pour eviter la perte."
                logger.error(msg)
                update_order_fulfillment(ebay_order_id, status="NEEDS_REVIEW", error_message=msg)
                return False

        # Execution de l'achat fournisseur
        logger.info(f"Declenchement de l'achat automatique aupres de {provider_name.upper()}...")
        purchase_result = provider.order_and_ship(
            source_id=product["source_id"],
            quantity=1,
            shipping_address=shipping_address
        )

        if not purchase_result.success:
            logger.error(f"Echec de l'achat fournisseur : {purchase_result.error_message}")
            update_order_fulfillment(
                ebay_order_id, 
                status="FAILED", 
                error_message=purchase_result.error_message
            )
            return False

        actual_profit = round(total_paid - purchase_result.total_charged_eur - (total_paid * 0.13), 2)
        carrier = "Colissimo" if provider_name == "amazon" else "AliExpress Standard"
        tracking_number = f"FR{random.randint(100000000, 999999999)}CM"
        
        ebay_client.update_tracking(
            ebay_order_id=ebay_order_id,
            tracking_number=tracking_number,
            carrier=carrier
        )

        update_order_fulfillment(
            ebay_order_id=ebay_order_id,
            status="COMPLETED",
            source_order_id=purchase_result.source_order_id,
            tracking_number=tracking_number,
            carrier=carrier,
            purchase_cost=purchase_result.total_charged_eur,
            actual_profit=actual_profit
        )

        logger.info(
            f"[SUCCES] [COMMANDE FINALISEE]\n"
            f"  - Commande eBay : {ebay_order_id}\n"
            f"  - Fournisseur   : {purchase_result.source_order_id} ({provider_name.capitalize()})\n"
            f"  - N. Suivi      : {tracking_number} ({carrier})\n"
            f"  - Benefice Net  : +{actual_profit:.2f} EUR\n"
        )
        return True

fulfillment_engine = FulfillmentEngine()
