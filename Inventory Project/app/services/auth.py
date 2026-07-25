from typing import Optional, Tuple
from ..core.db import (
    get_user_by_username, create_user, create_chain, create_store, 
    update_user_chain, get_chain_by_user, get_stores_by_chain, get_user_by_id
)
from ..core.auth import hash_password, verify_password
from .context import UserContext

class AuthService:
    """
    Handles User Authentication, Registration Orchestration, and Context Building.
    """
    
    def authenticate(self, username, password) -> Optional[dict]:
        """
        Verify credentials. Returns user dict if valid, None otherwise.
        """
        user = get_user_by_username(username)
        if user and verify_password(password, user['password_hash']):
            return user
        return None

    def register_chain_owner(self, username, password, chain_name) -> Tuple[int, int, int]:
        """
        Setup a new Shop/Business:
        1. Create User (Shop Owner)
        2. Create Business Identity (Hierarchy placeholder)
        3. Link User to Business
        4. Setup Head Office
        
        Returns: (user_id, chain_id, store_id)
        """
        if get_user_by_username(username):
            raise ValueError("Username already exists.")

        # 1. Create User as 'business_admin' (HQ Owner)
        password_hash = hash_password(password)
        user_id = create_user(username, password_hash, role='business_admin', chain_id=None, store_id=None)

        # 2. Create Chain
        chain_id = create_chain(chain_name, owner_user_id=user_id)

        # 3. Link
        update_user_chain(user_id, chain_id)

        # 4. Return Context (Store ID is None for HQ)
        return user_id, chain_id, None

    def build_user_context(self, user_id: int, session_chain_id: int = None, session_store_id: int = None) -> UserContext:
        user = get_user_by_id(user_id)
        if not user:
            raise ValueError("User not found.")

        # Resolve Identity
        raw_role = user['role']
        
        # Hydrate Scope Base
        db_chain_id = user['chain_id']
        db_store_id = user['store_id']
        
        final_role = raw_role
        final_chain = None
        final_store = None

        # Logic Matrix
        if raw_role in ('node_owner', 'business_admin', 'main_owner'):
            final_role = 'business_admin'
            # Owner owns the chain.
            if not db_chain_id:
                # Fallback to ownership lookup if not cached in user row
                chain = get_chain_by_user(user_id)
                final_chain = chain['id'] if chain else None
            else:
                final_chain = db_chain_id
                
            # Owner can view specific shop details, but isn't locked to one.
            # If session requests a specific shop, and it belongs to their business, allow it.
            if session_store_id:
                # Validation: Does this shop belong to their business?
                from ..core.db import get_all_stores_by_chain
                stores = get_all_stores_by_chain(final_chain)
                if any(s['id'] == int(session_store_id) for s in stores):
                     final_store = int(session_store_id)
            elif db_store_id:
                 final_store = db_store_id
                 
        elif raw_role in ('branch_admin', 'store_manager'):
            final_role = 'branch_admin'
            final_chain = db_chain_id
            final_store = db_store_id # Locked
            
        elif raw_role in ('branch_staff', 'branch_user', 'user'):
            final_role = 'branch_staff'
            final_chain = db_chain_id
            final_store = db_store_id # Locked
            
        return UserContext(
            user_id=user['id'],
            username=user['username'],
            role=final_role,
            chain_id=final_chain,
            store_id=final_store
        )
