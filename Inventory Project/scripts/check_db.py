import sqlite3

conn = sqlite3.connect('instance/inventory.db')
cursor = conn.cursor()

cursor.execute('SELECT COUNT(*) FROM global_products')
print(f'Global Products (Registry): {cursor.fetchone()[0]}')

cursor.execute('SELECT COUNT(*) FROM products')
print(f'Branch Products (Stock): {cursor.fetchone()[0]}')

cursor.execute('SELECT s.name, COUNT(p.id) FROM stores s LEFT JOIN products p ON s.id = p.store_id GROUP BY s.id, s.name')
print('\nProducts per branch:')
for row in cursor.fetchall():
    print(f'  {row[0]}: {row[1]} products')

conn.close()
