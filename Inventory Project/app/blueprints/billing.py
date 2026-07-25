from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash
from ..core.auth import login_required
from ..services.auth import AuthService
from ..services.transaction import TransactionService

# ==================== CONFIGURATION ====================
billing_bp = Blueprint('billing', __name__)
auth_service = AuthService()

def get_transaction_service():
    """Resolve TransactionService with active context."""
    user_id = session.get('user_id')
    context = auth_service.build_user_context(
        user_id, 
        session_chain_id=session.get('chain_id'), 
        session_store_id=session.get('store_id')
    )
    return TransactionService(context)

# ==================== POS VIEW ROUTES ====================

@billing_bp.route('/')
@login_required
def billing():
    """Billing Counter Interface."""
    try:
        # Staff must be attached to a Shop
        if not session.get('store_id'):
             flash("Please select a Shop to start billing.", "warning")
             return redirect(url_for('main.dashboard'))
             
        return render_template('billing.html')
    except Exception as e:
        flash(f"Access error: {str(e)}", 'error')
        return redirect(url_for('main.dashboard'))

# ==================== TRANSACTION ENGINE ====================

@billing_bp.route('/checkout', methods=['POST'])
@login_required
def checkout():
    try:
        service = get_transaction_service()
        d = request.get_json()
        res = service.process_sale(d.get('items', []), d.get('customerName'), d.get('customerPhone'))
        return jsonify({'success': True, 'bill_number': res['bill_number'], 
                        'bill_details': {'subtotal': res['subtotal'], 'tax': res['tax_amount'], 'total': res['total_amount']}})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

