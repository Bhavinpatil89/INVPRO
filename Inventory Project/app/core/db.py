# Database operations for inventory system (Data Access Layer)
import sqlite3
import os
from contextlib import contextmanager

DATABASE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'instance', 'inventory.db')

@contextmanager
def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def init_db():
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # 0. Chains (Organization)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chains (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                owner_user_id INTEGER,
                tax_rate REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (owner_user_id) REFERENCES users(id) ON DELETE SET NULL
            )
        ''')

        # 1. Users
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'main_owner',
                gender TEXT CHECK(gender IN ('Male', 'Female', 'Other', NULL)),
                chain_id INTEGER,
                store_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (chain_id) REFERENCES chains(id) ON DELETE CASCADE,
                FOREIGN KEY (store_id) REFERENCES stores(id) ON DELETE SET NULL
            )
        ''')
        
        # 2. Stores
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                chain_id INTEGER NOT NULL,
                location TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (chain_id) REFERENCES chains(id) ON DELETE CASCADE
            )
        ''')
        
        # 3. Categories
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                chain_id INTEGER NOT NULL,
                FOREIGN KEY (chain_id) REFERENCES chains(id) ON DELETE CASCADE
            )
        ''')
        
        # 4. Global Products (HQ Product Registry)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS global_products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                default_cost_price REAL NOT NULL,
                default_selling_price REAL NOT NULL,
                category_id INTEGER NOT NULL,
                chain_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE,
                FOREIGN KEY (chain_id) REFERENCES chains(id) ON DELETE CASCADE
            )
        ''')
        
        # 5. Products (Branch-Specific Stock)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                global_product_id INTEGER,
                name TEXT NOT NULL,
                cost_price REAL NOT NULL,
                selling_price REAL NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 0 CHECK(quantity >= 0),
                category_id INTEGER NOT NULL,
                store_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (global_product_id) REFERENCES global_products(id) ON DELETE SET NULL,
                FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE,
                FOREIGN KEY (store_id) REFERENCES stores(id) ON DELETE CASCADE
            )
        ''')

        # 6. Bills
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bill_number TEXT NOT NULL UNIQUE,
                date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                subtotal_amount REAL NOT NULL DEFAULT 0.0,
                tax_amount REAL NOT NULL DEFAULT 0.0,
                total_amount REAL NOT NULL DEFAULT 0.0,
                total_cost REAL NOT NULL DEFAULT 0.0,
                total_profit REAL NOT NULL DEFAULT 0.0,
                store_id INTEGER NOT NULL,
                user_id INTEGER,
                customer_id INTEGER,
                customer_name TEXT,
                customer_phone TEXT,
                FOREIGN KEY (store_id) REFERENCES stores(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
                FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE SET NULL
            )
        ''' )
        
        # 7. Bill Items
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bill_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bill_id INTEGER NOT NULL,
                product_id INTEGER,
                product_name TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                price_at_sale REAL NOT NULL,
                cost_at_sale REAL NOT NULL DEFAULT 0.0,
                tax_rate_applied REAL NOT NULL DEFAULT 0.0,
                tax_amount REAL NOT NULL DEFAULT 0.0,
                FOREIGN KEY (bill_id) REFERENCES bills(id) ON DELETE CASCADE,
                FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE SET NULL
            )
        ''')

        # 8. Tax Policies
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tax_policies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chain_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                percentage REAL NOT NULL,
                is_all_categories INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (chain_id) REFERENCES chains(id) ON DELETE CASCADE
            )
        ''')

        # 9. Tax Policy Categories (Many-to-Many)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tax_policy_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tax_id INTEGER NOT NULL,
                category_id INTEGER NOT NULL,
                FOREIGN KEY (tax_id) REFERENCES tax_policies(id) ON DELETE CASCADE,
                FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
            )
        ''')

        # 10. Settings (Configuration)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scope TEXT NOT NULL CHECK(scope IN ('chain', 'store')),
                scope_id INTEGER NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(scope, scope_id, key)
            )
        ''')

        # 11. Customers (CRM & Loyalty)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chain_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                phone TEXT NOT NULL,
                email TEXT,
                loyalty_points REAL DEFAULT 0.0,
                total_spent REAL DEFAULT 0.0,
                last_visit TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(chain_id, phone),
                FOREIGN KEY (chain_id) REFERENCES chains(id) ON DELETE CASCADE
            )
        ''')


        
        conn.commit()

        # Schema Integrity Patches
        try: cursor.execute("ALTER TABLE bills ADD COLUMN customer_id INTEGER")
        except: pass
        try: cursor.execute("ALTER TABLE bills ADD COLUMN customer_name TEXT")
        except: pass
        try: cursor.execute("ALTER TABLE bills ADD COLUMN customer_phone TEXT")
        except: pass
        try: cursor.execute("ALTER TABLE bill_items ADD COLUMN tax_rate_applied REAL NOT NULL DEFAULT 0.0")
        except: pass
        try: cursor.execute("ALTER TABLE bill_items ADD COLUMN tax_amount REAL NOT NULL DEFAULT 0.0")
        except: pass
        try: cursor.execute("ALTER TABLE products ADD COLUMN global_product_id INTEGER")
        except: pass
        try: cursor.execute("ALTER TABLE users ADD COLUMN gender TEXT")
        except: pass

