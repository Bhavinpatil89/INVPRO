import sqlite3
import os

DB_PATH = "instance/inventory.db"

def check_stock():
    if not os.path.exists(DB_PATH): return
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("--- Products in DB ---")
    products = cursor.execute("SELECT id, name, cost_price, quantity, store_id FROM products").fetchall()
    for p in products:
        print(p)
    
    conn.close()

if __name__ == "__main__":
    check_stock()
