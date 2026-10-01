import math
from dataclasses import dataclass
from config import cfg

@dataclass
class PriceCalculation:
    supplier_cost_eur: float
    supplier_shipping_eur: float
    total_cost_eur: float
    selling_price_eur: float
    ebay_fee_eur: float
    payment_fee_eur: float
    safety_buffer_eur: float
    net_profit_eur: float
    margin_percent: float
    is_profitable: bool

def calculate_selling_price(supplier_cost_eur: float, supplier_shipping_eur: float = 0.0) -> PriceCalculation:
    """
    Calcule le prix de vente optimal sur eBay en intégrant :
    - Le coût d'achat fournisseur + livraison fournisseur
    - La commission finale eBay (ex: 12.8% + 0.35€)
    - Les frais de traitement bancaire / change (ex: 2.5%)
    - Un tampon de sécurité contre les hausses de prix subites (ex: 5%)
    - La marge bénéficiaire ciblée (ex: 25% minimum ou 5.00€)
    - L'arrondi psychologique (.99€)
    """
    total_cost = supplier_cost_eur + supplier_shipping_eur
    
    # Marge brute souhaitée : minimum en % ou minimum absolu
    target_profit = max(total_cost * (cfg.MIN_PROFIT_MARGIN_PERCENT / 100.0), cfg.MIN_PROFIT_ABSOLUTE_EUR)
    
    # Formule analytique :
    # PrixVente = (TotalCost + FixedFee + TargetProfit) / (1 - (CommissionPct + PaymentPct + BufferPct))
    variable_fee_rate = (cfg.EBAY_COMMISSION_PERCENT + cfg.PAYMENT_PROCESSING_FEE_PERCENT + cfg.SAFETY_PRICE_BUFFER_PERCENT) / 100.0
    
    if variable_fee_rate >= 0.95:
        variable_fee_rate = 0.80 # Protection division par zéro
        
    raw_selling_price = (total_cost + cfg.EBAY_FIXED_FEE_EUR + target_profit) / (1.0 - variable_fee_rate)
    
    # Application de l'arrondi psychologique en .99 (ex: 24.32 -> 24.99)
    base_int = math.floor(raw_selling_price)
    suggested_price = float(base_int) + 0.99
    if suggested_price < raw_selling_price:
        suggested_price += 1.0 # Toujours au-dessus du plancher de marge
        
    suggested_price = round(suggested_price, 2)
    
    # Décomposition exacte des frais finaux au prix fixé
    ebay_fee = round(suggested_price * (cfg.EBAY_COMMISSION_PERCENT / 100.0) + cfg.EBAY_FIXED_FEE_EUR, 2)
    payment_fee = round(suggested_price * (cfg.PAYMENT_PROCESSING_FEE_PERCENT / 100.0), 2)
    safety_buffer = round(suggested_price * (cfg.SAFETY_PRICE_BUFFER_PERCENT / 100.0), 2)
    
    net_profit = round(suggested_price - total_cost - ebay_fee - payment_fee, 2)
    margin_pct = round((net_profit / suggested_price) * 100.0, 1) if suggested_price > 0 else 0.0
    
    is_profitable = (net_profit >= cfg.MIN_PROFIT_ABSOLUTE_EUR) and (margin_pct >= cfg.MIN_PROFIT_MARGIN_PERCENT * 0.8)
    
    return PriceCalculation(
        supplier_cost_eur=round(supplier_cost_eur, 2),
        supplier_shipping_eur=round(supplier_shipping_eur, 2),
        total_cost_eur=round(total_cost, 2),
        selling_price_eur=suggested_price,
        ebay_fee_eur=ebay_fee,
        payment_fee_eur=payment_fee,
        safety_buffer_eur=safety_buffer,
        net_profit_eur=net_profit,
        margin_percent=margin_pct,
        is_profitable=is_profitable
    )