def execute_query(query, params=None, fetch_one=False, fetch_all=False):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        if fetch_one:
            return cursor.fetchone()
        elif fetch_all:
            return cursor.fetchall()
        else:
            return cursor.lastrowid

# --- CORE DAL HELPERS (Used by Services) ---

# Settings
def upsert_setting(scope, scope_id, key, value):
    """
    Insert or Update a setting.
    """
    query = """
        INSERT INTO settings (scope, scope_id, key, value, updated_at)
        VALUES (:scope, :scope_id, :key, :value, CURRENT_TIMESTAMP)
        ON CONFLICT(scope, scope_id, key) 
        DO UPDATE SET value=excluded.value, updated_at=CURRENT_TIMESTAMP
    """
    execute_query(query, {'scope': scope, 'scope_id': scope_id, 'key': key, 'value': str(value)})

def get_settings_by_scope(scope, scope_id):
    """
    Get all settings for a specific scope as a dict.
    """
    rows = execute_query("SELECT key, value FROM settings WHERE scope = ? AND scope_id = ?", (scope, scope_id), fetch_all=True)
    return {row['key']: row['value'] for row in rows}

# Chains/Stores
def get_chain_by_id(chain_id):
    return execute_query("SELECT * FROM chains WHERE id = ?", (chain_id,), fetch_one=True)

def get_stores_by_chain(chain_id):
    """Fetch all physical nodes in a chain."""
    return execute_query("SELECT * FROM stores WHERE chain_id = ?", (chain_id,), fetch_all=True)

def get_all_stores_by_chain(chain_id):
    """Alias for get_stores_by_chain for service-layer compatibility."""
    return get_stores_by_chain(chain_id)

def get_users_by_chain(chain_id):
    return execute_query("SELECT * FROM users WHERE chain_id = ?", (chain_id,), fetch_all=True)

def create_chain(name, owner_user_id):
    return execute_query("INSERT INTO chains (name, owner_user_id) VALUES (?, ?)", (name, owner_user_id))

def create_store(name, chain_id, location=None):
    return execute_query("INSERT INTO stores (name, chain_id, location) VALUES (?, ?, ?)", (name, chain_id, location))

# User Mgmt Helpers
def create_user(username, password_hash, role, chain_id, store_id, gender=None):
    return execute_query(
        "INSERT INTO users (username, password_hash, role, chain_id, store_id, gender) VALUES (?, ?, ?, ?, ?, ?)", 
        (username, password_hash, role, chain_id, store_id, gender)
    )

def get_user_by_username(username):
    # Used by AuthService (login) - Case-insensitive lookup
    return execute_query("SELECT * FROM users WHERE username = ? COLLATE NOCASE", (username,), fetch_one=True)

def get_user_by_id(user_id):
    return execute_query("SELECT * FROM users WHERE id = ?", (user_id,), fetch_one=True)

def update_user_chain(user_id, chain_id):
    execute_query("UPDATE users SET chain_id = ? WHERE id = ?", (chain_id, user_id))

