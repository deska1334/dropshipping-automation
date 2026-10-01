import sqlite3
import json
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

DB_FILE = Path(__file__).parent / "dropship.db"

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_FILE))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cur = conn.cursor()
    
    # Table des articles sourcés (fournisseurs)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        provider TEXT NOT NULL,
        source_id TEXT UNIQUE NOT NULL,
        source_url TEXT,
        title TEXT NOT NULL,
        description TEXT,
        price_eur REAL NOT NULL,
        shipping_eur REAL DEFAULT 0.0,
        in_stock INTEGER DEFAULT 1,
        category TEXT,
        images_json TEXT,
        last_checked TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Table des annonces eBay publiées
    cur.execute("""
    CREATE TABLE IF NOT EXISTS listings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        ebay_item_id TEXT UNIQUE,
        title TEXT NOT NULL,
        supplier_cost_eur REAL NOT NULL,
        selling_price_eur REAL NOT NULL,
        estimated_profit_eur REAL NOT NULL,
        stock_quantity INTEGER DEFAULT 1,
        status TEXT DEFAULT 'DRAFT', -- DRAFT, ACTIVE, PAUSED, ENDED
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (product_id) REFERENCES products(id)
    );
    """)

    # Table des commandes clients et traitement d'achat automatisé
    cur.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ebay_order_id TEXT UNIQUE NOT NULL,
        ebay_item_id TEXT NOT NULL,
        buyer_username TEXT,
        buyer_name TEXT NOT NULL,
        buyer_address_json TEXT NOT NULL,
        total_paid_eur REAL NOT NULL,
        status TEXT DEFAULT 'PAID', -- PAID, SOURCING_ORDERED, SHIPPED, FAILED, COMPLETED
        source_order_id TEXT,
        tracking_number TEXT,
        carrier TEXT,
        purchase_cost_eur REAL DEFAULT 0.0,
        actual_profit_eur REAL DEFAULT 0.0,
        error_message TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Journal d'activités et d'événements anti-ban
    cur.execute("""
    CREATE TABLE IF NOT EXISTS activity_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        level TEXT NOT NULL,
        category TEXT NOT NULL,
        message TEXT NOT NULL,
        details_json TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    conn.commit()
    conn.close()

# Fonctions CRUD simplifiées
def upsert_product(provider: str, source_id: str, title: str, price_eur: float, 
                   shipping_eur: float = 0.0, in_stock: bool = True,
                   source_url: str = "", description: str = "", 
                   category: str = "", images: List[str] = None) -> int:
    conn = get_connection()
    cur = conn.cursor()
    images_str = json.dumps(images or [])
    
    cur.execute("""
    INSERT INTO products (provider, source_id, source_url, title, description, price_eur, shipping_eur, in_stock, category, images_json, last_checked)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    ON CONFLICT(source_id) DO UPDATE SET
        price_eur = excluded.price_eur,
        shipping_eur = excluded.shipping_eur,
        in_stock = excluded.in_stock,
        last_checked = CURRENT_TIMESTAMP
    """, (provider, source_id, source_url, title, description, price_eur, shipping_eur, 1 if in_stock else 0, category, images_str))
    
    product_id = cur.lastrowid
    if not product_id:
        cur.execute("SELECT id FROM products WHERE source_id = ?", (source_id,))
        row = cur.fetchone()
        product_id = row["id"] if row else None
        
    conn.commit()
    conn.close()
    return product_id

def create_or_update_listing(product_id: int, ebay_item_id: str, title: str,
                            supplier_cost: float, selling_price: float, profit: float,
                            status: str = "ACTIVE") -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
    INSERT INTO listings (product_id, ebay_item_id, title, supplier_cost_eur, selling_price_eur, estimated_profit_eur, status, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    ON CONFLICT(ebay_item_id) DO UPDATE SET
        supplier_cost_eur = excluded.supplier_cost_eur,
        selling_price_eur = excluded.selling_price_eur,
        estimated_profit_eur = excluded.estimated_profit_eur,
        status = excluded.status,
        updated_at = CURRENT_TIMESTAMP
    """, (product_id, ebay_item_id, title, supplier_cost, selling_price, profit, status))
    listing_id = cur.lastrowid
    conn.commit()
    conn.close()
    return listing_id

def get_product_by_id(product_id: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM products WHERE id = ?", (product_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

def get_listing_by_ebay_id(ebay_item_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM listings WHERE ebay_item_id = ?", (ebay_item_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

def save_order(ebay_order_id: str, ebay_item_id: str, buyer_username: str, buyer_name: str,
               address_dict: Dict[str, Any], total_paid: float) -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
    INSERT INTO orders (ebay_order_id, ebay_item_id, buyer_username, buyer_name, buyer_address_json, total_paid_eur, status)
    VALUES (?, ?, ?, ?, ?, ?, 'PAID')
    ON CONFLICT(ebay_order_id) DO NOTHING
    """, (ebay_order_id, ebay_item_id, buyer_username, buyer_name, json.dumps(address_dict), total_paid))
    order_id = cur.lastrowid
    conn.commit()
    conn.close()
    return order_id

def update_order_fulfillment(ebay_order_id: str, status: str, source_order_id: str = None,
                            tracking_number: str = None, carrier: str = None,
                            purchase_cost: float = None, actual_profit: float = None,
                            error_message: str = None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
    UPDATE orders SET
        status = ?,
        source_order_id = COALESCE(?, source_order_id),
        tracking_number = COALESCE(?, tracking_number),
        carrier = COALESCE(?, carrier),
        purchase_cost_eur = COALESCE(?, purchase_cost_eur),
        actual_profit_eur = COALESCE(?, actual_profit_eur),
        error_message = ?,
        updated_at = CURRENT_TIMESTAMP
    WHERE ebay_order_id = ?
    """, (status, source_order_id, tracking_number, carrier, purchase_cost, actual_profit, error_message, ebay_order_id))
    conn.commit()
    conn.close()

def log_activity(level: str, category: str, message: str, details: Dict[str, Any] = None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO activity_logs (level, category, message, details_json) VALUES (?, ?, ?, ?)",
                (level, category, message, json.dumps(details or {})))
    conn.commit()
    conn.close()

# Initialisation au chargement
init_db()
