import sys
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except AttributeError:
        pass

import time
import argparse
import logging
from datetime import datetime
from config import cfg
from database import get_connection
from engine import dropship_engine
from cli import cmd_status, cmd_test_flow

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger('StartBot')

DEFAULT_QUERIES = [
    'ecouteurs sans fil bluetooth',
    'montre connectee sport fitness',
    'mini projecteur led portable',
    'lampe solaire exterieure detecteur',
    'chargeur sans fil rapide induction',
    'support telephone voiture charge rapide'
]

def banner():
    mode_str = "SIMULATION (Securise, sans risque)" if cfg.SIMULATION_MODE else "REEL (PRODUCTION LIVE API)"
    print("=" * 65)
    print("          LANCEMENT DU BOT DROPSHIPPING AUTOMATISE")
    print("=" * 65)
    print(f" Mode actuel       : {mode_str}")
    print(f" Plateforme cible  : eBay ({cfg.EBAY_MARKETPLACE_ID})")
    print(f" Quota max listing : {cfg.MAX_LISTINGS_PER_DAY} par 24 heures")
    print(f" Anti-ban jitter   : ACTIVE (delais gaussiens)")
    print("=" * 65)

def run_daemon_loop(interval_sec=300, auto_list=True):
    banner()
    logger.info(f"Demarrage du daemon en arriere-plan (cycle : {interval_sec}s)...")
    logger.info("Appuyez sur Ctrl+C a tout moment pour arreter le bot proprement.\n")

    query_idx = 0
    cycle = 1

    try:
        while True:
            cycle_time = datetime.now().strftime("%H:%M:%S")
            print(f"\n--- [CYCLE #{cycle} - {cycle_time}] ---")

            # 1. Verification et traitement des commandes payees (Fulfillment)
            print("[1/2] Verification des commandes eBay a expedier...")
            try:
                processed = dropship_engine.run_fulfillment_cycle()
                if processed > 0:
                    logger.info(f"Succes : {processed} commande(s) traitee(s) et achetee(s) chez le fournisseur.")
                else:
                    print("      Aucune nouvelle commande en attente.")
            except Exception as e:
                logger.error(f"Erreur lors du cycle de fulfillment : {e}")

            # 2. Sourcage et publication automatique si active
            if auto_list:
                query = DEFAULT_QUERIES[query_idx % len(DEFAULT_QUERIES)]
                query_idx += 1
                provider = "amazon" if (cycle % 2 == 1) else "aliexpress"
                print(f"[2/2] Sourcage et mise en vente eBay (Recherche: '{query}' sur {provider.upper()})...")
                try:
                    dropship_engine.discover_and_list(query, provider_name=provider, limit=1)
                except Exception as e:
                    logger.error(f"Erreur lors du cycle de sourcage/listing : {e}")

            # 3. Bilan rapide
            print("\n[Statut du bot]")
            cmd_status()

            print(f"Prochain cycle dans {interval_sec} secondes... [Ctrl+C pour arreter]")
            time.sleep(interval_sec)
            cycle += 1

    except KeyboardInterrupt:
        print("\n\nArret demande par l'utilisateur. Fermeture securisee du bot...")
        logger.info("Bot arrete proprement.")

def interactive_menu():
    banner()
    while True:
        print("\nMenu de demarrage :")
        print("  1. Lancer le Bot en continu (Daemon automatique)")
        print("  2. Executer un cycle de test complet (Test-Flow)")
        print("  3. Afficher le tableau de bord (Status & Benefices)")
        print("  4. Traiter immediatement les commandes payees (Fulfill)")
        print("  5. Quitter")
        print("-" * 65)

        try:
            choice = input("Votre choix [1-5] (defaut: 1) : ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nAu revoir !")
            break

        if not choice or choice == "1":
            try:
                interval_input = input("Intervalle entre les cycles en secondes [defaut: 300s (5min)] : ").strip()
                interval = int(interval_input) if interval_input else 300
            except ValueError:
                interval = 300
            run_daemon_loop(interval_sec=interval)
            break
        elif choice == "2":
            cmd_test_flow()
        elif choice == "3":
            cmd_status()
        elif choice == "4":
            processed = dropship_engine.run_fulfillment_cycle()
            print(f"{processed} commande(s) traitee(s).")
        elif choice == "5":
            print("Fermeture du programme.")
            break
        else:
            print("Choix non valide, veuillez reessayer.")

def main():
    parser = argparse.ArgumentParser(description="StartBot - Lanceur du bot de Dropshipping")
    parser.add_argument("--daemon", action="store_true", help="Lancer directement le bot en continu")
    parser.add_argument("--test", action="store_true", help="Executer un test-flow complet")
    parser.add_argument("--status", action="store_true", help="Afficher le statut actuel")
    parser.add_argument("--fulfill", action="store_true", help="Traiter les commandes en attente")
    parser.add_argument("--interval", type=int, default=300, help="Intervalle en secondes pour le daemon (defaut: 300)")
    parser.add_argument("--no-auto-list", action="store_true", help="Desactiver le sourcage automatique")

    args = parser.parse_args()

    if args.daemon:
        run_daemon_loop(interval_sec=args.interval, auto_list=not args.no_auto_list)
    elif args.test:
        cmd_test_flow()
    elif args.status:
        cmd_status()
    elif args.fulfill:
        processed = dropship_engine.run_fulfillment_cycle()
        print(f"{processed} commande(s) traitee(s).")
    else:
        interactive_menu()

if __name__ == "__main__":
    main()
