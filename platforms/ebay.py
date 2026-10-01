import random
import logging
import json
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional
from config import cfg
from stealth import stealth

logger = logging.getLogger("EbayClient")

class EbayClient:
    def __init__(self):
        self.simulated_orders: List[Dict[str, Any]] = []

    def _get_api_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {cfg.EBAY_USER_TOKEN}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-EBAY-C-MARKETPLACE-ID": cfg.EBAY_MARKETPLACE_ID
        }

    def _get_base_url(self) -> str:
        if cfg.EBAY_ENVIRONMENT.upper() == "SANDBOX":
            return "https://api.sandbox.ebay.com"
        return "https://api.ebay.com"

    def publish_listing(self, title: str, description: str, price_eur: float,
                        stock_quantity: int = 2, image_urls: List[str] = None) -> str:
        stealth.delay_for_listing()
        
        if cfg.SIMULATION_MODE:
            simulated_item_id = f"EBAY-{random.randint(100000000000, 999999999999)}"
            logger.info(
                f"[EBAY SIMULATION] Annonce creee sur {cfg.EBAY_MARKETPLACE_ID} :\n"
                f"  -> Ref eBay     : {simulated_item_id}\n"
                f"  -> Titre        : {title}\n"
                f"  -> Prix Vente   : {price_eur:.2f} EUR\n"
                f"  -> Stock Alloue : {stock_quantity}"
            )
            return simulated_item_id
        else:
            sku = f"SKU-{random.randint(100000, 999999)}"
            url = f"{self._get_base_url()}/sell/inventory/v1/inventory_item/{sku}"
            payload = {
                "availability": {"shipToLocationAvailability": {"quantity": stock_quantity}},
                "condition": "NEW",
                "product": {
                    "title": title[:80],
                    "description": description,
                    "imageUrls": image_urls or []
                }
            }
            try:
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers=self._get_api_headers(),
                    method="PUT"
                )
                with urllib.request.urlopen(req, timeout=20) as resp:
                    logger.info(f"[EBAY LIVE] Article d'inventaire SKU {sku} cree (HTTP {resp.status})")
                return f"EBAY-LIVE-{sku}"
            except Exception as e:
                logger.error(f"[EBAY API ERROR] Echec publication inventaire : {e}")
                return f"EBAY-LIVE-{sku}"

    def get_paid_orders(self) -> List[Dict[str, Any]]:
        if cfg.SIMULATION_MODE:
            orders = list(self.simulated_orders)
            self.simulated_orders.clear()
            return orders
        else:
            url = f"{self._get_base_url()}/sell/fulfillment/v1/order?filter=orderfulfillmentstatus:{{NOT_STARTED}}&filter=paymentstatus:{{PAID}}"
            try:
                req = urllib.request.Request(url, headers=self._get_api_headers(), method="GET")
                with urllib.request.urlopen(req, timeout=20) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    results = []
                    for o in data.get("orders", []):
                        pricing = o.get("pricingSummary", {}).get("total", {})
                        shipping = o.get("fulfillmentStartPlans", [{}])[0].get("shippingStep", {}).get("shipTo", {})
                        addr = shipping.get("contactAddress", {})
                        results.append({
                            "order_id": o["orderId"],
                            "ebay_item_id": o["lineItems"][0]["legacyItemId"],
                            "buyer_username": o.get("buyer", {}).get("username", "client"),
                            "buyer_name": shipping.get("fullName", "Client eBay"),
                            "total_paid_eur": float(pricing.get("value", 0.0)),
                            "shipping_address": {
                                "name": shipping.get("fullName", "Client eBay"),
                                "street1": addr.get("addressLine1", ""),
                                "street2": addr.get("addressLine2", ""),
                                "city": addr.get("city", ""),
                                "postal_code": addr.get("postalCode", ""),
                                "country_code": addr.get("countryCode", "FR"),
                                "phone": shipping.get("primaryPhone", {}).get("phoneNumber", "")
                            }
                        })
                    return results
            except Exception as e:
                logger.error(f"[EBAY API ERROR] Echec recuperation des commandes : {e}")
                return []

    def create_simulated_sale(self, ebay_item_id: str, total_price_eur: float) -> Dict[str, Any]:
        prenoms = ["Lucas", "Camille", "Thomas", "Sarah", "Alexandre", "Emma"]
        noms = ["Dupont", "Martin", "Bernard", "Petit", "Moreau", "Dubois"]
        villes = [
            ("Paris", "75015", "12 Rue du Commerce"),
            ("Lyon", "69002", "45 Rue de la Republique"),
            ("Toulouse", "31000", "8 Place du Capitole"),
            ("Bordeaux", "33000", "22 Cours de l'Intendance")
        ]
        prenom = random.choice(prenoms)
        nom = random.choice(noms)
        ville, cp, rue = random.choice(villes)
        
        order = {
            "order_id": f"ORD-{random.randint(100000, 999999)}",
            "ebay_item_id": ebay_item_id,
            "buyer_username": f"{prenom.lower()}_{nom.lower()}{random.randint(10, 99)}",
            "buyer_name": f"{prenom} {nom}",
            "total_paid_eur": total_price_eur,
            "shipping_address": {
                "name": f"{prenom} {nom}",
                "street1": rue,
                "street2": "",
                "city": ville,
                "postal_code": cp,
                "country_code": "FR",
                "phone": f"06{random.randint(10000000, 99999999)}"
            }
        }
        self.simulated_orders.append(order)
        return order

    def update_tracking(self, ebay_order_id: str, tracking_number: str, carrier: str) -> bool:
        if cfg.SIMULATION_MODE:
            logger.info(
                f"[EBAY FULFILLMENT SIMULE] Suivi transmis pour commande {ebay_order_id} :\n"
                f"  -> Transporteur : {carrier} | N. Suivi : {tracking_number}"
            )
            return True
        else:
            url = f"{self._get_base_url()}/sell/fulfillment/v1/order/{ebay_order_id}/shipping_fulfillment"
            payload = {
                "lineItems": [{"lineItemId": "1", "quantity": 1}],
                "shippingCarrierCode": carrier,
                "trackingNumber": tracking_number
            }
            try:
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers=self._get_api_headers(),
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=15) as resp:
                    logger.info(f"[EBAY LIVE] Suivi {tracking_number} valide sur eBay (HTTP {resp.status})")
                return True
            except Exception as e:
                logger.error(f"[EBAY API ERROR] Echec upload tracking : {e}")
                return False

ebay_client = EbayClient()
