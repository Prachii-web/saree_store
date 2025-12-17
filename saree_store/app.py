from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import sqlite3
import razorpay   # <-- added for payment gateway

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# ---------- RAZORPAY CLIENT SETUP ----------
razorpay_client = razorpay.Client(auth=("YOUR_KEY_ID", "YOUR_KEY_SECRET"))  # Replace with your Razorpay test keys


# ---------- DATABASE CONNECTION ----------
def get_db_connection():
    conn = sqlite3.connect('saree_store.db')
    conn.row_factory = sqlite3.Row
    return conn


# ---------- HOME PAGE ----------
@app.route('/')
def index():
    conn = get_db_connection()
    products = conn.execute('SELECT * FROM products').fetchall()
    conn.close()
    return render_template('index.html', products=products)


# ---------- CONTACT PAGE ----------
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


# ---------- BUY PRODUCT PAGE ----------
@app.route('/buy/<int:product_id>', methods=['GET', 'POST'])
def buy_product(product_id):
    conn = get_db_connection()
    product = conn.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()

    if not product:
        conn.close()
        return "Product not found", 404

    if request.method == 'POST':
        name = request.form['name']
        address = request.form['address']
        contact = request.form['contact']

        conn.execute(
            'INSERT INTO orders (product_id, customer_name, address, contact) VALUES (?, ?, ?, ?)',
            (product_id, name, address, contact)
        )
        conn.commit()
        conn.close()

        return render_template('order_success.html', product=product, name=name)

    conn.close()
    return render_template('buy.html', product=product)


# ---------- PAYMENT PAGE ----------
@app.route('/payment', methods=['GET', 'POST'])
def payment():
    if request.method == 'POST':
        customer_name = request.form['customer_name']
        amount = int(float(request.form['amount']) * 100)  # Razorpay works in paise

        # Create Razorpay order
        order = razorpay_client.order.create({
            "amount": amount,
            "currency": "INR",
            "payment_capture": "1"
        })

        return render_template('checkout.html',
                               customer_name=customer_name,
                               amount=amount,
                               order_id=order['id'],
                               key_id="rzp_test_RcvPgVgWJGUzQu")  # Replace YOUR_KEY_ID
    return render_template('payment.html')


# ---------- VERIFY PAYMENT ----------
# ---------- VERIFY PAYMENT ----------
@app.route('/verify_payment', methods=['POST'])
def verify_payment():
    data = request.form
    try:
        # Verify Razorpay signature
        razorpay_client.utility.verify_payment_signature({
            'razorpay_order_id': data['razorpay_order_id'],
            'razorpay_payment_id': data['razorpay_payment_id'],
            'razorpay_signature': data['razorpay_signature']
        })

        conn = get_db_connection()
        conn.execute('''
            INSERT INTO payments (customer_name, order_id, payment_id, amount, status)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            data.get('customer_name', 'Unknown'),
            data['razorpay_order_id'],
            data['razorpay_payment_id'],
            int(data.get('amount', 0)) // 100,
            'Success'
        ))
        conn.commit()
        conn.close()

        return render_template('payment_success.html')

    except Exception as e:
        print("Verification failed:", e)
        return render_template('payment_failed.html')


    # Record payment in DB
    conn = get_db_connection()
    conn.execute('INSERT INTO payments (customer_name, amount, date) VALUES (?, ?, datetime("now","localtime"))',
                 ("Test User", float(data.get('amount', 0)) / 100))
    conn.commit()
    conn.close()

    return redirect(url_for('payment_success'))


# ---------- PAYMENT SUCCESS ----------
@app.route('/payment_success')
def payment_success():
    return render_template('success.html', message="✅ Payment processed successfully!")


# ---------- ADMIN LOGIN ----------
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


#-----------ADMIN DASHBOARD------------
@app.route('/admin/dashboard')
def admin_dashboard():
    conn = get_db_connection()
    products = conn.execute('SELECT * FROM products').fetchall()
    enquiries = conn.execute('SELECT * FROM enquiries').fetchall()
    orders = conn.execute('''
        SELECT o.id, o.customer_name, o.address, o.contact, p.name AS product_name
        FROM orders o
        JOIN products p ON o.product_id = p.id
    ''').fetchall()
    payments = conn.execute('SELECT * FROM payments').fetchall()
    conn.close()

    return render_template('admin_dashboard.html',
                           products=products,
                           enquiries=enquiries,
                           orders=orders,
                           payments=payments)


# ---------- ADD PRODUCT ----------
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
            image.save('static/uploads/' + image_path)

        conn = get_db_connection()
        conn.execute('INSERT INTO products (name, price, description, image) VALUES (?, ?, ?, ?)',
                     (name, price, description, image_path))
        conn.commit()
        conn.close()

        return redirect(url_for('admin_dashboard'))

    return render_template('add_product.html')


# ---------- VIEW ENQUIRIES ----------
@app.route('/admin/enquiries')
def view_enquiries():
    conn = get_db_connection()
    enquiries = conn.execute('SELECT * FROM enquiries').fetchall()
    conn.close()
    return render_template('view_enquiries.html', enquiries=enquiries)

@app.route("/category/<name>")
def category_page(name):
    conn = sqlite3.connect("saree_store.db")  # FIXED DB NAME
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT * FROM products WHERE category=?", (name,))  # FIXED TABLE NAME
    data = cur.fetchall()
    conn.close()

    return render_template("category.html", products=data, cat=name)

@app.route('/products')
def products():
    conn = sqlite3.connect('saree_store.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products;")
    items = cursor.fetchall()
    conn.close()
    return render_template('products.html', products=items)


# ---------- RUN APP ----------
if __name__ == '__main__':
    app.run(debug=True)
