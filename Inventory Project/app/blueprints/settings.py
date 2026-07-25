"""
Settings routes for chain and store configuration.
Main owners can configure tax rates, store settings, and preferences.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from ..core.auth import login_required
from ..services.auth import AuthService
from ..services.configuration import ConfigurationService
from ..services.management import ChainService

settings_bp = Blueprint('settings', __name__)
auth_service = AuthService()

def get_services():
    user_id = session.get('user_id')
    context = auth_service.build_user_context(
        user_id, 
        session_chain_id=session.get('chain_id')
    )
    # Authority Protocol: Only HQ can access Settings cluster
    if not context.is_business_admin():
        raise PermissionError("Settings protocol restricted to HQ.")
        
    return ChainService(context), ConfigurationService(context)

@settings_bp.route('/')
@login_required
def index():
    """Settings page for main owners."""
    try:
        return render_template('settings/index.html')
    except Exception as e:
        flash(str(e), 'error')
        return redirect(url_for('main.dashboard'))

@settings_bp.route('/update-tax', methods=['POST'])
@login_required
def update_tax():
    """Update global fiscal settings."""
    try:
        _, config_service = get_services()
        
        # Tax Rate
        if 'tax_rate' in request.form:
             tax_rate = float(request.form.get('tax_rate', '0'))
             config_service.set_chain_setting('tax_rate', str(tax_rate))
             
        # Currency
        if 'currency_symbol' in request.form:
             currency = request.form.get('currency_symbol', '$').strip()
             config_service.set_chain_setting('currency_symbol', currency)
             
        flash('Fiscal configuration updated successfully.', 'success')
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
    
    return redirect(url_for('settings.index'))

@settings_bp.route('/add-node', methods=['POST'])
@login_required
def add_node():
    """Add a new node to the chain."""
    try:
        service, _ = get_services()
        name = request.form.get('name', '').strip()
        location = request.form.get('location', '').strip()
        
        if not name:
            flash('Node name is required.', 'error')
            return redirect(url_for('settings.index'))
            
        service.add_node(name, location)
        flash(f'Node "{name}" activated successfully!', 'success')
    except Exception as e:
        flash(f'Error activating node: {str(e)}', 'error')
    
    return redirect(url_for('settings.index'))

@settings_bp.route('/delete-node/<int:node_id>', methods=['POST'])
@login_required
def delete_node(node_id):
    """Purge a node."""
    try:
        service, _ = get_services()
        # Ensure service has delete_node
        if hasattr(service, 'delete_store'):
            service.delete_store(node_id)
        else:
            from ..core.db import execute_query
            execute_query("DELETE FROM stores WHERE id = ?", (node_id,))
            
        flash('Node connection purged.', 'success')
    except Exception as e:
        flash(f'Error purging node: {str(e)}', 'error')
    
    return redirect(url_for('settings.index'))

@settings_bp.route('/update-node/<int:node_id>', methods=['POST'])
@login_required
def update_node(node_id):
    """Update node details (Rename)."""
    try:
        service, _ = get_services()
        name = request.form.get('name', '').strip()
        location = request.form.get('location', '').strip()
        
        if not name:
            flash('Node name required.', 'error')
            return redirect(url_for('settings.index'))
            
        service.update_node(node_id, name, location)
        flash(f'Node details updated.', 'success')
    except Exception as e:
        flash(f'Update Error: {str(e)}', 'error')
    
    return redirect(url_for('settings.index'))

@settings_bp.route('/tax')
@login_required
def tax_management():
    """Tax Policy Management page (HQ Only)."""
    try:
        # Re-use the security check from get_services
        get_services()
        return render_template('settings/tax.html')
    except Exception as e:
        flash(str(e), 'error')
        return redirect(url_for('main.dashboard'))

# ==================== TAX POLICY API (INVPRO) ====================

@settings_bp.route('/api/tax-policies', methods=['GET'])
@login_required
def get_tax_policies_api():
    """Get all tax policies for the chain"""
    try:
        _, config_service = get_services()
        from ..services.tax import TaxService
        tax_service = TaxService(config_service.context)
        policies = tax_service.get_all_policies()
        return jsonify(policies)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@settings_bp.route('/api/tax-policies', methods=['POST'])
@login_required
def create_tax_policy_api():
    """Create a new tax policy"""
    try:
        _, config_service = get_services()
        from ..services.tax import TaxService
        tax_service = TaxService(config_service.context)
        
        data = request.get_json()
        tax_service.create_policy(
            data['name'], 
            data['percentage'], 
            data['is_all'], 
            data.get('category_ids', [])
        )
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@settings_bp.route('/api/tax-policies/<int:policy_id>', methods=['PUT', 'POST'])
@login_required
def update_tax_policy_api(policy_id):
    """Update a tax policy"""
    try:
        _, config_service = get_services()
        from ..services.tax import TaxService
        tax_service = TaxService(config_service.context)
        
        data = request.get_json() if request.is_json else request.form
        
        # Support both JSON and Form (for legacy)
        if request.is_json:
            tax_service.update_policy(
                policy_id, 
                data['name'], 
                data['percentage'], 
                data['is_all'], 
                data.get('category_ids', [])
            )
        else:
            # Traditional form logic if needed, but let's stick to API for new UI
            pass
            
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@settings_bp.route('/api/tax-policies/<int:policy_id>', methods=['DELETE'])
@login_required
def delete_tax_policy_api(policy_id):
    """Delete a tax policy"""
    try:
        _, config_service = get_services()
        from ..services.tax import TaxService
        tax_service = TaxService(config_service.context)
        tax_service.delete_policy(policy_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@settings_bp.route('/update-chain-name', methods=['POST'])
@login_required
def update_chain_name():
    """Update chain name."""
    try:
        service, _ = get_services()
        name = request.form.get('name', '').strip()
        
        if not name:
            flash('Chain name is required.', 'error')
            return redirect(url_for('settings.index'))
            
        service.update_chain_name(name)
        session['chain_name'] = name
        flash(f'Chain name updated to "{name}"', 'success')
    except Exception as e:
        flash(f'Error updating chain name: {str(e)}', 'error')
    
    return redirect(url_for('settings.index'))

# --- CLUSTER REGISTRY (CATEGORIES) ---

@settings_bp.route('/categories/add', methods=['POST'])
@login_required
def add_category():
    """Initialize a new asset cluster."""
    try:
        _, config_service = get_services()
        from ..services.inventory import InventoryService
        inv_service = InventoryService(config_service.context)
        
        name = request.form.get('name', '').strip()
        if not name:
            flash('Cluster designation required.', 'error')
            return redirect(url_for('settings.index'))
            
        inv_service.add_category(name)
        flash(f'Cluster "{name}" initialized successfully.', 'success')
    except Exception as e:
        flash(f'Initialization Error: {str(e)}', 'error')
    
    return redirect(url_for('settings.index'))

@settings_bp.route('/categories/update/<int:category_id>', methods=['POST'])
@login_required
def update_category(category_id):
    """Calibrate cluster parameters."""
    try:
        _, config_service = get_services()
        from ..services.inventory import InventoryService
        inv_service = InventoryService(config_service.context)
        
        name = request.form.get('name', '').strip()
        if not name:
            flash('Cluster designation required.', 'error')
            return redirect(url_for('settings.index'))
            
        inv_service.update_category(category_id, name)
        flash('Cluster calibration successful.', 'success')
    except Exception as e:
        flash(f'Calibration Error: {str(e)}', 'error')
    
    return redirect(url_for('settings.index'))

@settings_bp.route('/categories/delete/<int:category_id>', methods=['POST'])
@login_required
def delete_category(category_id):
    """Decommission an asset cluster."""
    try:
        _, config_service = get_services()
        from ..services.inventory import InventoryService
        inv_service = InventoryService(config_service.context)
        
        inv_service.delete_category(category_id)
        flash('Cluster decommissioned.', 'success')
    except Exception as e:
        flash(f'Decommission Error: {str(e)}', 'error')
    
    return redirect(url_for('settings.index'))

# ==================== CATEGORY MANAGEMENT API (INVPRO) ====================

@settings_bp.route('/api/categories', methods=['POST'])
@login_required
def create_category_api():
    """Create a new category"""
    try:
        _, config_service = get_services()
        from ..services.inventory import InventoryService
        inv_service = InventoryService(config_service.context)
        
        data = request.get_json()
        inv_service.add_category(data['name'])
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@settings_bp.route('/api/categories/<int:category_id>', methods=['PUT'])
@login_required
def update_category_api(category_id):
    """Update a category"""
    try:
        _, config_service = get_services()
        from ..services.inventory import InventoryService
        inv_service = InventoryService(config_service.context)
        
        data = request.get_json()
        inv_service.update_category(category_id, data['name'])
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@settings_bp.route('/api/categories/<int:category_id>', methods=['DELETE'])
@login_required
def delete_category_api(category_id):
    """Delete a category"""
    try:
        _, config_service = get_services()
        from ..services.inventory import InventoryService
        inv_service = InventoryService(config_service.context)
        
        inv_service.delete_category(category_id)
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==================== BRANCH MANAGEMENT API (INVPRO) ====================

@settings_bp.route('/api/branches', methods=['GET'])
@login_required
def get_branches_api():
    """Get all branches with stats"""
    try:
        from ..core.db import execute_query
        chain_id = session.get('chain_id')
        
        branches = execute_query("""
            SELECT s.*,
                   (SELECT COUNT(*) FROM users WHERE store_id = s.id) as user_count,
                   (SELECT COUNT(*) FROM products WHERE store_id = s.id) as product_count,
                   (SELECT COALESCE(SUM(quantity), 0) FROM products WHERE store_id = s.id) as stock_volume
            FROM stores s
            WHERE s.chain_id = ? AND s.location != 'HQ'
            ORDER BY s.name
        """, (chain_id,), fetch_all=True)
        
        return jsonify([dict(b) for b in branches])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@settings_bp.route('/api/branches', methods=['POST'])
@login_required
def create_branch_api():
    """Create a new branch"""
    try:
        service, _ = get_services()
        data = request.get_json()
        
        service.add_node(data['name'], data.get('location', ''))
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@settings_bp.route('/api/branches/<int:branch_id>', methods=['PUT'])
@login_required
def update_branch_api(branch_id):
    """Update a branch"""
    try:
        service, _ = get_services()
        data = request.get_json()
        
        service.update_node(branch_id, data['name'], data.get('location', ''))
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@settings_bp.route('/api/branches/<int:branch_id>', methods=['DELETE'])
@login_required
def delete_branch_api(branch_id):
    """Delete a branch"""
    try:
        service, _ = get_services()
        
        if hasattr(service, 'delete_store'):
            service.delete_store(branch_id)
        else:
            from ..core.db import execute_query
            execute_query("DELETE FROM stores WHERE id = ?", (branch_id,))
            
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
