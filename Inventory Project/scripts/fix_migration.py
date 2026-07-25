import sqlite3
import os

db_path = os.path.join('instance', 'inventory.db')

def migrate():
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        
        # Check if user_id exists
        cursor.execute("PRAGMA table_info(bills)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'user_id' not in columns:
            print("Adding user_id column to bills table...")
            # SQLite ALTER TABLE is limited, but adding a column is supported
            cursor.execute("ALTER TABLE bills ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE SET NULL")
            conn.commit()
            print("Migration successful.")
        else:
            print("user_id column already exists.")
            
    except Exception as e:
        print(f"Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