def get_chain_by_user(user_id):
    # For owners, find the chain they own
    return execute_query("SELECT * FROM chains WHERE owner_user_id = ?", (user_id,), fetch_one=True)

# Categories
def create_category(name, chain_id):
    return execute_query("INSERT INTO categories (name, chain_id) VALUES (?, ?)", (name, chain_id))

def get_categories_by_chain(chain_id):
    return execute_query("SELECT * FROM categories WHERE chain_id = ? ORDER BY name", (chain_id,), fetch_all=True)

def update_category(category_id, name, chain_id):
    execute_query("UPDATE categories SET name = ? WHERE id = ? AND chain_id = ?", (name, category_id, chain_id))

def delete_category(category_id, chain_id):
    execute_query("DELETE FROM categories WHERE id = ? AND chain_id = ?", (category_id, chain_id))

# Products
def create_product(data):
    # Used by InventoryService
    query = """
        INSERT INTO products (global_product_id, name, cost_price, selling_price, quantity, category_id, store_id)
        VALUES (:global_product_id, :name, :cost_price, :selling_price, :quantity, :category_id, :store_id)
    """
    return execute_query(query, data)

def get_products_by_store(store_id):
    query = """
        SELECT p.*, c.name as category_name
        FROM products p
        JOIN categories c ON p.category_id = c.id
        WHERE p.store_id = ?
        ORDER BY p.name
    """
    return execute_query(query, (store_id,), fetch_all=True)

def get_products_by_chain(chain_id):
    query = """
        SELECT p.*, c.name as category_name, s.name as store_name
        FROM products p
        JOIN categories c ON p.category_id = c.id
        JOIN stores s ON p.store_id = s.id
        WHERE s.chain_id = ?
        ORDER BY s.name, p.name
    """
    return execute_query(query, (chain_id,), fetch_all=True)

def get_product_for_update(product_id, store_id):
    # Used for ownership check before update
    return execute_query("SELECT * FROM products WHERE id = ? AND store_id = ?", (product_id, store_id), fetch_one=True)

def update_product_details(product_id, store_id, data):
    fields = []
    params = {'id': product_id, 'store_id': store_id}
    
    for key, value in data.items():
        if key not in ['id', 'store_id']:
            fields.append(f"{key} = :{key}")
            params[key] = value
            
    if not fields:
        return

    query = f"""
        UPDATE products 
        SET {', '.join(fields)}
        WHERE id = :id AND store_id = :store_id
    """
    execute_query(query, params)

def delete_product(product_id, store_id):
    execute_query("DELETE FROM products WHERE id = ? AND store_id = ?", (product_id, store_id))

def search_products(store_id, term):
    query = """
        SELECT p.*, c.name as category_name
        FROM products p
        JOIN categories c ON p.category_id = c.id
        WHERE p.store_id = ? AND p.name LIKE ?
        ORDER BY p.name
    """
    return execute_query(query, (store_id, f'%{term}%'), fetch_all=True)

# Transactions
def get_all_bills(store_id):
    query = """
        SELECT b.*, u.username as creator_name, COUNT(bi.id) as item_count 
        FROM bills b 
        LEFT JOIN bill_items bi ON b.id = bi.bill_id 
        LEFT JOIN users u ON b.user_id = u.id
        WHERE b.store_id = ? 
        GROUP BY b.id, u.username
        ORDER BY b.date DESC
    """
    return execute_query(query, (store_id,), fetch_all=True)

def get_recent_bills(store_id, limit=5):
    query = """
        SELECT b.*, u.username as creator_name, COUNT(bi.id) as item_count 
        FROM bills b 
        LEFT JOIN bill_items bi ON b.id = bi.bill_id 
        LEFT JOIN users u ON b.user_id = u.id
        WHERE b.store_id = ? 
        GROUP BY b.id, u.username
        ORDER BY b.date DESC 
        LIMIT ?
    """
    return execute_query(query, (store_id, limit), fetch_all=True)

