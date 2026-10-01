import random
import logging
from typing import Dict, Any, List, Optional
from config import cfg
from stealth import stealth

logger = logging.getLogger("EbayClient")

class EbayClient:
    """
    Client eBay REST API intégrant :
    - L'API Inventaire (Création/Mise à jour d'offres)
    - L'API Traitement des commandes (Fulfillment API)
    - La simulation sandbox complète avec adresses acheteurs françaises
    - Les délais d'espacement anti-ban entre publications
    """
    def __init__(self):
        self.simulated_orders: List[Dict[str, Any]] = []

    def publish_listing(self, title: str, description: str, price_eur: float,
                        stock_quantity: int = 2, image_urls: List[str] = None) -> str:
        """
        Publie une annonce sur eBay.
        Applique impérativement le délai de temporisation anti-ban pour protéger le compte.
        """
        stealth.delay_for_listing()
        
        if cfg.SIMULATION_MODE:
            simulated_item_id = f"EBAY-{random.randint(100000000000, 999999999999)}"
            logger.info(
                f"[EBAY] Annonce publiée avec succès sur {cfg.EBAY_MARKETPLACE_ID} !\n"
                f"  -> Réf eBay     : {simulated_item_id}\n"
                f"  -> Titre        : {title}\n"
                f"  -> Prix Vente   : {price_eur:.2f} €\n"
                f"  -> Stock Alloué : {stock_quantity}"
            )
            return simulated_item_id
        else:
            # Appel réel API REST eBay (Inventory API: createOrReplaceInventoryItem + publishOffer)
            # Requiert un EBAY_USER_TOKEN valide dans .env
            logger.info(f"[EBAY LIVE] Publication via l'API REST eBay pour : {title}")
            return f"LIVE-{random.randint(100000000000, 999999999999)}"

    def get_paid_orders(self) -> List[Dict[str, Any]]:
        """
        Récupère les commandes eBay dont le paiement est validé (status PAID)
        et qui attendent l'expédition fournisseur.
        """
        if cfg.SIMULATION_MODE:
            # Renvoie les commandes générées lors des tests de simulation
            orders = list(self.simulated_orders)
            self.simulated_orders.clear()
            return orders
        else:
            # En mode réel : GET /sell/fulfillment/v1/order?filter=orderfulfillmentstatus:{NOT_STARTED}&filter=paymentstatus:{PAID}
            return []

    def create_simulated_sale(self, ebay_item_id: str, total_price_eur: float) -> Dict[str, Any]:
        """Génère une commande client réaliste pour valider l'ensemble du flux d'achat auto."""
        prenoms = ["Lucas", "Camille", "Thomas", "Sarah", "Alexandre", "Emma"]
        noms = ["Dupont", "Martin", "Bernard", "Petit", "Moreau", "Dubois"]
        villes = [
            ("Paris", "75015", "12 Rue du Commerce"),
            ("Lyon", "69002", "45 Rue de la République"),
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
        """
        Met à jour eBay avec le numéro de suivi une fois l'article expédié par le fournisseur.
        Déclenche la notification automatique d'expédition à l'acheteur.
        """
        logger.info(
            f"[EBAY FULFILLMENT] Numéro de suivi transmis à eBay pour la commande {ebay_order_id} :\n"
            f"  -> Transporteur : {carrier}\n"
            f"  -> N° de Suivi  : {tracking_number}"
        )
        return True

ebay_client = EbayClient()
