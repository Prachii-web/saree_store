import sqlite3

db = "saree_store.db"
conn = sqlite3.connect(db)
cur = conn.cursor()

# Check if column exists
cur.execute("PRAGMA table_info(products);")
cols = [c[1].lower() for c in cur.fetchall()]
if "category" in cols:
    print("Category column already exists. Nothing to do.")
else:
    try:
        cur.execute("ALTER TABLE products ADD COLUMN category TEXT;")
        conn.commit()
        print("✅ Added 'category' column.")
    except Exception as e:
        print("✖ ALTER TABLE failed:", e)

conn.close()
