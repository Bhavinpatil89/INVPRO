from typing import List, Dict, Any, Optional
from ..core.db import execute_query, get_db_connection
from .base import BaseService

class TaxService(BaseService):
    """
    Manages Tax Policies at the Chain level.
    Taxes are named entities scoped to specific categories.
    """

    def get_all_policies(self) -> List[Dict[str, Any]]:
        self.context.ensure_chain_access(self.chain_id)
        policies = execute_query(
            "SELECT * FROM tax_policies WHERE chain_id = ? ORDER BY created_at DESC",
            (self.chain_id,),
            fetch_all=True
        )
        
        # Hydrate with categories
        hydrated = []
        for p in policies:
            p_dict = dict(p)
            cat_ids = execute_query(
                "SELECT category_id FROM tax_policy_categories WHERE tax_id = ?",
                (p['id'],),
                fetch_all=True
            )
            p_dict['category_ids'] = [r['category_id'] for r in cat_ids]
            hydrated.append(p_dict)
            
        return hydrated

    def create_policy(self, name: str, percentage: float, is_all: bool, category_ids: List[int]) -> int:
        self.context.ensure_chain_access(self.chain_id)
        if not self.context.is_business_admin():
            raise PermissionError("Only Business HQ can create tax policies.")

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO tax_policies (chain_id, name, percentage, is_all_categories) VALUES (?, ?, ?, ?)",
                (self.chain_id, name, percentage, 1 if is_all else 0)
            )
            tax_id = cursor.lastrowid

            if not is_all and category_ids:
                for cat_id in category_ids:
                    cursor.execute(
                        "INSERT INTO tax_policy_categories (tax_id, category_id) VALUES (?, ?)",
                        (tax_id, cat_id)
                    )
            return tax_id

    def update_policy(self, policy_id: int, name: str, percentage: float, is_all: bool, category_ids: List[int]):
        self.context.ensure_chain_access(self.chain_id)
        if not self.context.is_business_admin():
            raise PermissionError("Only Business HQ can update tax policies.")

        # Ensure policy belongs to chain
        policy = execute_query(
            "SELECT id FROM tax_policies WHERE id = ? AND chain_id = ?",
            (policy_id, self.chain_id),
            fetch_one=True
        )
        if not policy:
            raise ValueError("Policy not found or access denied.")

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE tax_policies SET name = ?, percentage = ?, is_all_categories = ? WHERE id = ?",
                (name, percentage, 1 if is_all else 0, policy_id)
            )

            # Refresh categories
            cursor.execute("DELETE FROM tax_policy_categories WHERE tax_id = ?", (policy_id,))
            if not is_all and category_ids:
                for cat_id in category_ids:
                    cursor.execute(
                        "INSERT INTO tax_policy_categories (tax_id, category_id) VALUES (?, ?)",
                        (policy_id, cat_id)
                    )

    def delete_policy(self, policy_id: int):
        self.context.ensure_chain_access(self.chain_id)
        if not self.context.is_business_admin():
            raise PermissionError("Only Business HQ can delete tax policies.")

        # Ensure ownership
        execute_query(
            "DELETE FROM tax_policies WHERE id = ? AND chain_id = ?",
            (policy_id, self.chain_id)
        )

    def resolve_tax_rate(self, category_id: int) -> float:
        """
        Resolves the tax rate for a category.
        1. Category-specific policy (most recent)
        2. Universal policy (is_all_categories = 1, most recent)
        """
        # Specific match
        query = """
            SELECT p.percentage 
            FROM tax_policies p
            JOIN tax_policy_categories tpc ON p.id = tpc.tax_id
            WHERE p.chain_id = ? AND tpc.category_id = ?
            ORDER BY p.created_at DESC LIMIT 1
        """
        res = execute_query(query, (self.chain_id, category_id), fetch_one=True)
        if res:
            return float(res['percentage'])

        # Universal match
        query = "SELECT percentage FROM tax_policies WHERE chain_id = ? AND is_all_categories = 1 ORDER BY created_at DESC LIMIT 1"
        res = execute_query(query, (self.chain_id,), fetch_one=True)
        if res:
            return float(res['percentage'])

        return 0.0
