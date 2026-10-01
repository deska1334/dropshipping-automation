# 🚀 Guide Dédié : Sortir du Mode Simulation & Passage en Production

Ce document est le guide de référence pour basculer le bot de dropshipping du mode sécurisé (**Simulation**) vers le mode réel (**Production live**).

---

## ⚠️ Avertissements Importants & Règles d'Or

1. **Ne brûlez pas les étapes** : Ne commencez jamais directement avec 50 annonces par jour. Un compte eBay nouvellement créé qui publie massivement sans historique de vente déclenche une restriction algorithmique (**MC011**).
2. **Période de Rodage ("Warm-up")** : Commencez par publier 1 à 2 annonces par jour la première semaine, puis 3 à 5 la deuxième semaine.
3. **Sécurité des Clés API** : Ne committez JAMAIS votre fichier `.env` sur un dépôt public. Il reste localement sur votre machine grâce au `.gitignore`.

---

## 📋 Étape 1 : Obtenir les Clés API Développeur eBay

Pour que le bot puisse créer des annonces et récupérer les commandes payées directement sur votre compte eBay :

1. Rendez-vous sur le [Portail eBay Developers Program](https://developer.ebay.com/).
2. Créez un compte développeur ou connectez-vous avec votre compte eBay.
3. Allez dans **Application Keys** et générez vos clés d'application :
   - **App ID (Client ID)**
   - **Dev ID**
   - **Cert ID (Client Secret)**
4. Générez un **User Token OAuth** (jeton utilisateur) avec les autorisations nécessaires :
   - `https://api.ebay.com/oauth/api_scope/sell.inventory` (pour publier et modifier des annonces)
   - `https://api.ebay.com/oauth/api_scope/sell.fulfillment` (pour lire les commandes payées et envoyer les numéros de suivi)
5. Si vous préférez tester d'abord avec un compte d'essai, utilisez l'environnement `SANDBOX`. Pour vendre en réel, utilisez `PRODUCTION`.

---

## 📦 Étape 2 : Configurer les Comptes Fournisseurs

### Option A : Amazon
- **API Officielle (PA-API)** : Créez un compte Amazon Partenaire (Associates) et récupérez vos clés PA-API (`Access Key`, `Secret Key`, `Associate Tag`).
- **Moyen de paiement** : Le compte Amazon acheteur doit posséder une carte bancaire approvisionnée et une adresse de facturation valide pour honorer les achats automatiques lorsque le client eBay règle sa commande.

### Option B : AliExpress
- **AliExpress Open Platform** : Créez un compte sur `portals.aliexpress.com` et activez l'API Dropshipping pour obtenir l'`App Key` et l'`App Secret`.
- **Mode direct** : Assurez-vous d'avoir enregistré un moyen de paiement (carte ou compte pro) pré-autorisé.

---

## ⚙️ Étape 3 : Renseigner le Fichier `.env`

Ouvrez le fichier `.env` situé à la racine du projet et remplacez les paramètres :

```env
# 1. BASCULER DU MODE SIMULATION AU MODE RÉEL
SIMULATION_MODE=False

# 2. CONFIGURATION EBAY LIVE
EBAY_ENVIRONMENT=PRODUCTION
EBAY_APP_ID=Votre_Vrai_App_ID_eBay
EBAY_CERT_ID=Votre_Vrai_Cert_ID_eBay
EBAY_DEV_ID=Votre_Vrai_Dev_ID_eBay
EBAY_USER_TOKEN=Votre_Jeton_OAuth_Utilisateur_Complet
EBAY_MARKETPLACE_ID=EBAY_FR

# 3. FOURNISSEURS
AMAZON_PAAPI_KEY=Votre_Cle_Amazon
AMAZON_PAAPI_SECRET=Votre_Secret_Amazon
AMAZON_ASSOCIATE_TAG=Votre_Tag_Partenaire

ALIEXPRESS_APP_KEY=Votre_Cle_AliExpress
ALIEXPRESS_APP_SECRET=Votre_Secret_AliExpress

# 4. MARGES DE SÉCURITÉ RECOMMANDÉES EN PRODUCTION
MIN_PROFIT_MARGIN_PERCENT=25.0
MIN_PROFIT_ABSOLUTE_EUR=5.00
EBAY_COMMISSION_PERCENT=12.8
EBAY_FIXED_FEE_EUR=0.35
PAYMENT_PROCESSING_FEE_PERCENT=2.5
SAFETY_PRICE_BUFFER_PERCENT=6.0

# 5. DÉLAIS ANTI-BAN EN PRODUCTION (RECOMMANDÉS)
DELAY_SCRAPE_MIN=5.0
DELAY_SCRAPE_MAX=15.0
DELAY_LISTING_MIN=45.0
DELAY_LISTING_MAX=120.0
DELAY_FULFILLMENT_MIN=20.0
DELAY_FULFILLMENT_MAX=60.0

# QUOTAS STRICTS POUR COMPTE RÉCENT
MAX_LISTINGS_PER_DAY=5
MAX_SCRAPES_PER_HOUR=30
CIRCUIT_BREAKER_COOLDOWN_SEC=1200
```

---

## 🚦 Étape 4 : Protocole de Lancement Progressif

Avant d'activer l'automatisation complète sans surveillance :

1. **Test unitaire d'une première annonce réelle** :
   ```bash
   python cli.py list-items --provider amazon --query "accessoire bureau" --limit 1
   ```
   Vérifiez sur votre compte eBay que l'annonce est bien en ligne, avec les photos, la description, la politique de retour et le prix calculé avec marge.

2. **Surveillance manuelle de la première vente** :
   Dès qu'une vente a lieu sur eBay, lancez :
   ```bash
   python cli.py fulfill
   ```
   Contrôlez que l'adresse du client a été convenablement renseignée chez le fournisseur, que le débit bancaire correspond bien et que le tracking a été transmis à eBay.

3. **Passage en routine périodique** :
   Vous pouvez programmer une tâche planifiée Windows (Planificateur de tâches) pour exécuter :
   - Le traitement des commandes (`python cli.py fulfill`) 3 à 4 fois par jour.
   - La mise en vente d'un quota limité d'articles le matin et en soirée.

---

## 🛡️ Procédure d'Urgence (Rollback)

Si vous constatez un problème (hausse imprévue des prix fournisseur, alerte eBay, etc.) :
1. Remettez immédiatement `SIMULATION_MODE=True` dans `.env`.
2. Le bot cessera toute interaction financière et API avec les plateformes tout en vous permettant de diagnostiquer l'historique dans `dropship.db`.
