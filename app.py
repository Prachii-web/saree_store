from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
import razorpay
from datetime import datetime
import uuid


app = Flask(__name__)
app.secret_key = 'your_secret_key'

# ---------- RAZORPAY CLIENT SETUP ----------
razorpay_client = razorpay.Client(auth=("YOUR_KEY_ID", "YOUR_KEY_SECRET"))

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
    user_name = session.get('user_name')
    return render_template('index.html', products=products, user_name=user_name)

# ---------- REGISTER ----------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        address = request.form['address']

        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO users (name, email, password, address) VALUES (?, ?, ?, ?)',
                         (name, email, password, address))
            conn.commit()
            flash('✅ Account created successfully! Please login.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('❌ Email already registered!', 'error')
        finally:
            conn.close()
    return render_template('register.html')

# ---------- LOGIN ----------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ? AND password = ?', (email, password)).fetchone()
        conn.close()

        if user:
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            flash(f'✅ Welcome back, {user["name"]}!', 'success')
            return redirect(url_for('user_dashboard'))
        else:
            flash('❌ Invalid credentials!', 'error')

    return render_template('login.html')

# ---------- LOGOUT ----------
@app.route('/logout')
def logout():
    session.clear()
    flash('✅ Logged out successfully!', 'success')
    return redirect(url_for('index'))

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
        flash("✅ Message sent successfully!", "success")
        return redirect(url_for('index'))

    return render_template('contact.html')

# ---------- BUY PRODUCT PAGE ----------
@app.route('/buy/<int:product_id>', methods=['GET', 'POST'])
def buy_product(product_id):
    if 'user_id' not in session:
        flash("Please login first to place an order.", "warning")
        return redirect(url_for('login'))

    conn = get_db_connection()
    product = conn.execute(
        "SELECT * FROM products WHERE id = ?", (product_id,)
    ).fetchone()

    if request.method == 'POST':
        name = request.form['name']
        address = request.form['address']
        contact = request.form['contact']

        # 🟢 Create order
        conn.execute("""
            INSERT INTO orders
            (user_id, product_id, customer_name, address, contact, status)
            VALUES (?, ?, ?, ?, ?, 'Pending')
        """, (
            session['user_id'],
            product_id,
            name,
            address,
            contact
        ))

        # ✅ order_id exists ONLY here
        order_id = conn.execute(
            "SELECT last_insert_rowid()"
        ).fetchone()[0]

        conn.commit()
        conn.close()

        # ✅ Redirect ONLY after order is created
        return redirect(url_for('payment', order_id=order_id))

    conn.close()
    return render_template('buy.html', product=product)




@app.route('/payment/<int:order_id>', methods=['GET', 'POST'])
def payment(order_id):
    if 'user_id' not in session:
        flash("Please login first.", "warning")
        return redirect(url_for('login'))

    conn = get_db_connection()

    # Fetch order + product details
    order = conn.execute("""
        SELECT o.id, o.customer_name, o.address, o.contact, p.name AS product_name,
               p.quantity, pay.status AS payment_status, pay.payment_mode, o.user_id, o.product_id
        FROM orders o
        JOIN products p ON o.product_id = p.id
        LEFT JOIN payments pay ON o.id = pay.order_id
        WHERE o.id = ?
    """, (order_id,)).fetchone()

    if not order:
        flash("Invalid order.", "danger")
        conn.close()
        return redirect(url_for('user_dashboard'))

    if request.method == 'POST':
        amount = request.form['amount']
        mode = request.form['mode']
        payment_id = str(uuid.uuid4())

        try:
            # Save payment
            conn.execute("""
                INSERT INTO payments (payment_id, order_id, customer_name, amount, payment_mode, status)
                VALUES (?, ?, ?, ?, ?, 'Paid')
            """, (
                payment_id,
                order_id,
                order['customer_name'],
                amount,
                mode
            ))

            # Update order status
            conn.execute("""
                UPDATE orders SET order_status = 'Paid' WHERE id = ?
            """, (order_id,))

            # Reduce stock
            if order['quantity'] > 0:
                conn.execute("""
                    UPDATE products SET quantity = quantity - 1 WHERE id = ?
                """, (order['product_id'],))
            else:
                flash("⚠️ Product out of stock!", "danger")
                conn.rollback()
                conn.close()
                return redirect(url_for('user_dashboard'))

            conn.commit()
            flash("💰 Payment successful!", "success")
        except Exception as e:
            conn.rollback()
            flash(f"Payment failed: {e}", "danger")
        finally:
            conn.close()

        return redirect(url_for('user_dashboard'))

    # GET request renders payment page
    conn.close()
    return render_template('payment.html', order=order)



# ---------- CUSTOMER DASHBOARD ----------
@app.route('/dashboard', endpoint='user_dashboard')
def user_dashboard():
    if 'user_id' not in session:
        flash("Please login first!", "warning")
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = get_db_connection()

    # Fetch orders for this customer
    orders = conn.execute("""
        SELECT o.id, o.customer_name, o.address, o.contact, p.name AS product_name,
               o.order_status, o.delivery_date
        FROM orders o
        JOIN products p ON o.product_id = p.id
        WHERE o.user_id = ?
    """, (user_id,)).fetchall()

    # Fetch admin messages for this customer
   # Fetch admin messages for logged-in user
    messages = conn.execute("""
        SELECT m.order_id, m.message AS admin_reply, m.date, p.name AS product_name
        FROM order_messages m
        JOIN orders o ON m.order_id = o.id
        JOIN products p ON o.product_id = p.id
        WHERE m.user_id = ?
        ORDER BY m.date DESC
    """, (user_id,)).fetchall()


    conn.close()
    return render_template('user_dashboard.html', orders=orders, messages=messages)


    # Fetch orders
    orders = conn.execute("""
        SELECT o.id, o.customer_name, o.address, o.contact, p.name AS product_name, o.order_status, o.delivery_date
        FROM orders o
        JOIN products p ON o.product_id = p.id
        WHERE o.user_id = ?
    """, (user_id,)).fetchall()

    # Fetch admin messages
    messages = conn.execute("""
        SELECT m.order_id, m.message, m.date, p.name AS product_name
        FROM order_messages m
        JOIN orders o ON m.order_id = o.id
        JOIN products p ON o.product_id = p.id
        WHERE m.user_id = ?
        ORDER BY m.date DESC
    """, (user_id,)).fetchall()

    conn.close()
    return render_template('user_dashboard.html', orders=orders, messages=messages)

# ---------- ADMIN LOGIN ----------
@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username == 'prachu' and password == '2812':
            session['admin'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            return render_template('admin_login.html', error="Invalid Credentials ❌")
    return render_template('admin_login.html')

# ---------- ADMIN DASHBOARD ----------
@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin'):
        flash("Admin login required!", "error")
        return redirect(url_for('admin_login'))

    conn = get_db_connection()
    products = conn.execute('SELECT * FROM products').fetchall()
    enquiries = conn.execute('SELECT * FROM enquiries').fetchall()
    orders = conn.execute("""
    SELECT o.id, o.user_id, o.customer_name, o.address, o.contact,
        p.name AS product_name,
        COALESCE(pay.status, 'Pending') AS payment_status,
        pay.payment_mode,
        o.delivery_date
    FROM orders o
    JOIN products p ON o.product_id = p.id
    LEFT JOIN payments pay ON o.id = pay.order_id
    ORDER BY o.id DESC
    """).fetchall()


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
        flash("✅ Product added successfully!", "success")
        return redirect(url_for('admin_dashboard'))

    return render_template('add_product.html')

# ---------- DELETE PRODUCT ----------
@app.route('/delete/<int:id>')
def delete_product(id):
    conn = get_db_connection()
    conn.execute("DELETE FROM products WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    flash("✅ Product deleted successfully!", "success")
    return redirect(url_for('admin_dashboard'))

# ---------- DELETE ORDER ----------
@app.route('/delete_order/<int:order_id>')
def delete_order(order_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM orders WHERE id = ?", (order_id,))
    conn.commit()
    conn.close()
    flash("✅ Order deleted successfully!", "success")
    return redirect(url_for('admin_dashboard'))

# ---------- SEND ORDER MESSAGE ----------
@app.route('/admin/send_order_message', methods=['POST'])
def admin_send_order_message():
    user_id = request.form['user_id']
    order_id = request.form['order_id']
    message = request.form['message']

    conn = get_db_connection()
    conn.execute(
        "INSERT INTO order_messages (user_id, order_id, message, date) VALUES (?, ?, ?, ?)",
        (user_id, order_id, message, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    )
    conn.commit()
    conn.close()

    flash("✅ Message sent to customer!")
    return redirect(url_for('admin_dashboard'))

# ---------- UPDATE PRICE / QUANTITY ----------
@app.route('/admin/update_price/<int:product_id>', methods=['POST'])
def update_price(product_id):
    new_price = request.form['price']
    conn = get_db_connection()
    conn.execute('UPDATE products SET price = ? WHERE id = ?', (new_price, product_id))
    conn.commit()
    conn.close()
    flash(f'✅ Price updated for product ID {product_id}', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/update_quantity/<int:product_id>', methods=['POST'])
def update_quantity(product_id):
    new_quantity = request.form['quantity']
    conn = get_db_connection()
    conn.execute('UPDATE products SET quantity = ? WHERE id = ?', (new_quantity, product_id))
    conn.commit()
    conn.close()
    flash(f'✅ Quantity updated for product ID {product_id}', 'success')
    return redirect(url_for('admin_dashboard'))

# ---------- RUN APP ----------
if __name__ == '__main__':
    app.run(debug=True)
