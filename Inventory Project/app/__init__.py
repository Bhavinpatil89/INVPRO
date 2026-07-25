from flask import Flask
from datetime import timedelta

from .core.db import init_db

def create_app():
    app = Flask(__name__)
    
    # Config
    app.config['SECRET_KEY'] = 'invpro-vanilla-secret-key-2026'
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
    
    # Initialize database
    with app.app_context():
        init_db()
    
    # Register Blueprints
    from .blueprints.auth import auth_bp
    from .blueprints.main import main_bp
    from .blueprints.inventory import inventory_bp
    from .blueprints.billing import billing_bp
    from .blueprints.sales import sales_bp
    from .blueprints.users import users_bp
    from .blueprints.settings import settings_bp
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(main_bp, url_prefix='/')
    app.register_blueprint(inventory_bp, url_prefix='/inventory')
    app.register_blueprint(billing_bp, url_prefix='/billing')
    app.register_blueprint(sales_bp, url_prefix='/sales')
    app.register_blueprint(users_bp, url_prefix='/users')
    app.register_blueprint(settings_bp, url_prefix='/settings')
    
    return app
