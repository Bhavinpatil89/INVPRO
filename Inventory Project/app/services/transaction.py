from typing import List, Dict, Any
import uuid
from datetime import datetime

from ..core.db import (
    get_chain_by_id, get_db_connection
)
from ..utils.calculations import calculate_bill_totals
from .base import BaseService
from .configuration import ConfigurationService

class TransactionService(BaseService):
    """
    Handles Sales/Billing Transactions with ACID guarantees and Context enforcement.
    """
    
    def process_sale(self, items: List[Dict[str, Any]], customer_name: str = None, customer_phone: str = None) -> Dict[str, Any]:
        """
        Process a sale transaction with CRM integration.
        """
        self.context.ensure_store_access(self.store_id)
        
        if not items or len(items) == 0:
            raise ValueError("Cannot process sale: Cart is empty.")
            
        config = ConfigurationService(self.context)
        chain_id = self.context.chain_id
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # --- CRM Logic: Resolve or Create Customer ---
            customer_id = None
            if customer_phone:
                # 1. Check if customer exists in this chain
                cursor.execute("SELECT id FROM customers WHERE chain_id = ? AND phone = ?", (chain_id, customer_phone))
                cust_row = cursor.fetchone()
                
                if cust_row:
                    customer_id = cust_row['id']
                    # 2. Update existing customer (if name changed or just visiting)
                    cursor.execute("""
                        UPDATE customers 
                        SET name = COALESCE(?, name), last_visit = CURRENT_TIMESTAMP 
                        WHERE id = ?
                    """, (customer_name, customer_id))
                else:
                    # 3. Create NEW customer
                    cursor.execute("""
                        INSERT INTO customers (chain_id, name, phone, last_visit)
                        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                    """, (chain_id, customer_name or "Guest", customer_phone))
                    customer_id = cursor.lastrowid

            subtotal = 0.0
            total_tax = 0.0
            total_cost = 0.0
            total_profit = 0.0
            bill_items_data = []
            
            for item in items:
                p_id = item['id']
                qty = int(item['qty'])
                
                cursor.execute("""
                    SELECT name, cost_price, selling_price, quantity, category_id 
                    FROM products 
                    WHERE id = ? AND store_id = ?
                """, (p_id, self.store_id))
                product = cursor.fetchone()
                
                if not product:
                    raise ValueError(f"Product ID {p_id} not found.")
                
                if product['quantity'] < qty:
                    raise ValueError(f"Insufficient stock for {product['name']}.")

                selling_price = config.resolve_product_price(p_id, product['selling_price'])
                tax_rate = config.resolve_item_tax(p_id, product['category_id'])
                
                line_subtotal = round(selling_price * qty, 2)
                line_cost = round(product['cost_price'] * qty, 2)
                line_tax = round(line_subtotal * (tax_rate / 100), 2)
                
                subtotal += line_subtotal
                total_tax += line_tax
                total_cost += line_cost
                total_profit += round((selling_price - product['cost_price']) * qty, 2)
                
                bill_items_data.append({
                    'product_id': p_id,
                    'product_name': product['name'],
                    'quantity': qty,
                    'price_at_sale': selling_price,
                    'cost_at_sale': product['cost_price'],
                    'tax_rate_applied': tax_rate,
                    'tax_amount': line_tax
                })
                
                cursor.execute("UPDATE products SET quantity = quantity - ? WHERE id = ?", (qty, p_id))
            
            total_amount = round(subtotal + total_tax, 2)
            
            # --- Loyalty logic: 1% of total as points ---
            if customer_id:
                earned_points = round(total_amount * 0.01, 2)
                cursor.execute("""
                    UPDATE customers 
                    SET loyalty_points = loyalty_points + ?, 
                        total_spent = total_spent + ?
                    WHERE id = ?
                """, (earned_points, total_amount, customer_id))

            # Get Store Name for Snapshot (Preserves history if shop is deleted)
            cursor.execute("SELECT name FROM stores WHERE id = ?", (self.store_id,))
            store_res = cursor.fetchone()
            store_name = store_res['name'] if store_res else "Unknown Shop"

            bill_number = f"INV-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
            
            cursor.execute("""
                INSERT INTO bills (
                    bill_number, subtotal_amount, tax_amount, total_amount, total_cost, total_profit, 
                    store_id, chain_id, store_name_snapshot, user_id, customer_id, customer_name, customer_phone
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                bill_number, round(subtotal, 2), round(total_tax, 2), total_amount, 
                round(total_cost, 2), round(total_profit, 2), self.store_id, self.context.chain_id, 
                store_name, self.context.user_id, customer_id, customer_name, customer_phone
            ))
            bill_id = cursor.lastrowid
            
            # Insert Items
            for item in bill_items_data:
                cursor.execute("""
                    INSERT INTO bill_items (
                        bill_id, product_id, product_name, quantity, 
                        price_at_sale, cost_at_sale, tax_rate_applied, tax_amount
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    bill_id, item['product_id'], item['product_name'], item['quantity'], 
                    item['price_at_sale'], item['cost_at_sale'], item['tax_rate_applied'], item['tax_amount']
                ))
                
            return {
                'bill_number': bill_number, 
                'total_amount': total_amount,
                'subtotal': subtotal,
                'tax_amount': total_tax,
                'total_cost': total_cost,
                'total_profit': total_profit
            }
    
    def get_pos_metadata(self):
        """Get tax rate etc for Frontend."""
        self.context.ensure_store_access(self.store_id)
        config = ConfigurationService(self.context)
        return {
            'tax_rate': config.get_float_setting('tax_rate', 0.0),
            'currency_symbol': config.get_setting('currency_symbol', '₹')
        }
