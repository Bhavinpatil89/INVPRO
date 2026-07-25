from typing import List, Dict, Any, Optional
from ..core.db import (
    get_products_by_store, create_product, update_product_details, delete_product,
    get_categories_by_chain, create_category, update_category, delete_category,
    search_products, get_product_for_update
)
from ..utils.calculations import calculate_profit_metrics
from .base import BaseService

class InventoryService(BaseService):
    """
    Handles Inventory Operations (Products, Categories) with strict Context enforcement.
    """

    def get_product_by_id(self, product_id: int) -> Optional[Dict[str, Any]]:
        self.context.ensure_store_access(self.store_id)
        res = get_product_for_update(product_id, self.store_id)
        return dict(res) if res else None

    # --- PRODUCTS (Store Scope) ---

    def get_store_products(self) -> List[Dict[str, Any]]:
        """Get all products for the current store context, enriched with metrics and tax."""
        self.context.ensure_store_access(self.store_id)
        
        from .configuration import ConfigurationService
        config = ConfigurationService(self.context)
        
        raw_products = get_products_by_store(self.store_id)
        results = []
        for p in raw_products:
            p_dict = dict(p)
            # Resolve Effective Price (Branch Override > HQ Default)
            p_dict['selling_price'] = config.resolve_product_price(p_dict['id'], p_dict['selling_price'])
            
            # Enrich with calculated metrics
            metrics = calculate_profit_metrics(p_dict['cost_price'], p_dict['selling_price'], p_dict['quantity'])
            p_dict.update(metrics)
            
            # Resolve Effective Tax
            p_dict['effective_tax'] = config.resolve_item_tax(p_dict['id'], p_dict['category_id'])
            
            p_dict['velocity_class'] = 'N/A' 
            
            results.append(p_dict)
        return results

    def search_products(self, term: str) -> List[Dict[str, Any]]:
        self.context.ensure_store_access(self.store_id)
        from .configuration import ConfigurationService
        config = ConfigurationService(self.context)
        
        raw_products = search_products(self.store_id, term)
        results = []
        for p in raw_products:
            p_dict = dict(p)
            # Resolve Effective Price
            p_dict['selling_price'] = config.resolve_product_price(p_dict['id'], p_dict['selling_price'])
            
            metrics = calculate_profit_metrics(p_dict['cost_price'], p_dict['selling_price'], p_dict['quantity'])
            p_dict.update(metrics)
            
            p_dict['effective_tax'] = config.resolve_item_tax(p_dict['id'], p_dict['category_id'])
            
            results.append(p_dict)
        return results

    def add_product(self, data: Dict[str, Any]):
        """
        Add product to current store.
        Strict enforcement: Only HQ can create direct entries (usually during setup).
        Managers must use the Import Registry flow.
        """
        self.context.ensure_store_access(self.store_id)
        if not self.context.is_business_admin():
            raise PermissionError("Direct creation restricted. Please use 'Import from HQ' to add stock.")
        
        # Validation
        if data['cost_price'] < 0 or data['selling_price'] < 0 or data['quantity'] < 0:
            raise ValueError("Negative values are not allowed.")

        # Inject Store ID from Context (Security)
        data['store_id'] = self.store_id
        # Default global_product_id to None if not provided (manual HQ entry)
        if 'global_product_id' not in data:
            data['global_product_id'] = None
        
        create_product(data)

    def update_product(self, product_id: int, data: Dict[str, Any]):
        self.context.ensure_store_access(self.store_id)
        
        # Validation
        cost = data.get('cost_price')
        sell = data.get('selling_price')
        qty = data.get('quantity')
        
        if (cost is not None and cost < 0) or \
           (sell is not None and sell < 0) or \
           (qty is not None and qty < 0):
            raise ValueError("Negative values are not allowed.")
        
        # Verify ownership before update
        existing = get_product_for_update(product_id, self.store_id)
        if not existing:
            raise ValueError("Product not found or access denied.")
            
        # Context-Aware Update Logic
        if self.context.is_business_admin():
            # HQ Update: Modify core record (The "Default")
            update_product_details(product_id, self.store_id, data)
        else:
            # Branch Update: Local Price Override & Stock only
            # Prices are stored in Settings as 'price_override_{id}'
            from .configuration import ConfigurationService
            config = ConfigurationService(self.context)
            
            if sell is not None:
                config.set_store_setting(f"price_override_{product_id}", str(sell))
                # Remove selling_price from data to avoid updating base record
                data.pop('selling_price')
            
            # Other details (Name, Category) are HQ-only for core, 
            # but InventoryService might still allow if not restricted in DB method.
            # We'll stick to Quantity and Name if permitted.
            # Usually Branch Managers only update Quantity and maybe Cost Price locally?
            # User said: "Branch Manager can edit price for that sole branch"
            update_product_details(product_id, self.store_id, data)

    def update_product_quantity(self, product_id: int, new_quantity: int):
        """Execution-only action for Managers/Staff if permitted."""
        self.context.ensure_store_access(self.store_id)
        if new_quantity < 0:
            raise ValueError("Quantity cannot be negative.")
            
        existing = get_product_for_update(product_id, self.store_id)
        if not existing:
            raise ValueError("Product not found.")
            
        update_product_details(product_id, self.store_id, {'quantity': new_quantity})

    def delete_product(self, product_id: int):
        self.context.ensure_store_access(self.store_id)
        delete_product(product_id, self.store_id)

    def get_chain_products(self) -> List[Dict[str, Any]]:
        """Used by HQ to see everything."""
        self.context.ensure_chain_access(self.chain_id)
        # Fetch all products in chain
        from ..core.db import get_products_by_chain
        return get_products_by_chain(self.chain_id)

    # --- CATEGORIES (Chain Scope) ---

    def get_chain_categories(self) -> List[Dict[str, Any]]:
        self.context.ensure_chain_access(self.chain_id)
        return get_categories_by_chain(self.chain_id)

    def add_category(self, name: str):
        self.context.ensure_chain_access(self.chain_id)
        if not self.context.can_manage_inventory_structure():
            raise PermissionError("Only HQ can define clusters.")
            
        create_category(name, self.chain_id)

    def update_category(self, category_id: int, name: str):
        self.context.ensure_chain_access(self.chain_id)
        if not self.context.can_manage_inventory_structure():
            raise PermissionError("Cluster structural protocols are HQ-only.")
        update_category(category_id, name, self.chain_id)

    def delete_category(self, category_id: int):
        self.context.ensure_chain_access(self.chain_id)
        if not self.context.can_manage_inventory_structure():
             raise PermissionError("Cluster deletion is an HQ-level action.")
        delete_category(category_id, self.chain_id)
