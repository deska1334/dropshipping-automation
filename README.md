# Bot de Dropshipping Automatisé & Système Anti-Ban

Ce dossier contient une solution complète et modulaire de dropshipping automatisé avec protection algorithmique contre les bannissements.

---

## 🎯 Architecture et Fonctionnalités

1. **Sourçage Multi-Fournisseurs (`providers/`)** :
   - Recherche d'articles à bas prix sur **Amazon** et **AliExpress**.
   - Extraction des photos, descriptions, stocks et prix d'expédition.

2. **Moteur de Calcul de Marges & Frais (`pricing.py`)** :
   - Calcul automatique du prix optimal sur eBay intégrant :
     - Frais eBay (12.8% + 0.35 €).
     - Frais de transaction et conversion bancaire (2.5%).
     - Tampon de sécurité contre la volatilité des prix fournisseur (5%).
     - Marge bénéficiaire nette minimale garantie (25% ou 5.00 € minimum).
     - Arrondi psychologique en `.99 €`.

3. **Intégration eBay (`platforms/ebay.py`)** :
   - Publication des annonces via l'API REST d'inventaire eBay.
   - Surveillance des commandes avec paiement validé (`status: PAID`).
   - Transmission automatique du numéro de suivi transporteur (Colissimo, La Poste, AliExpress Standard).

4. **Achat et Expédition Automatiques (`fulfillment.py`)** :
   - Dès qu'un client paye sur eBay, le système extrait l'adresse exacte (Nom, Rue, Ville, Code Postal).
   - Passe la commande sur le site source (Amazon / AliExpress) à destination directe du client.
   - Enregistre le numéro de commande fournisseur et notifie eBay avec le numéro de suivi.

---

## 🛡️ Système Anti-Ban & Délais de Discrétion (`stealth.py`)

Les plateformes (eBay, Amazon, AliExpress) disposent d'algorithmes sophistiqués détectant les automates et sanctionnant le "retail arbitrage" agressif. Pour contourner ces risques, le système intègre :

1. **Jitter Gaussien Non-Linéaire** :
   - Chaque action (recherche, listing, achat) est séparée par des pauses aléatoires modélisées par une distribution normale (loi gaussienne) avec micro-bruit.
   - Jamais deux requêtes ne sont envoyées à intervalle fixe.

2. **Quotas Journaliers Adaptatifs (Anti-Suspension eBay)** :
   - Un nouveau compte eBay publiant 50 annonces en 1 heure est immédiatement suspendu (MC011 / vérification d'identité).
   - Le système applique une limite stricte (`MAX_LISTINGS_PER_DAY = 15`) et espace chaque publication de 30 à 90 secondes.

3. **Rotation de Headers & User-Agents Réalistes** :
   - Empreintes HTTP authentiques (Chrome 128+, Edge, Firefox sur Windows et macOS).
   - En-têtes Client Hints (`Sec-CH-UA`, `Sec-Fetch-Dest`, `Sec-Fetch-Mode`).

4. **Coupe-Circuit Automatique (Circuit Breaker)** :
   - Si un CAPTCHA, une erreur HTTP 429 (Trop de requêtes) ou un blocage Cloudflare/Akamai est détecté, le système suspend automatiquement les requêtes pendant 15 minutes (`CIRCUIT_BREAKER_COOLDOWN_SEC`) plutôt que d'insister et de provoquer un ban IP/compte définitif.

---

## 🚀 Guide d'Utilisation Immédiate

### 1. Consulter l'état du système
```bash
python cli.py status
```

### 2. Tester le cycle complet (Simulation 100% fonctionnelle)
Cette commande exécute le cycle de bout en bout :
Sourçage -> Calcul de marge -> Mise en vente eBay -> Achat simulé par un acheteur français -> Commande automatique chez le fournisseur -> Expédition et numéro de suivi -> Calcul du bénéfice net.
```bash
python cli.py test-flow
```

### 3. Rechercher des articles
```bash
python cli.py search --provider amazon --query "montre connectee" --limit 3
python cli.py search --provider aliexpress --query "lampe solaire" --limit 3
```

### 4. Mettre en vente sur eBay
```bash
python cli.py list-items --provider amazon --query "projecteur" --limit 1
```

### 5. Traiter les commandes payées
```bash
python cli.py fulfill
```

---

## ⚙️ Configuration en Mode Réel (.env)

Pour basculer du mode simulation au mode réel :
1. Modifiez le fichier `.env` :
   ```env
   SIMULATION_MODE=False
   EBAY_ENVIRONMENT=PRODUCTION
   EBAY_USER_TOKEN=votre_vrai_token_oauth
   ```
2. Renseignez vos identifiants marchands (Amazon PA-API / AliExpress Dropshipping API).


## Demarrage Rapide avec StartBot

Vous pouvez demarrer le bot instantanement avec le script lanceur :
- **Double-clic sur `startbot.bat`** (Windows)
- Ou en ligne de commande :
  ```bash
  # Mode interactif
  python startbot.py
  # Ou direct en daemon
  python startbot.py --daemon
  ```
