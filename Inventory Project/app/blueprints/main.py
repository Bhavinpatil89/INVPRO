"""
Main application routes.
Handles dashboard and analytics via Service Layer.
"""
from flask import Blueprint, render_template, jsonify, session, redirect, url_for, request, flash
from ..core.auth import login_required, logout_user, is_authenticated
from ..services.auth import AuthService
from ..services.reports import ReportService
from ..core.db import get_stores_by_chain, execute_query

# ==================== CONFIGURATION ====================
main_bp = Blueprint('main', __name__)
auth_service = AuthService()

def get_report_service():
    """Utility to resolve ReportService with active session context."""
    user_id = session.get('user_id')
    context = auth_service.build_user_context(
        user_id, 
        session_chain_id=session.get('chain_id'), 
        session_store_id=session.get('store_id')
    )
    return ReportService(context)

# ==================== MAIN DASHBOARD ROUTES ====================

@main_bp.route('/')
def index():
    """Root route: Landing page or Dashboard redirect."""
    if is_authenticated():
        return redirect(url_for('main.dashboard'))
    return render_template('landing.html')

@main_bp.route('/dashboard')
@login_required
def dashboard():
    """Main Business Dashboard."""
    try:
        ctx = get_report_service().context
        if ctx.is_branch_staff(): return redirect(url_for('billing.billing'))
        if ctx.is_branch_admin(): return redirect(url_for('main.branch_dashboard'))
        if ctx.is_business_admin(): return render_template('dashboard/hq.html')
        return redirect(url_for('auth.logout'))
    except Exception as e:
        flash(f"Error: {str(e)}", 'error')
        logout_user()
        return redirect(url_for('main.index'))

@main_bp.route('/store-dashboard')
@login_required
def branch_dashboard():
    """Focus view for a single shop (Manager or Head Office view)."""
    try:
        ctx = get_report_service().context
        
        # Security: Ensure we have a store context
        if not ctx.store_id:
             if ctx.is_business_admin():
                  flash("Select a Shop to view details.", "warning")
                  return redirect(url_for('main.dashboard'))
             else:
                  return redirect(url_for('auth.logout'))

        return render_template('dashboard/store.html')
    except Exception as e:
        flash(str(e), 'error')
        return redirect(url_for('main.dashboard'))

# ==================== SYSTEM API ENDPOINTS ====================

@main_bp.route('/api/dashboard/stats')
@login_required
def dashboard_stats():
    """Fetch high-level KPI cards for the current context."""
    try:
        service = get_report_service()
        stats = service.get_store_dashboard_stats()
        return jsonify(stats)
    except Exception:
        return jsonify({})

@main_bp.route('/api/session-context')
@login_required
def session_context():
    """Expose security and authority metadata for dynamic UI adjustments."""
    return jsonify({
        'username': session.get('username'),
        'role': session.get('role'),
        'chain_name': session.get('chain_name', 'INVPRO'),
        'store_name': session.get('store_name', 'Global Core'),
        'store_id': session.get('store_id'),
        'chain_id': session.get('chain_id'),
        'tax_rate': session.get('tax_rate', 18.0)
    })

# ==================== CONTEXT SWITCHING ====================

@main_bp.route('/switch-store/<int:store_id>')
@login_required
def switch_store(store_id):
    """Head Office action to jump between different shops."""
    try:
        current_user_id = session.get('user_id')
        temp_ctx = auth_service.build_user_context(current_user_id)
        
        # Authority Check
        if not temp_ctx.is_business_admin(): return redirect(url_for('main.dashboard'))

        # Verify target node belongs to user's chain
        target_ctx = auth_service.build_user_context(current_user_id, session_store_id=store_id)
        
        if target_ctx.store_id == store_id or store_id == 0:
            if store_id == 0:
                session.update({'store_id': None, 'store_name': "Head Office"})
                flash('Returned to Head Office Dashboard.', 'success')
            else:
                session['store_id'] = store_id
                res = execute_query("SELECT name FROM stores WHERE id=?", (store_id,), fetch_one=True)
                if res: session['store_name'] = res['name']
                flash(f'Switched to Shop: {session.get("store_name")}', 'success')
        else: flash('Shop is out of your scope.', 'error')
                 
    except Exception as e: flash(f'Switch failed: {str(e)}', 'error')
        
    return redirect(request.referrer or url_for('main.dashboard'))
