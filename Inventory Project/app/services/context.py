from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

@dataclass
class UserContext:
    """
    UserContext: The Source of Truth for Authority.
    
    Principles:
    1. Identity: user_id, username
    2. Role: What controls do they have? (business_admin, branch_admin, branch_staff)
    3. Scope: Where can they operate? (chain_id, store_id)
    """
    user_id: int
    username: str
    role: str  
    
    # Scope context
    chain_id: Optional[int] = None
    store_id: Optional[int] = None
    
    def __post_init__(self):
        # Validate Role
        valid_roles = ('business_admin', 'branch_admin', 'branch_staff')
        
        # Legacy mappings for smooth migration
        legacy_map = {
            'node_owner': 'business_admin',
            'main_owner': 'business_admin',
            'user': 'branch_staff',
            'branch_user': 'branch_staff',
            'super_admin': 'business_admin' # Merge platform admin into business admin
        }
        
        if self.role in legacy_map:
            self.role = legacy_map[self.role]
            
        if self.role not in valid_roles:
            # If still invalid, default to lowest privilege for safety
            self.role = 'branch_staff'

    # --- Role Checks ---

    def is_business_admin(self) -> bool:
        """Business Owner (HQ): Controls entire chain."""
        return self.role == 'business_admin'

    def is_main_owner(self) -> bool:
        """Alias for is_business_admin to support legacy checks."""
        return self.is_business_admin()

    def is_branch_admin(self) -> bool:
        """Store Manager: Controls single branch."""
        return self.role == 'branch_admin'

    def is_branch_staff(self) -> bool:
        """POS Operator: Execution only."""
        return self.role == 'branch_staff'

    # --- Scope Enforcement ---

    def ensure_chain_access(self, target_chain_id: int):
        """
        Confirms user authorization for a specific Business Chain.
        """
        if not self.chain_id:
            raise PermissionError("User is not attached to any business chain.")

        if self.chain_id != target_chain_id:
            raise PermissionError(f"Access Denied: User belongs to Chain {self.chain_id}, attempted access to {target_chain_id}")

    def ensure_store_access(self, target_store_id: int):
        """
        Confirms user authorization for a specific Physical Branch.
        """
        # Business Admin can access ANY store in their chain
        if self.is_business_admin():
            self.ensure_chain_access(self.chain_id)
            # HQ is not locked to a specific branch
            return

        # Branch Admin/Staff are strictly locked to their assigned store
        if not self.store_id:
            raise PermissionError("User is not assigned to any branch.")

        if self.store_id != target_store_id:
            raise PermissionError(f"Access Denied: User locked to Branch {self.store_id}, attempted access to {target_store_id}")

    def can_manage_users(self) -> bool:
        """
        Business Admin: Can manage all users in chain.
        Branch Admin: Can manage staff in their branch.
        """
        return self.is_business_admin() or self.is_branch_admin()

    def can_manage_inventory_structure(self) -> bool:
        """
        Only Business Admin (HQ) can change categories/tax/global rules.
        """
        return self.is_business_admin()
