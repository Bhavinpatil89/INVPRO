"""
User management routes with strict data isolation.
HQ can manage all users, Branch Managers can only manage their branch users.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from ..core.auth import login_required, hash_password
from ..services.auth import AuthService
from ..services.management import UserService

users_bp = Blueprint('users', __name__)
auth_service = AuthService()

def get_user_service():
    context = auth_service.build_user_context(
        session.get('user_id'), 
        session_chain_id=session.get('chain_id'),
        session_store_id=session.get('store_id')
    )
    return UserService(context)

@users_bp.route('/')
@login_required
def manage_users():
    """Team management page."""
    try:
        return render_template('users/manage.html')
    except Exception as e:
        flash(str(e), 'error')
        return redirect(url_for('main.dashboard'))

# ==================== USER MANAGEMENT API (INVPRO) ====================

@users_bp.route('/api/users', methods=['GET'])
@login_required
def get_users_api():
    """Get users based on role - HQ sees all, Branch Managers see only their branch"""
    try:
        from ..core.db import execute_query
        chain_id = session.get('chain_id')
        role = session.get('role')
        store_id = session.get('store_id')
        
        # HQ sees all users in the chain
        if role == 'business_admin':
            users = execute_query("""
                SELECT u.*, s.name as store_name
                FROM users u
                LEFT JOIN stores s ON u.store_id = s.id
                WHERE u.chain_id = ?
                ORDER BY u.created_at DESC
            """, (chain_id,), fetch_all=True)
        # Branch Managers see only their branch users
        else:
            users = execute_query("""
                SELECT u.*, s.name as store_name
                FROM users u
                LEFT JOIN stores s ON u.store_id = s.id
                WHERE u.chain_id = ? AND u.store_id = ?
                ORDER BY u.created_at DESC
            """, (chain_id, store_id), fetch_all=True)
        
        return jsonify([dict(u) for u in users])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@users_bp.route('/api/users', methods=['POST'])
@login_required
def create_user_api():
    """Create a new user with proper branch isolation"""
    try:
        from ..core.db import execute_query
        import sqlite3
        chain_id = session.get('chain_id')
        role = session.get('role')
        current_store_id = session.get('store_id')
        
        data = request.get_json()
        
        # Validate required fields
        if not data.get('username') or not data.get('password'):
            return jsonify({'error': 'Username and password are required'}), 400
        
        # Validate role
        user_role = data.get('role', 'branch_staff')
        if user_role not in ('branch_staff', 'branch_admin', 'business_admin'):
            return jsonify({'error': 'Invalid role specified'}), 400
            
        # Permission Check: Only HQ can create HQ Admins
        if user_role == 'business_admin' and role != 'business_admin':
            return jsonify({'error': 'Only HQ Admins can create other HQ Admins'}), 403
        
        # Determine store_id based on role
        if role == 'business_admin':
            # HQ can assign to any branch or leave empty for HQ
            store_id = data.get('store_id')
            if store_id == "" or store_id is None:
                store_id = None
            else:
                try:
                    store_id = int(store_id)
                except (TypeError, ValueError):
                    return jsonify({'error': 'Invalid branch selection'}), 400
        else:
            # Branch Managers can only add to their own branch
            store_id = current_store_id
        
        # Hash password
        password_hash = hash_password(data['password'])
        
        # Create user
        try:
            user_id = execute_query("""
                INSERT INTO users (username, password_hash, role, gender, chain_id, store_id)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                data['username'],
                password_hash,
                user_role,
                data.get('gender'),
                chain_id,
                store_id
            ))
        except Exception as db_err:
            if 'UNIQUE constraint' in str(db_err):
                return jsonify({'error': f'Username "{data["username"]}" already exists. Choose a different one.'}), 409
            raise
        
        return jsonify({'id': user_id, 'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@users_bp.route('/api/users/<int:user_id>', methods=['PUT'])
@login_required
def update_user_api(user_id):
    """Update a user with proper permission checks"""
    try:
        from ..core.db import execute_query
        chain_id = session.get('chain_id')
        role = session.get('role')
        current_store_id = session.get('store_id')
        
        data = request.get_json()
        
        # Get existing user to verify permissions
        existing_user = execute_query("""
            SELECT * FROM users WHERE id = ? AND chain_id = ?
        """, (user_id, chain_id), fetch_one=True)
        
        if not existing_user:
            return jsonify({'error': 'User not found'}), 404
        
        # Branch Managers can only edit users in their branch
        if role != 'business_admin' and existing_user['store_id'] != current_store_id:
            return jsonify({'error': 'Permission denied'}), 403
        
        # Cannot edit HQ admin users
        if existing_user['role'] == 'business_admin':
            return jsonify({'error': 'Cannot edit HQ admin users'}), 403
        
        # Build update query
        update_fields = []
        params = []
        
        if 'username' in data:
            update_fields.append('username = ?')
            params.append(data['username'])
        
        if 'password' in data and data['password']:
            update_fields.append('password_hash = ?')
            params.append(hash_password(data['password']))
        
        if 'gender' in data:
            update_fields.append('gender = ?')
            params.append(data['gender'])
        
        if 'role' in data:
            update_fields.append('role = ?')
            params.append(data['role'])
        
        # HQ can change branch assignment
        if role == 'business_admin' and 'store_id' in data:
            update_fields.append('store_id = ?')
            params.append(data['store_id'])
        
        if not update_fields:
            return jsonify({'error': 'No fields to update'}), 400
        
        params.extend([user_id, chain_id])
        
        execute_query(f"""
            UPDATE users
            SET {', '.join(update_fields)}
            WHERE id = ? AND chain_id = ?
        """, tuple(params))
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@users_bp.route('/api/users/<int:user_id>', methods=['DELETE'])
@login_required
def delete_user_api(user_id):
    """Delete a user with proper permission checks"""
    try:
        from ..core.db import execute_query
        chain_id = session.get('chain_id')
        role = session.get('role')
        current_store_id = session.get('store_id')
        current_user_id = session.get('user_id')
        
        # Get existing user to verify permissions
        existing_user = execute_query("""
            SELECT * FROM users WHERE id = ? AND chain_id = ?
        """, (user_id, chain_id), fetch_one=True)
        
        if not existing_user:
            return jsonify({'error': 'User not found'}), 404
        
        # Cannot delete yourself
        if user_id == current_user_id:
            return jsonify({'error': 'Cannot delete your own account'}), 403
        
        # Cannot delete HQ admin users
        if existing_user['role'] == 'business_admin':
            return jsonify({'error': 'Cannot delete HQ admin users'}), 403
        
        # Branch Managers can only delete users in their branch
        if role != 'business_admin' and existing_user['store_id'] != current_store_id:
            return jsonify({'error': 'Permission denied'}), 403
        
        # Delete the user (CASCADE will handle related data)
        execute_query("""
            DELETE FROM users WHERE id = ? AND chain_id = ?
        """, (user_id, chain_id))
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Legacy routes for backward compatibility
@users_bp.route('/create', methods=['POST'])
@login_required
def create_branch_user():
    """Add a new team member (legacy form-based route)."""
    try:
        service = get_user_service()
        
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        store_id = request.form.get('store_id')
        role = request.form.get('role', 'branch_staff')
        gender = request.form.get('gender')
        
        if not username or not password:
            flash('Username and password are required.', 'error')
            return redirect(url_for('users.manage_users'))
        
        service.create_user(username, password, store_id, role, gender)
        flash(f'User "{username}" created successfully!', 'success')
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
    
    return redirect(url_for('users.manage_users'))

@users_bp.route('/delete/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    """Remove a team member (legacy form-based route)."""
    try:
        service = get_user_service()
        service.delete_user(user_id)
        flash('User removed successfully.', 'success')
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
    
    return redirect(url_for('users.manage_users'))
