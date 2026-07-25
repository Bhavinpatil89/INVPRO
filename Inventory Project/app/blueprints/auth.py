"""
Authentication routes.
Handles user registration (Franchise setup), login, and logout.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from ..services.auth import AuthService
from ..core.auth import login_user, logout_user, is_authenticated

# ==================== CONFIGURATION ====================
auth_bp = Blueprint('auth', __name__)
auth_service = AuthService()

# ==================== VIEW ROUTES ====================

def _auth_resp(success, msg, status=200, template=None, redirect_url=None):
    ifSuccess = "success" if success else "error"
    if request.headers.get('Accept') == 'application/json':
        return {"success": success, "message": msg, "redirect": redirect_url}, status
    if msg: flash(msg, ifSuccess)
    return redirect(redirect_url) if redirect_url and success else render_template(template)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if is_authenticated(): return redirect(url_for('main.dashboard'))
    if request.method == 'POST':
        d = request.form
        node = (d.get('chain_name','') or d.get('store_name','')).strip()
        username, pw, cpw = d.get('username','').strip(), d.get('password',''), d.get('confirm_password','')
        if not all([username, pw, cpw, node]): return _auth_resp(False, 'All fields required.', 400, 'auth/register.html')
        if pw != cpw: return _auth_resp(False, 'Passwords match mismatch.', 400, 'auth/register.html')
        try:
            uid, cid, sid = auth_service.register_chain_owner(username, pw, node)
            login_user(uid, username, role='business_admin')
            session.update({'chain_id': cid, 'store_id': sid, 'node_name': node})
            return _auth_resp(True, f'Shop "{node}" is now ready!', 200, redirect_url=url_for('main.dashboard'))
        except Exception as e: return _auth_resp(False, str(e), 500, 'auth/register.html')
    return render_template('auth/register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if is_authenticated(): return redirect(url_for('main.dashboard'))
    if request.method == 'POST':
        user = auth_service.authenticate(request.form.get('username','').strip(), request.form.get('password',''))
        if not user: return _auth_resp(False, 'Invalid login details.', 401, 'auth/login.html')
        try:
            ctx = auth_service.build_user_context(user['id'])
            login_user(user['id'], user['username'], ctx.role)
            session.update({'chain_id': ctx.chain_id, 'store_id': ctx.store_id})
            
            from ..core.db import execute_query
            if ctx.store_id:
                res = execute_query("SELECT name FROM stores WHERE id=?", (ctx.store_id,), fetch_one=True)
                session['store_name'] = res['name'] if res else "Shop"
            else: session['store_name'] = "Head Office"
            
            if ctx.chain_id:
                res = execute_query("SELECT name FROM chains WHERE id=?", (ctx.chain_id,), fetch_one=True)
                session['chain_name'] = res['name'] if res else "INVPRO"

            target = url_for('billing.billing') if ctx.is_branch_staff() else url_for('main.dashboard')
            role_name = "Boss" if ctx.is_business_admin() else ("Manager" if ctx.is_branch_admin() else "Bill Counter")
            return _auth_resp(True, f'Welcome back, {role_name}!', 200, redirect_url=target)
        except Exception as e: return _auth_resp(False, f'Login Error: {str(e)}', 500, 'auth/login.html')
    
    # Redirect GET to landing page which has the login form
    return redirect(url_for('main.index'))

# ==================== LOGOUT ====================

@auth_bp.route('/logout')
def logout():
    logout_user()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('main.index'))

