from flask import Flask, send_from_directory, request, jsonify, session, redirect
import json, os, uuid, smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from functools import wraps
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'ptod-secret-change-me'

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
PRODUCTS_F  = os.path.join(BASE_DIR, 'products.json')
ORDERS_F    = os.path.join(BASE_DIR, 'orders.json')
UPLOADS_DIR = os.path.join(BASE_DIR, 'uploads')
ADMIN_PASS  = 'preparetodye2024'

# ── SMTP (placeholder credentials — swap before going live) ──
SMTP_HOST   = 'smtp.gmail.com'
SMTP_PORT   = 587
SMTP_USER   = 'preparetodye@gmail.com'
SMTP_PASS   = 'your-app-password-here'
ADMIN_EMAIL = 'preparetodye@gmail.com'

# ── PayPal sandbox client ID (placeholder — swap for live before going live) ──
PAYPAL_CLIENT_ID = 'AZkQ7vKR-SANDBOX-CLIENT-ID-PLACEHOLDER'

os.makedirs(UPLOADS_DIR, exist_ok=True)


def load_products():
    if not os.path.exists(PRODUCTS_F):
        return []
    with open(PRODUCTS_F) as f:
        return json.load(f)

def save_products(products):
    with open(PRODUCTS_F, 'w') as f:
        json.dump(products, f, indent=2)

def load_orders():
    if not os.path.exists(ORDERS_F):
        return []
    with open(ORDERS_F) as f:
        return json.load(f)

def save_orders(orders):
    with open(ORDERS_F, 'w') as f:
        json.dump(orders, f, indent=2)

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect('/admin/login')
        return f(*args, **kwargs)
    return decorated

def send_order_email(order, customer):
    """Send order confirmation to customer and notification to admin."""
    customer_email = customer.get('email', '')
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"Order Confirmed — {order['product_name']}"
        msg['From']    = SMTP_USER
        msg['To']      = customer_email

        body = f"""
Hi {customer.get('name', 'there')}!

Your order has been placed. Here's your summary:

  Item:     {order['product_name']}
  Qty:      {order['quantity']}
  Total:    ${order['total']:.2f}
  Order ID: {order['id']}
  PayPal:   {order['paypal_order_id']}

We'll be in touch soon with pickup or shipping details.

— Prepare To Dye
"""
        msg.attach(MIMEText(body, 'plain'))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            if customer_email:
                server.sendmail(SMTP_USER, customer_email, msg.as_string())

            # Admin notification
            admin_msg = MIMEMultipart('alternative')
            admin_msg['Subject'] = f"New Order: {order['product_name']} x{order['quantity']}"
            admin_msg['From']    = SMTP_USER
            admin_msg['To']      = ADMIN_EMAIL
            admin_body = f"""New order received!

  Customer: {customer.get('name', 'N/A')} <{customer_email}>
  Item:     {order['product_name']}
  Qty:      {order['quantity']}
  Total:    ${order['total']:.2f}
  Order ID: {order['id']}
  PayPal:   {order['paypal_order_id']}
  Time:     {order['created']}
"""
            admin_msg.attach(MIMEText(admin_body, 'plain'))
            server.sendmail(SMTP_USER, ADMIN_EMAIL, admin_msg.as_string())
    except Exception:
        # Email failure is non-fatal; order is already saved
        pass


# ── SITE ──
@app.route('/')
def index():
    return send_from_directory(BASE_DIR, 'index.html')

@app.route('/shop')
def shop():
    return send_from_directory(BASE_DIR, 'shop.html')

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOADS_DIR, filename)


# ── PUBLIC API ──
@app.route('/api/products')
def api_products():
    return jsonify([p for p in load_products() if p.get('active', True)])

@app.route('/api/paypal-client-id')
def api_paypal_client_id():
    return jsonify({'client_id': PAYPAL_CLIENT_ID})

