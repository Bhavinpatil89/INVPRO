import sqlite3
import os

DB_PATH = "instance/inventory.db"

def check_users():
    if not os.path.exists(DB_PATH):
        print(f"Error: Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print("--- User Accounts ---")
    users = cursor.execute("SELECT id, username, role, chain_id, store_id FROM users").fetchall()
    for user in users:
        print(dict(user))

    print("\n--- Chains ---")
    chains = cursor.execute("SELECT id, name, owner_user_id FROM chains").fetchall()
    for chain in chains:
        print(dict(chain))

    print("\n--- Stores ---")
    stores = cursor.execute("SELECT id, name, chain_id FROM stores").fetchall()
    for store in stores:
        print(dict(store))

    conn.close()

if __name__ == "__main__":
    check_users()
