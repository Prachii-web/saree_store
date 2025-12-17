import sqlite3

conn = sqlite3.connect('saree_store.db')
cursor = conn.cursor()

# Sample products with category
products = [
    ("Banarasi Silk Saree", 2500, "Elegant red Banarasi silk saree", "saree1.jpg", "banarasi"),
    ("Kanjivaram Saree", 3200, "Traditional South Indian style", "saree2.jpg", "kanjivaram"),
    ("Chiffon Saree", 1800, "Lightweight everyday wear", "saree3.jpg", "silk"),
    ("Cotton Saree", 1500, "Comfortable summer saree", "saree4.jpg", "cotton"),
    ("Wedding Lehenga Saree", 5000, "Luxurious wedding saree", "wedding.jpg", "wedding"),
    ("Handloom Cotton Saree", 1200, "Eco-friendly handloom saree", "handloom.jpg", "handloom")
]

cursor.executemany("INSERT INTO products (name, price, description, image, category) VALUES (?, ?, ?, ?, ?)", products)
conn.commit()
conn.close()

print("✅ Sample products added successfully!")