@app.route('/api/order', methods=['POST'])
def api_order():
    data       = request.get_json(force=True)
    product_id = data.get('product_id', '')
    quantity   = max(1, int(data.get('quantity', 1)))
    customer   = data.get('customer', {})
    paypal_id  = data.get('paypal_order_id', '')

    products = load_products()
    product  = next((p for p in products if p['id'] == product_id), None)
    if not product:
        return jsonify({'error': 'Product not found'}), 404
    if not product.get('active', True):
        return jsonify({'error': 'Product unavailable'}), 400
    if product.get('stock', 0) < quantity:
        return jsonify({'error': 'Not enough stock'}), 400

    for p in products:
        if p['id'] == product_id:
            p['stock'] = p.get('stock', 0) - quantity
    save_products(products)

    order = {
        'id':            str(uuid.uuid4()),
        'product_id':    product_id,
        'product_name':  product['name'],
        'price':         product['price'],
        'quantity':      quantity,
        'total':         round(product['price'] * quantity, 2),
        'customer':      customer,
        'paypal_order_id': paypal_id,
        'created':       datetime.now().isoformat(),
    }
    orders = load_orders()
    orders.insert(0, order)
    save_orders(orders)

    send_order_email(order, customer)
    return jsonify({'success': True, 'order_id': order['id']})


# ── ADMIN LOGIN ──
@app.route('/admin/login', methods=['GET'])
def admin_login_page():
    err = ''.join([
        '<div style="color:#c0392b;font-size:.8rem;margin-bottom:.8rem">Wrong password</div>'
    ]) if request.args.get('err') else ''
    return f'''<!DOCTYPE html>
<html><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Admin Login — Prepare To Dye</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box;}}
body{{font-family:Nunito,sans-serif;background:#0a0402;min-height:100vh;display:flex;align-items:center;justify-content:center;}}
@import url('https://fonts.googleapis.com/css2?family=Pacifico&family=Nunito:wght@700;900&display=swap');
.box{{background:rgba(242,232,212,.97);border-radius:16px;padding:2.5rem 2rem;width:min(90vw,380px);text-align:center;box-shadow:0 30px 80px rgba(0,0,0,.8);}}
h1{{font-family:Pacifico,cursive;font-size:1.8rem;color:#1a0804;margin-bottom:.3rem;}}
p{{font-size:.8rem;color:rgba(26,8,4,.5);margin-bottom:1.5rem;}}
input{{width:100%;padding:.75rem 1rem;border-radius:8px;border:1.5px solid rgba(26,8,4,.15);background:rgba(26,8,4,.04);font-family:Nunito,sans-serif;font-size:.95rem;margin-bottom:.85rem;outline:none;}}
input:focus{{border-color:rgba(0,185,168,.5);}}
button{{width:100%;padding:.75rem;border-radius:50px;background:#7a1418;color:#fff;border:none;font-family:Nunito,sans-serif;font-weight:900;font-size:1rem;cursor:pointer;}}
</style></head>
<body><div class="box">
<h1>Prepare To Dye</h1>
<p>Admin Dashboard</p>
{err}
<form method="POST" action="/admin/login">
<input type="password" name="password" placeholder="Password" autofocus>
<button type="submit">Log In</button>
</form>
</div></body></html>'''

@app.route('/admin/login', methods=['POST'])
def admin_login():
    if request.form.get('password') == ADMIN_PASS:
        session['logged_in'] = True
        return redirect('/admin')
    return redirect('/admin/login?err=1')

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect('/admin/login')