def get_bill_items(bill_id, store_id=None):
    if store_id:
        # Secure fetch: verify bill belongs to store
        query = """
            SELECT bi.* FROM bill_items bi
            JOIN bills b ON bi.bill_id = b.id
            WHERE bi.bill_id = ? AND b.store_id = ?
        """
        return execute_query(query, (bill_id, store_id), fetch_all=True)
    else:
        # Direct fetch for admin/owner who already checked ownership
        return execute_query("SELECT * FROM bill_items WHERE bill_id = ?", (bill_id,), fetch_all=True)

# --- REPORTING / ANALYTICS (Advanced) ---

def get_sales_time_series(scope, scope_id, start_date, end_date, interval='day'):
    """
    Get aggregated sales over time.
    Scope: 'store' or 'chain'.
    Interval: 'day', 'month'.
    """
    # SQLite date formatting
    if interval == 'month':
        date_format = '%Y-%m'
    else:
        date_format = '%Y-%m-%d'
    
    where_clause = "store_id = ?" if scope == 'store' else "chain_id = ?"
    
    query = f"""
        SELECT 
            strftime('{date_format}', date) as period,
            ROUND(SUM(total_amount), 2) as revenue,
            ROUND(SUM(total_cost), 2) as cost,
            ROUND(SUM(total_profit), 2) as profit,
            COUNT(*) as bill_count
        FROM bills
        WHERE {where_clause} 
        AND date BETWEEN ? AND ?
        GROUP BY period
        ORDER BY period ASC
    """
    # Ensure end_date includes the full day
    return execute_query(query, (scope_id, start_date, end_date + ' 23:59:59'), fetch_all=True)

def get_top_selling_products(scope, scope_id, limit=10):
    """
    Get top selling products by Revenue.
    Uses bill_items for historical accuracy.
    """
    where_clause = "b.store_id = ?" if scope == 'store' else "b.chain_id = ?"
    
    query = f"""
        SELECT 
            bi.product_name,
            SUM(bi.quantity) as total_qty,
            ROUND(SUM(bi.quantity * bi.price_at_sale), 2) as total_revenue,
            ROUND(SUM(bi.quantity * (bi.price_at_sale - bi.cost_at_sale)), 2) as total_profit
        FROM bill_items bi
        JOIN bills b ON bi.bill_id = b.id
        WHERE {where_clause}
        GROUP BY bi.product_name
        ORDER BY total_revenue DESC
        LIMIT ?
    """
    return execute_query(query, (scope_id, limit), fetch_all=True)

def get_dead_stock(store_id, days_threshold=30):
    """
    Identify products with NO sales in the last X days.
    (DSA: Set Difference or Exclusion)
    """
    query = """
        SELECT * FROM products p
        WHERE p.store_id = ?
        AND p.quantity > 0
        AND p.id NOT IN (
            SELECT bi.product_id 
            FROM bill_items bi
            JOIN bills b ON bi.bill_id = b.id
            WHERE b.store_id = ?
            AND b.date >= date('now', ?)
        )
        ORDER BY (p.cost_price * p.quantity) DESC
    """
    return execute_query(query, (store_id, store_id, f'-{days_threshold} days'), fetch_all=True)

# --- REPORTING AGGREGATES ---
def get_dashboard_kpi(store_id, date_filter=None):
    where = f"WHERE store_id = ? {date_filter if date_filter else ''}"
    return execute_query(f"SELECT ROUND(SUM(total_amount), 2), ROUND(SUM(total_cost), 2), ROUND(SUM(total_profit), 2), COUNT(*), ROUND(SUM(tax_amount), 2) FROM bills {where}", (store_id,), fetch_one=True)

def get_inventory_kpi(store_id):
    return execute_query("SELECT ROUND(SUM(cost_price * quantity), 2), COUNT(*) FROM products WHERE store_id = ?", (store_id,), fetch_one=True)

def get_stock_alerts(store_id, threshold=5):
    low = execute_query("SELECT COUNT(*) FROM products WHERE store_id = ? AND quantity <= ?", (store_id, threshold), fetch_one=True)[0]
    instock = execute_query("SELECT COUNT(*) FROM products WHERE store_id = ? AND quantity > 0", (store_id,), fetch_one=True)[0]
    return (low, instock)
