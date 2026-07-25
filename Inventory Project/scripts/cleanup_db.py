import sqlite3
import os

DB_PATH = "instance/inventory.db"

def cleanup_hq_ghost_branch():
    if not os.path.exists(DB_PATH):
        print(f"Error: Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("Cleaning up ghost branch 'HQ HQ'...")
    
    # 1. Identify store ID
    cursor.execute("SELECT id FROM stores WHERE name = 'HQ HQ'")
    row = cursor.fetchone()
    
    if row:
        store_id = row[0]
        print(f"Found 'HQ HQ' with ID: {store_id}")
        
        # 2. Update users pointing to this store
        cursor.execute("UPDATE users SET store_id = NULL WHERE store_id = ?", (store_id,))
        print(f"Updated {cursor.rowcount} users (set store_id to NULL)")
        
        # 3. Delete products in this store (prevent orphan products if any)
        cursor.execute("DELETE FROM products WHERE store_id = ?", (store_id,))
        print(f"Deleted {cursor.rowcount} products from this phantom branch")

        # 4. Delete the store
        cursor.execute("DELETE FROM stores WHERE id = ?", (store_id,))
        print("Deleted 'HQ HQ' store record.")
        
        conn.commit()
    else:
        print("No store named 'HQ HQ' found.")

    conn.close()

if __name__ == "__main__":
    cleanup_hq_ghost_branch()