# ── ADMIN DASHBOARD ──
@app.route('/admin')
@login_required
def admin_dashboard():
    products = load_products()
    orders   = load_orders()

    product_rows = ''
    for p in products:
        stock = p.get('stock', 0)
        stock_color = '#0a7858' if stock > 5 else ('#e67e22' if stock > 0 else '#c0392b')
        product_rows += f'''
        <tr>
          <td><img src="{p['image']}" style="width:48px;height:48px;border-radius:50%;object-fit:cover;"></td>
          <td>{p['name']}</td>
          <td>${p['price']:.2f}</td>
          <td style="color:{stock_color};font-weight:900;">{stock}</td>
          <td>{"Active" if p.get("active", True) else "Hidden"}</td>
          <td>
            <form method="POST" action="/admin/stock/{p['id']}" style="display:inline;gap:.3rem;display:flex;align-items:center;">
              <input type="number" name="stock" value="{stock}" min="0" style="width:64px;padding:.25rem .4rem;border-radius:6px;border:1px solid #ccc;font-size:.8rem;">
              <button type="submit" style="padding:.25rem .7rem;border-radius:6px;background:#0a7858;color:#fff;border:none;font-size:.78rem;cursor:pointer;">Set</button>
            </form>
          </td>
          <td>
            <a href="/admin/toggle/{p['id']}" style="color:#555;font-weight:900;text-decoration:none;font-size:.8rem;">{"Hide" if p.get("active",True) else "Show"}</a>
            &nbsp;|&nbsp;
            <a href="/admin/delete/{p['id']}" style="color:#c0392b;font-weight:900;text-decoration:none;font-size:.8rem;" onclick="return confirm('Delete?')">Del</a>
          </td>
        </tr>'''

    order_rows = ''
    for o in orders[:50]:
        c = o.get('customer', {})
        order_rows += f'''
        <tr>
          <td style="font-size:.72rem;color:#888;">{o['created'][:16]}</td>
          <td>{o['product_name']}</td>
          <td>{o['quantity']}</td>
          <td>${o['total']:.2f}</td>
          <td>{c.get('name','—')}</td>
          <td style="font-size:.72rem;">{c.get('email','—')}</td>
        </tr>'''

    return f'''<!DOCTYPE html>
<html><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Admin — Prepare To Dye</title>
<link href="https://fonts.googleapis.com/css2?family=Pacifico&family=Nunito:wght@500;700;900&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box;}}
body{{font-family:Nunito,sans-serif;background:#f5ede0;color:#1a0804;}}
header{{background:#1a0804;padding:1rem 1.5rem;display:flex;align-items:center;justify-content:space-between;}}
header h1{{font-family:Pacifico,cursive;color:#f0d060;font-size:1.3rem;}}
header a{{color:rgba(240,200,120,.6);font-size:.78rem;font-weight:900;text-decoration:none;margin-left:1rem;}}
.wrap{{max-width:960px;margin:0 auto;padding:1.5rem;}}
.card{{background:#fff;border-radius:12px;padding:1.5rem;margin-bottom:1.5rem;box-shadow:0 2px 12px rgba(0,0,0,.08);}}
.card h2{{font-family:Pacifico,cursive;font-size:1.2rem;color:#1a0804;margin-bottom:1rem;}}
label{{display:block;font-size:.78rem;font-weight:900;letter-spacing:.06em;text-transform:uppercase;color:rgba(26,8,4,.5);margin-bottom:.3rem;margin-top:.75rem;}}
input[type=text],input[type=number],textarea{{width:100%;padding:.65rem .9rem;border-radius:8px;border:1.5px solid rgba(26,8,4,.12);font-family:Nunito,sans-serif;font-size:.9rem;background:rgba(26,8,4,.03);}}
input[type=file]{{padding:.4rem 0;}}
textarea{{height:80px;resize:vertical;}}
.btn{{display:inline-block;padding:.65rem 1.5rem;border-radius:50px;background:#7a1418;color:#fff;border:none;font-family:Nunito,sans-serif;font-weight:900;font-size:.9rem;cursor:pointer;margin-top:1rem;}}
table{{width:100%;border-collapse:collapse;}}
th{{text-align:left;font-size:.72rem;font-weight:900;letter-spacing:.08em;text-transform:uppercase;color:rgba(26,8,4,.4);padding:.5rem .6rem;border-bottom:2px solid rgba(26,8,4,.08);}}
td{{padding:.55rem .6rem;border-bottom:1px solid rgba(26,8,4,.06);font-size:.84rem;vertical-align:middle;}}
tr:hover td{{background:rgba(0,185,168,.04);}}
.empty{{text-align:center;color:rgba(26,8,4,.35);padding:2rem;font-size:.9rem;}}
</style></head>
<body>
<header>
  <h1>Prepare To Dye</h1>
  <div>
    <a href="/shop" target="_blank">View Shop</a>
    <a href="/admin/logout">Log Out</a>
  </div>
</header>
<div class="wrap">

  <!-- ADD PRODUCT -->
  <div class="card">
    <h2>Add New Product</h2>
    <form method="POST" action="/admin/add" enctype="multipart/form-data">
      <label>Product Name</label>
      <input type="text" name="name" placeholder="e.g. Blue Spiral Tee — Medium" required>
      <label>Description</label>
      <textarea name="description" placeholder="Describe the item..." required></textarea>
      <label>Price ($)</label>
      <input type="number" name="price" step="0.01" min="0" placeholder="25.00" required>
      <label>Stock (quantity available)</label>
      <input type="number" name="stock" min="0" value="1" required>
      <label>Photo</label>
      <input type="file" name="image" accept="image/*" required>
      <br><button type="submit" class="btn">Add Product</button>
    </form>
  </div>

  <!-- PRODUCT LIST -->
  <div class="card">
    <h2>Products ({len(products)} total)</h2>
    {"<table><thead><tr><th>Photo</th><th>Name</th><th>Price</th><th>Stock</th><th>Status</th><th>Update Stock</th><th>Actions</th></tr></thead><tbody>" + product_rows + "</tbody></table>" if products else '<p class="empty">No products yet.</p>'}
  </div>

  <!-- ORDERS -->
  <div class="card">
    <h2>Recent Orders ({len(orders)} total)</h2>
    {"<table><thead><tr><th>Date</th><th>Item</th><th>Qty</th><th>Total</th><th>Customer</th><th>Email</th></tr></thead><tbody>" + order_rows + "</tbody></table>" if orders else '<p class="empty">No orders yet.</p>'}
  </div>

</div>
</body></html>'''


