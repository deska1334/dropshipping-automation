import sys
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except AttributeError:
        pass

import os
import argparse
import logging
from config import cfg
from database import get_connection, get_unfulfilled_orders
from engine import dropship_engine
from platforms.ebay import ebay_client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)

def cmd_status():
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

    cur.execute("SELECT COUNT(*) as count FROM orders WHERE status IN ('PAID', 'NEEDS_REVIEW', 'PENDING_RETRY')")
    pending_orders = cur.fetchone()["count"]

    print("=" * 60)
    print("         TABLEAU DE BORD DROPSHIPPING AUTOMATISE         ")
    print("=" * 60)
    print(f" Mode operationnel              : {'SIMULATION (100% SECURISE)' if cfg.SIMULATION_MODE else 'REEL (LIVE API)'}")
    print(f" Produits sources en base       : {total_products}")
    print(f" Annonces eBay actives          : {active_listings}")
    print(f" Commandes en attente d'achat   : {pending_orders}")
    print(f" Commandes finalisees (succes)  : {completed_orders}")
    print(f" Benefice net cumule            : +{total_profit:.2f} EUR")
    print("-" * 60)
    
    cur.execute("SELECT ebay_item_id, title, selling_price_eur, estimated_profit_eur FROM listings ORDER BY id DESC LIMIT 5")
    recent_listings = cur.fetchall()
    if recent_listings:
        print("Dernieres annonces eBay :")
        for row in recent_listings:
            print(f"  [{row['ebay_item_id']}] {row['title'][:38]}... -> {row['selling_price_eur']:.2f} EUR (+{row['estimated_profit_eur']:.2f} EUR net)")
    print("=" * 60)
    conn.close()

def cmd_search(args):
    provider = args.provider.lower()
    query = args.query
    limit = args.limit
    
    print(f"Recherche sur {provider.upper()} pour : '{query}' (limite : {limit})...")
    engine_provider = dropship_engine.amazon if provider == "amazon" else dropship_engine.aliexpress
    results = engine_provider.search_products(query, limit=limit)
    
    print(f"\nTrouve {len(results)} articles :")
    for r in results:
        print(f"- [{r.source_id}] {r.title}")
        print(f"  Prix fournisseur : {r.price_eur:.2f} EUR (+ {r.shipping_eur:.2f} EUR port) | Categorie: {r.category}")
        print(f"  Lien : {r.source_url}\n")

def cmd_list(args):
    query = args.query
    provider = args.provider.lower()
    limit = args.limit
    print(f"Lancement du sourcage et de la mise en vente eBay pour '{query}' sur {provider.upper()}...")
    dropship_engine.discover_and_list(query, provider_name=provider, limit=limit)
    print("Termine. Consultez l'etat avec 'python cli.py status'.")

def cmd_test_flow():
    print("=" * 60)
    print(" TEST DU CYCLE COMPLET : SOURCAGE -> EBAY -> COMMANDE -> EXPEDITION ")
    print("=" * 60)

    print("\n[ETAPE 1/4] Sourcage d'un article sur Amazon...")
    dropship_engine.discover_and_list("Ecouteurs Sans Fil", provider_name="amazon", limit=1)

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT ebay_item_id, selling_price_eur FROM listings ORDER BY id DESC LIMIT 1")
    latest = cur.fetchone()
    conn.close()

    if not latest:
        print("Erreur: aucune annonce n'a pu etre creee.")
        return

    ebay_item_id = latest["ebay_item_id"]
    price = latest["selling_price_eur"]

    print(f"\n[ETAPE 2/4] Un client achete et paie l'article {ebay_item_id} ({price:.2f} EUR)...")
    simulated_order = ebay_client.create_simulated_sale(ebay_item_id, price)
    print(f"Commande generee : {simulated_order['order_id']} pour {simulated_order['buyer_name']}")

    print("\n[ETAPE 3/4] Traitement automatique de la commande payee (Achat fournisseur)...")
    processed = dropship_engine.run_fulfillment_cycle()

    print("\n[ETAPE 4/4] Bilan final...")
    cmd_status()

def main():
    parser = argparse.ArgumentParser(description="Bot Dropshipping Automatise & Systeme Anti-Ban")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("status", help="Afficher les statistiques et les annonces actives")

    p_search = subparsers.add_parser("search", help="Rechercher des produits sur un fournisseur")
    p_search.add_argument("--provider", default="amazon", choices=["amazon", "aliexpress"])
    p_search.add_argument("--query", required=True, help="Mot-cle de recherche")
    p_search.add_argument("--limit", type=int, default=3)

    for cmd_name in ["list-items", "list-item"]:
        p_list = subparsers.add_parser(cmd_name, help="Rechercher et publier des articles sur eBay")
        p_list.add_argument("--provider", default="amazon", choices=["amazon", "aliexpress"])
        p_list.add_argument("--query", required=True, help="Mots-cles des articles a lister")
        p_list.add_argument("--limit", type=int, default=1)

    subparsers.add_parser("test-flow", help="Executer une simulation complete de vente et d'achat automatique")

    subparsers.add_parser("fulfill", help="Traiter les commandes payees en attente")

    args = parser.parse_args()

    if args.command == "status":
        cmd_status()
    elif args.command == "search":
        cmd_search(args)
    elif args.command in ["list-items", "list-item"]:
        cmd_list(args)
    elif args.command == "test-flow":
        cmd_test_flow()
    elif args.command == "fulfill":
        processed = dropship_engine.run_fulfillment_cycle()
        print(f"{processed} commande(s) traitee(s).")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
