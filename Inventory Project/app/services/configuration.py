from typing import Any, Optional, Dict
from ..core.db import upsert_setting, get_settings_by_scope, get_chain_by_id
from .base import BaseService

class ConfigurationService(BaseService):
    """
    Manages application settings with a hierarchy:
    Store Level > Chain Level > Defaults
    """

    DEFAULTS = {
        'tax_rate': '0.0',
        'currency_symbol': '₹',
        'low_stock_threshold': '5',
        'enable_reports': 'true',
        'theme': 'light'
    }

    def get_setting(self, key: str, default: Any = None) -> str:
        """
        Retrieve a setting value respecting the hierarchy.
        Store settings override Chain settings.
        """
        # 1. Check Store Level (if in store context)
        if self.store_id:
            store_settings = get_settings_by_scope('store', self.store_id)
            if key in store_settings:
                return store_settings[key]

        # 2. Check Chain Level
        if self.chain_id:
            chain_settings = get_settings_by_scope('chain', self.chain_id)
            if key in chain_settings:
                return chain_settings[key]
            
            # Fallback: Migration compatibility for 'tax_rate'
            # (If not in settings but exists in chains table legacy column)
            if key == 'tax_rate':
                chain = get_chain_by_id(self.chain_id)
                if chain and chain['tax_rate'] is not None:
                    return str(chain['tax_rate'])

        # 3. Default
        return default if default is not None else self.DEFAULTS.get(key, '')

    def get_float_setting(self, key: str, default: float = 0.0) -> float:
        try:
            return float(self.get_setting(key, str(default)))
        except ValueError:
            return default

    def get_bool_setting(self, key: str, default: bool = False) -> bool:
        val = self.get_setting(key, str(default)).lower()
        return val in ('true', '1', 'yes', 'on')

    def get_settings_by_scope(self, scope: str, scope_id: int) -> Dict[str, str]:
        """Proxy to DB layer for scoped settings."""
        return get_settings_by_scope(scope, scope_id)

    def set_chain_setting(self, key: str, value: Any):
        """
        Set a setting at the Chain scope. Only Main Owners.
        """
        self.context.ensure_chain_access(self.chain_id)
        if not self.context.is_main_owner():
            raise PermissionError("Only the Main Owner can modify chain settings.")
        
        upsert_setting('chain', self.chain_id, key, value)

    def resolve_product_price(self, product_id: int, base_selling_price: float) -> float:
        """
        Resolves the final selling price:
        1. Branch Price Override (Store Scope)
        2. HQ Default Price (Base from DB)
        """
        if self.store_id:
            key = f"price_override_{product_id}"
            override = self.get_setting(key, None)
            if override is not None:
                try:
                    return float(override)
                except ValueError:
                    pass
        return base_selling_price

    def set_store_setting(self, key: str, value: Any):
        """
        Set a setting at the Store scope.
        """
        self.context.ensure_store_access(self.store_id)
        # Assuming Owners and maybe Managers can change store settings.
        # For Phase 1/Prompt 4 strictness: Owner only or Branch User?
        # "Branch User: Can read relevant settings... Cannot change global behavior"
        # Since Store settings aren't global, maybe they can?
        # "If permissions are unclear -> restrict by default." -> Owner Only for now.
        # Owners and Store Managers can change store settings
        if not self.context.is_business_admin() and not self.context.is_branch_admin():
             raise PermissionError("Permission denied: Only HQ or Branch Managers can modify store settings.")
             
        upsert_setting('store', self.store_id, key, value)

    def set_item_tax_override(self, product_id: int, tax_percentage: float):
        """
        Explicitly set a tax override for a specific product.
        Branch Managers save to Store scope, HQ saves to Chain scope.
        """
        key = f"tax_product_{product_id}"
        if self.context.is_business_admin():
            self.set_chain_setting(key, str(tax_percentage))
        else:
            self.set_store_setting(key, str(tax_percentage))

    def resolve_item_tax(self, product_id: int, category_id: int) -> float:
        """
        Resolves the tax rate for a specific item based on the priority:
        1. Branch Product Tax (Store Scope)
        2. Branch Category Tax (Store Scope)
        3. Chain Product Tax (Chain Scope)
        4. Chain Category Tax (Chain Scope)
        5. Chain Universal Tax (Chain Scope, fallback)
        """
        # Keys for settings
        p_key = f"tax_product_{product_id}"
        c_key = f"tax_category_{category_id}"

        # 1. Branch Product (Store Scope)
        if self.store_id:
            val = self.get_setting(p_key, None) # Use direct lookup to avoid recursion if get_setting changes
            # Wait, get_setting already does hierarchy. I need to check specific scopes.
            # Let's use get_settings_by_scope directly for precision.
            store_settings = get_settings_by_scope('store', self.store_id)
            if p_key in store_settings:
                return float(store_settings[p_key])
            
            # 2. Branch Category (Store Scope)
            if c_key in store_settings:
                return float(store_settings[c_key])

        # 3. Chain Scope
        if self.chain_id:
            chain_settings = get_settings_by_scope('chain', self.chain_id)
            
            # 3. Chain Product Override (Explicitly set per product)
            if p_key in chain_settings:
                return float(chain_settings[p_key])
            
            # 4. Chain Policy (New: Scoped by Category)
            from .tax import TaxService
            tax_service = TaxService(self.context)
            return tax_service.resolve_tax_rate(category_id)

        # Final Fallback to DEFAULTS
        return float(self.DEFAULTS.get('tax_rate', '0.0'))
