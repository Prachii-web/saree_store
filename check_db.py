import sqlite3

conn = sqlite3.connect('saree_store.db')
cursor = conn.cursor()

print("🧵 Current Products:")
for row in cursor.execute("SELECT id, name, image FROM products"):
    print(row)

conn.close()
