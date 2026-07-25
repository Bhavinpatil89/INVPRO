from werkzeug.security import generate_password_hash, check_password_hash
import secrets
from functools import wraps
from flask import session, redirect, url_for, flash

def hash_password(password):
    return generate_password_hash(password, method='scrypt')

def verify_password(password, password_hash):
    return check_password_hash(password_hash, password)

def login_user(user_id, username, role='user'):
    session['user_id'] = user_id
    session['username'] = username
    session['role'] = role
    session.permanent = True

def logout_user():
    """Log out the current user by clearing the session."""
    session.clear()

def get_current_user():
    if 'user_id' in session:
        return {
            'user_id': session['user_id'],
            'username': session['username'],
            'role': session.get('role', 'user')
        }
    return None

def is_authenticated():
    """Check if a user is currently authenticated."""
    return 'user_id' in session

def login_required(f):
    """
    Decorator to require login for a route.
    Redirects to login page if user is not authenticated.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_authenticated():
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

def generate_secret_key():
    """Generate a secure random secret key for Flask sessions."""
    return secrets.token_hex(32)
