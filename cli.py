import sys
# Forcer UTF-8 sur la console Windows
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except AttributeError:
        pass
import sys
import os
import argparse
import logging
from config import cfg
from database import get_connection
from engine import dropship_engine
from platforms.ebay import ebay_client

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)

def cmd_status():
    """Affiche le tableau de bord de l'activité dropshipping."""
    conn = get_connection()
    cur = conn.cursor()
    
    cur.execute("SELECT COUNT(*) as count FROM products")
    total_products = cur.fetchone()["count"]
    
    cur.execute("SELECT COUNT(*) as count FROM listings WHERE status = 'ACTIVE'")
    active_listings = cur.fetchone()["count"]
    
    cur.execute("SELECT COUNT(*) as count, COALESCE(SUM(actual_profit_eur), 0) as total_profit FROM orders WHERE status = 'COMPLETED'")
    orders_row = cur.fetchone()
    completed_orders = orders_row["count"]
    total_profit = orders_row["total_profit"]

    print("=" * 60)
    print("         TABLEAU DE BORD DROPSHIPPING AUTOMATISÉ         ")
    print("=" * 60)
    print(f" Mode opérationnel          : {'SIMULATION (100% SÉCURISÉ)' if cfg.SIMULATION_MODE else 'RÉEL (LIVE API)'}")
    print(f" Produits sourcés en base   : {total_products}")
    print(f" Annonces eBay actives      : {active_listings}")
    print(f" Commandes traitées avec succès : {completed_orders}")
    print(f" Bénéfice net cumulé       : +{total_profit:.2f} €")
    print("-" * 60)
    
    cur.execute("SELECT ebay_item_id, title, selling_price_eur, estimated_profit_eur FROM listings ORDER BY id DESC LIMIT 5")
    recent_listings = cur.fetchall()
    if recent_listings:
        print("Dernières annonces eBay :")
        for row in recent_listings:
            print(f"  [{row['ebay_item_id']}] {row['title'][:38]}... -> {row['selling_price_eur']:.2f} € (+{row['estimated_profit_eur']:.2f} € net)")
    print("=" * 60)
    conn.close()

def cmd_search(args):
    """Recherche des articles sur Amazon ou AliExpress."""
    provider = args.provider.lower()
    query = args.query
    limit = args.limit
    
    print(f"Recherche sur {provider.upper()} pour : '{query}' (limite : {limit})...")
    engine_provider = dropship_engine.amazon if provider == "amazon" else dropship_engine.aliexpress
    results = engine_provider.search_products(query, limit=limit)
    
    print(f"\nTrouvé {len(results)} articles :")
    for r in results:
        print(f"- [{r.source_id}] {r.title}")
        print(f"  Prix fournisseur : {r.price_eur:.2f} € (+ {r.shipping_eur:.2f} € port) | Catégorie: {r.category}")
        print(f"  Lien : {r.source_url}\n")

def cmd_list(args):
    """Sorce et met en vente sur eBay des articles selon une requête."""
    query = args.query
    provider = args.provider.lower()
    limit = args.limit
    print(f"Lancement du sourçage et de la mise en vente eBay pour '{query}' sur {provider.upper()}...")
    dropship_engine.discover_and_list(query, provider_name=provider, limit=limit)
    print("Terminé. Consultez l'état avec 'python cli.py status'.")

def cmd_test_flow():
    """
    Exécute un cycle complet de bout en bout :
    1. Sourçage d'un article Amazon.
    2. Calcul automatique du prix avec marge et frais.
    3. Mise en vente sur eBay.
    4. Simulation d'un achat client avec paiement reçu et adresse en France.
    5. Achat automatique chez le fournisseur vers l'adresse client.
    6. Transmission du numéro de suivi et clôture de commande.
    """
    print("=" * 60)
    print(" TEST DU CYCLE COMPLET : SOURCAGE -> EBAY -> COMMANDE -> EXPÉDITION ")
    print("=" * 60)

    # 1. Sourçage et mise en vente
    print("\n[ETAPE 1/4] Sourçage d'un article sur Amazon...")
    dropship_engine.discover_and_list("Écouteurs Sans Fil", provider_name="amazon", limit=1)

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT ebay_item_id, selling_price_eur FROM listings ORDER BY id DESC LIMIT 1")
    latest = cur.fetchone()
    conn.close()

    if not latest:
        print("Erreur: aucune annonce n'a pu être créée.")
        return

    ebay_item_id = latest["ebay_item_id"]
    price = latest["selling_price_eur"]

    # 2. Simulation d'un client qui paye l'article sur eBay
    print(f"\n[ETAPE 2/4] Un client achète et paie l'article {ebay_item_id} ({price:.2f} €)...")
    simulated_order = ebay_client.create_simulated_sale(ebay_item_id, price)
    print(f"Commande générée : {simulated_order['order_id']} pour {simulated_order['buyer_name']}")

    # 3. Traitement automatique de la commande
    print("\n[ETAPE 3/4] Traitement automatique de la commande payée (Achat fournisseur)...")
    processed = dropship_engine.run_fulfillment_cycle()

    # 4. Bilan final
    print("\n[ETAPE 4/4] Bilan final...")
    cmd_status()

def main():
    parser = argparse.ArgumentParser(description="Bot Dropshipping Automatisé & Système Anti-Ban")
    subparsers = parser.add_subparsers(dest="command")

    # Commande status
    subparsers.add_parser("status", help="Afficher les statistiques et les annonces actives")

    # Commande search
    p_search = subparsers.add_parser("search", help="Rechercher des produits sur un fournisseur")
    p_search.add_argument("--provider", default="amazon", choices=["amazon", "aliexpress"])
    p_search.add_argument("--query", required=True, help="Mot-clé de recherche")
    p_search.add_argument("--limit", type=int, default=3)

    # Commande list-item
    p_list = subparsers.add_parser("list-items", help="Rechercher et publier des articles sur eBay")
    p_list.add_argument("--provider", default="amazon", choices=["amazon", "aliexpress"])
    p_list.add_argument("--query", required=True, help="Mots-clés des articles à lister")
    p_list.add_argument("--limit", type=int, default=1)

    # Commande test-flow
    subparsers.add_parser("test-flow", help="Exécuter une simulation complète de vente et d'achat automatique")

    # Commande fulfill
    subparsers.add_parser("fulfill", help="Traiter les commandes payées en attente")

    args = parser.parse_args()

    if args.command == "status":
        cmd_status()
    elif args.command == "search":
        cmd_search(args)
    elif args.command == "list-items":
        cmd_list(args)
    elif args.command == "test-flow":
        cmd_test_flow()
    elif args.command == "fulfill":
        processed = dropship_engine.run_fulfillment_cycle()
        print(f"{processed} commande(s) traitée(s).")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
