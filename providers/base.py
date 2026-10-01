from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

@dataclass
class SourcedProduct:
    provider: str
    source_id: str
    source_url: str
    title: str
    description: str
    price_eur: float
    shipping_eur: float
    in_stock: bool
    category: str
    images: List[str]

@dataclass
class PurchaseResult:
    success: bool
    source_order_id: Optional[str]
    total_charged_eur: float
    estimated_delivery: str
    error_message: Optional[str] = None

class BaseProvider(ABC):
    name: str

    @abstractmethod
    def search_products(self, query: str, limit: int = 5) -> List[SourcedProduct]:
        """Recherche des produits rentables sur la plateforme source avec temporisation anti-ban."""
        pass

    @abstractmethod
    def get_product_details(self, source_id: str) -> Optional[SourcedProduct]:
        """Récupère les détails frais, le stock et le prix unitaire actuel."""
        pass

    @abstractmethod
    def order_and_ship(self, source_id: str, quantity: int, shipping_address: Dict[str, Any]) -> PurchaseResult:
        """Exécute la commande auprès du fournisseur à destination de l'adresse de l'acheteur eBay."""
        pass
