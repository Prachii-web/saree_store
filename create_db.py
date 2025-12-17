from flask import Flask, render_template, request, redirect, url_for
import sqlite3, os

app = Flask(__name__)

# ---------- DATABASE CONNECTION ----------
def get_db_connection():
    conn = sqlite3.connect('saree_store.db')
    conn.row_factory = sqlite3.Row
    return conn


# ---------- INITIAL SETUP ----------
def initialize_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Create tables if they don't exist
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        price REAL NOT NULL,
        description TEXT,
        image TEXT
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS enquiries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL,
        message TEXT NOT NULL
    )
    ''')

    # Seed data only if products table is empty
    cursor.execute("SELECT COUNT(*) FROM products")
    count = cursor.fetchone()[0]
    if count == 0:
        products = [
            ("Silk Saree", 2499, "Elegant silk saree with gold border", "saree1.jpg"),
            ("Banarasi Saree", 3299, "Royal Banarasi saree with intricate design", "saree2.jpg"),
            ("Cotton Saree", 1999, "Soft cotton saree for daily wear", "saree3.jpg"),
            ("Kanjivaram Saree", 4599, "Traditional South Indian weave", "saree4.jpg")
        ]
        cursor.executemany('''
        INSERT INTO products (name, price, description, image)
        VALUES (?, ?, ?, ?)
        ''', products)
        print("✅ Sample sarees inserted successfully!")

    conn.commit()
    conn.close()


# ---------- ROUTES ----------
@app.route('/')
def index():
    conn = get_db_connection()
    products = conn.execute('SELECT * FROM products').fetchall()
    conn.close()
    return render_template('index.html', products=products)


@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        message = request.form['message']

        conn = get_db_connection()
        conn.execute('INSERT INTO enquiries (name, email, message) VALUES (?, ?, ?)',
                     (name, email, message))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))

    return render_template('contact.html')


# ---------- ADMIN ROUTES ----------
@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username == 'prachu' and password == '2812':
            return redirect(url_for('admin_dashboard'))
        else:
            return render_template('admin_login.html', error="Invalid Credentials ❌")

    return render_template('admin_login.html')


@app.route('/admin/dashboard')
def admin_dashboard():
    conn = get_db_connection()
    products = conn.execute('SELECT * FROM products').fetchall()
    enquiries = conn.execute('SELECT * FROM enquiries').fetchall()
    conn.close()
    return render_template('admin_dashboard.html', products=products, enquiries=enquiries)


@app.route('/admin/add', methods=['GET', 'POST'])
def add_product():
    if request.method == 'POST':
        name = request.form['name']
        price = request.form['price']
        description = request.form['description']
        image = request.files['image']

        image_path = ''
        if image:
            image_path = image.filename
            upload_dir = os.path.join('static', 'uploads')
            os.makedirs(upload_dir, exist_ok=True)
            image.save(os.path.join(upload_dir, image_path))

        conn = get_db_connection()
        conn.execute('INSERT INTO products (name, price, description, image) VALUES (?, ?, ?, ?)',
                     (name, price, description, image_path))
        conn.commit()
        conn.close()

        return redirect(url_for('admin_dashboard'))

    return render_template('add_product.html')


@app.route('/admin/enquiries')
def view_enquiries():
    conn = get_db_connection()
    enquiries = conn.execute('SELECT * FROM enquiries').fetchall()
    conn.close()
    return render_template('view_enquiries.html', enquiries=enquiries)


# ---------- MAIN ----------
if __name__ == '__main__':
    initialize_db()  # 💾 This ensures tables and sample sarees are ready
    app.run(debug=True)
