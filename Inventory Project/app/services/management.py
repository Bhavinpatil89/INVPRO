from typing import List, Dict, Any, Optional
from ..core.db import (
    create_user, get_users_by_chain, get_stores_by_chain, execute_query,
    get_chain_by_id
)
from ..core.auth import hash_password
from .base import BaseService

class UserService(BaseService):
    """
    Handles Team Management (HQ, Managers, and Staff).
    """
    
    def get_manageable_users(self) -> List[Dict[str, Any]]:
        """Fetch users based on who is logged in."""
        if self.context.is_business_admin():
            # HQ (The Boss) view: See everyone in all branches
            self.context.ensure_chain_access(self.context.chain_id)
            return get_users_by_chain(self.context.chain_id)
            
        elif self.context.is_branch_admin():
            # Manager view: See ONLY staff working in their specific branch
            self.context.ensure_store_access(self.context.store_id)
            return execute_query("SELECT * FROM users WHERE store_id = ?", (self.context.store_id,), fetch_all=True)
            
        else:
            raise PermissionError("Access Denied: You don't have permission to manage users.")

    def create_user(self, username, password, store_id, role='branch_staff', gender=None):
        """
        Create a new user (Staff or Manager).
        """
        # Validate Role
        if role not in ('branch_staff', 'branch_admin'):
             raise ValueError("Invalid user role.")

        target_chain_id = None
        
        # 1. HQ (Boss): Can add Managers or Staff to ANY branch they own
        if self.context.is_business_admin():
            self.context.ensure_chain_access(self.context.chain_id)
            # Make sure the branch belongs to this boss
            stores = get_stores_by_chain(self.context.chain_id)
            if not any(str(s['id']) == str(store_id) for s in stores):
                 raise ValueError("That branch does not belong to your business.")
            target_chain_id = self.context.chain_id

        # 2. Branch Manager: Can add Staff or Managers to THEIR OWN branch
        elif self.context.is_branch_admin():
            if str(self.context.store_id) != str(store_id):
                raise PermissionError("You can only add team members to your own branch.")
            # Managers can create other Managers or Staff within their branch
            target_chain_id = self.context.chain_id
            
        else:
            raise PermissionError("You don't have permission to add users.")

        pwd_hash = hash_password(password)
        create_user(username, pwd_hash, role, target_chain_id, store_id, gender)
        
    def delete_user(self, target_user_id):
        """Delete a user account."""
        if target_user_id == self.context.user_id:
             raise ValueError("You cannot delete your own account while logged in.")

        user = execute_query("SELECT chain_id, store_id, role FROM users WHERE id = ?", (target_user_id,), fetch_one=True)
        if not user: raise ValueError("User not found.")

        # Check permission to delete
        if self.context.is_business_admin():
            # HQ can delete anyone in their business
            if user['chain_id'] != self.context.chain_id:
                raise PermissionError("This user is not in your business.")
                
        elif self.context.is_branch_admin():
            # Manager can delete anyone in their branch (Manager or Staff)
            if user['store_id'] != self.context.store_id:
                raise PermissionError("This user is not in your branch.")
        else:
            raise PermissionError("Access Denied.")

        execute_query("DELETE FROM users WHERE id = ?", (target_user_id,))

    def update_user(self, user_id, username, role, store_id, new_password=None, old_password_to_verify=None):
        """Update a team member's details."""
        if not (self.context.is_business_admin() or self.context.is_branch_admin()):
            raise PermissionError("Access Denied.")

        user = execute_query("SELECT id, chain_id, store_id, role, password_hash FROM users WHERE id = ?", (user_id,), fetch_one=True)
        if not user: raise ValueError("User not found.")

        # Permission Check
        if self.context.is_business_admin():
            if user['chain_id'] != self.context.chain_id:
                raise PermissionError("User outside your business.")
        elif self.context.is_branch_admin():
            if user['store_id'] != self.context.store_id:
                raise PermissionError("User outside your branch.")

        # Change Password if requested
        if new_password:
            from ..core.auth import verify_password, hash_password
            pwd_hash = hash_password(new_password)
            execute_query("UPDATE users SET password_hash = ? WHERE id = ?", (pwd_hash, user_id))

        execute_query(
            "UPDATE users SET username = ?, role = ?, store_id = ? WHERE id = ?",
            (username, role, store_id, user_id)
        )


class ChainService(BaseService):
    """
    Handles Branch/Store Settings for HQ.
    """

    def get_settings(self) -> Dict[str, Any]:
        """Fetch business settings and branch list."""
        if self.context.is_business_admin():
            self.context.ensure_chain_access(self.context.chain_id)
            chain = get_chain_by_id(self.context.chain_id)
            stores = get_stores_by_chain(self.context.chain_id)
        else:
            raise PermissionError("Access Denied: Managers cannot change global settings.")
            
        return {'chain': chain, 'stores': stores}

    def add_node(self, name: str, location: str, chain_id: int = None):
        """Add a new branch."""
        if self.context.is_business_admin():
            target_chain = self.context.chain_id
        else:
            raise PermissionError("Only HQ / Owners can add new branches.")
            
        execute_query(
            "INSERT INTO stores (name, chain_id, location) VALUES (?, ?, ?)",
            (name, target_chain, location)
        )

    def delete_store(self, store_id: int):
        """Delete a branch."""
        if self.context.is_business_admin():
            self.context.ensure_chain_access(self.context.chain_id)
            # Check if this branch belongs to the HQ
            store = execute_query("SELECT chain_id FROM stores WHERE id = ?", (store_id,), fetch_one=True)
            if not store or store['chain_id'] != self.context.chain_id:
                raise PermissionError("This branch does not belong to your business.")
        else:
            raise PermissionError("Only HQ / Owners can delete branches.")
            
        execute_query("DELETE FROM stores WHERE id = ?", (store_id,))

    def update_chain_name(self, name: str):
        """Update the business name."""
        if not self.context.is_business_admin():
             raise PermissionError("Only Business HQ can rename the chain.")
             
        self.context.ensure_chain_access(self.context.chain_id)
        execute_query("UPDATE chains SET name = ? WHERE id = ?", (name, self.context.chain_id))

    def update_node(self, node_id, name, location):
        """Update node details."""
        if not self.context.is_business_admin():
            raise PermissionError("Only Business HQ can rename nodes.")
            
        self.context.ensure_chain_access(self.context.chain_id)
        
        # Verify store belongs to chain
        store = execute_query("SELECT chain_id FROM stores WHERE id = ?", (node_id,), fetch_one=True)
        if not store or store['chain_id'] != self.context.chain_id:
            raise PermissionError("Target Node does not belong to your business.")

        execute_query(
            "UPDATE stores SET name = ?, location = ? WHERE id = ?",
            (name, location, node_id)
        )

    # Alias for routing compatibility
    def add_store(self, name, location, chain_id=None):
        return self.add_node(name, location, chain_id)