# ── ADMIN ACTIONS ──
@app.route('/admin/add', methods=['POST'])
@login_required
def admin_add():
    products = load_products()
    file = request.files.get('image')
    if not file:
        return redirect('/admin')

    ext      = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else 'jpg'
    filename = str(uuid.uuid4()) + '.' + ext
    file.save(os.path.join(UPLOADS_DIR, filename))

    product = {
        'id':          str(uuid.uuid4()),
        'name':        request.form['name'],
        'description': request.form['description'],
        'price':       float(request.form['price']),
        'stock':       int(request.form.get('stock', 1)),
        'image':       '/uploads/' + filename,
        'active':      True,
        'created':     datetime.now().isoformat(),
    }
    products.append(product)
    save_products(products)
    return redirect('/admin')

@app.route('/admin/stock/<product_id>', methods=['POST'])
@login_required
def admin_stock(product_id):
    new_stock = int(request.form.get('stock', 0))
    products  = load_products()
    for p in products:
        if p['id'] == product_id:
            p['stock'] = max(0, new_stock)
    save_products(products)
    return redirect('/admin')

@app.route('/admin/delete/<product_id>')
@login_required
def admin_delete(product_id):
    products = [p for p in load_products() if p['id'] != product_id]
    save_products(products)
    return redirect('/admin')

@app.route('/admin/toggle/<product_id>')
@login_required
def admin_toggle(product_id):
    products = load_products()
    for p in products:
        if p['id'] == product_id:
            p['active'] = not p.get('active', True)
    save_products(products)
    return redirect('/admin')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=4001, debug=True)
