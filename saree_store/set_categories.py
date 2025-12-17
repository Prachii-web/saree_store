import sqlite3
conn = sqlite3.connect("saree_store.db")
cur = conn.cursor()

# Set category for existing sample sarees
cur.execute("UPDATE products SET category='Banarasi' WHERE name LIKE '%Banarasi%';")
cur.execute("UPDATE products SET category='Kanjivaram' WHERE name LIKE '%Kanjivaram%';")
cur.execute("UPDATE products SET category='Chiffon' WHERE name LIKE '%Chiffon%';")
cur.execute("UPDATE products SET category='Cotton' WHERE name LIKE '%Cotton%';")

conn.commit()
conn.close()
print("🎉 Categories added to products successfully!")
