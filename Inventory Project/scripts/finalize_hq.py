import sqlite3
import os

DB_PATH = "instance/inventory.db"

def finalize_hq_separation():
    if not os.path.exists(DB_PATH): return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Mark remaining HQ-named stores as HQ location to trigger the UI filter
    cursor.execute("UPDATE stores SET location = 'HQ' WHERE name LIKE '%HQ%'")
    print(f"Standardized {cursor.rowcount} HQ-related stores to location='HQ'.")

    # Double check users
    users = cursor.execute("SELECT id, username, store_id FROM users").fetchall()
    print("\nCurrent User Scopes:")
    for u in users:
        print(u)
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    finalize_hq_separation()
