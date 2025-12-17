# create_orders_table.py
import sqlite3

conn = sqlite3.connect('saree_store.db')
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER,
    customer_name TEXT NOT NULL,
    address TEXT NOT NULL,
    contact TEXT NOT NULL,
    FOREIGN KEY (product_id) REFERENCES products (id)
)
''')

conn.commit()
conn.close()
print("✅ 'orders' table created successfully!")
