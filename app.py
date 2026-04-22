from flask import Flask, send_from_directory, request, jsonify, session, redirect
import json, os, base64, uuid
from functools import wraps
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'ptod-secret-change-me'

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
PRODUCTS_F  = os.path.join(BASE_DIR, 'products.json')
UPLOADS_DIR = os.path.join(BASE_DIR, 'uploads')
ADMIN_PASS  = 'preparetodye2024'   # ← change this

os.makedirs(UPLOADS_DIR, exist_ok=True)

def load_products():
    if not os.path.exists(PRODUCTS_F):
        return []
    with open(PRODUCTS_F) as f:
        return json.load(f)

def save_products(products):
    with open(PRODUCTS_F, 'w') as f:
        json.dump(products, f, indent=2)

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect('/admin/login')
        return f(*args, **kwargs)
    return decorated

# ── SITE ──
@app.route('/')
def index():
    return send_from_directory(BASE_DIR, 'index.html')

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOADS_DIR, filename)

# ── PUBLIC API ──
@app.route('/api/products')
def api_products():
    return jsonify(load_products())

# ── ADMIN LOGIN ──
@app.route('/admin/login', methods=['GET'])
def admin_login_page():
    return '''<!DOCTYPE html>
<html><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Admin Login — Prepare To Dye</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;}
body{font-family:Nunito,sans-serif;background:#0a0402;min-height:100vh;display:flex;align-items:center;justify-content:center;}
@import url('https://fonts.googleapis.com/css2?family=Pacifico&family=Nunito:wght@700;900&display=swap');
.box{background:rgba(242,232,212,.97);border-radius:16px;padding:2.5rem 2rem;width:min(90vw,380px);text-align:center;box-shadow:0 30px 80px rgba(0,0,0,.8);}
h1{font-family:Pacifico,cursive;font-size:1.8rem;color:#1a0804;margin-bottom:.3rem;}
p{font-size:.8rem;color:rgba(26,8,4,.5);margin-bottom:1.5rem;}
input{width:100%;padding:.75rem 1rem;border-radius:8px;border:1.5px solid rgba(26,8,4,.15);background:rgba(26,8,4,.04);font-family:Nunito,sans-serif;font-size:.95rem;margin-bottom:.85rem;outline:none;}
input:focus{border-color:rgba(0,185,168,.5);}
button{width:100%;padding:.75rem;border-radius:50px;background:#7a1418;color:#fff;border:none;font-family:Nunito,sans-serif;font-weight:900;font-size:1rem;cursor:pointer;}
.err{color:#c0392b;font-size:.8rem;margin-bottom:.8rem;display:none;}
</style></head>
<body><div class="box">
<h1>Prepare To Dye</h1>
<p>Admin Dashboard</p>
<div class="err" id="err">Wrong password</div>
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
    product_rows = ''
    for p in products:
        product_rows += f'''
        <tr>
          <td><img src="{p["image"]}" style="width:48px;height:48px;border-radius:50%;object-fit:cover;"></td>
          <td>{p["name"]}</td>
          <td>{p["description"][:40]}...</td>
          <td>${p["price"]}</td>
          <td>{"✅ Active" if p.get("active", True) else "⏸ Hidden"}</td>
          <td>
            <a href="/admin/toggle/{p["id"]}" style="color:#0a7858;font-weight:900;text-decoration:none;">{"Hide" if p.get("active",True) else "Show"}</a>
            &nbsp;|&nbsp;
            <a href="/admin/delete/{p["id"]}" style="color:#c0392b;font-weight:900;text-decoration:none;" onclick="return confirm('Delete this product?')">Delete</a>
          </td>
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
header a{{color:rgba(240,200,120,.6);font-size:.78rem;font-weight:900;text-decoration:none;}}
.wrap{{max-width:900px;margin:0 auto;padding:1.5rem;}}
.card{{background:#fff;border-radius:12px;padding:1.5rem;margin-bottom:1.5rem;box-shadow:0 2px 12px rgba(0,0,0,.08);}}
.card h2{{font-family:Pacifico,cursive;font-size:1.2rem;color:#1a0804;margin-bottom:1rem;}}
label{{display:block;font-size:.78rem;font-weight:900;letter-spacing:.06em;text-transform:uppercase;color:rgba(26,8,4,.5);margin-bottom:.3rem;margin-top:.75rem;}}
input,textarea{{width:100%;padding:.65rem .9rem;border-radius:8px;border:1.5px solid rgba(26,8,4,.12);font-family:Nunito,sans-serif;font-size:.9rem;background:rgba(26,8,4,.03);}}
textarea{{height:80px;resize:vertical;}}
input:focus,textarea:focus{{outline:none;border-color:rgba(0,185,168,.5);}}
.btn{{display:inline-block;padding:.65rem 1.5rem;border-radius:50px;background:#7a1418;color:#fff;border:none;font-family:Nunito,sans-serif;font-weight:900;font-size:.9rem;cursor:pointer;margin-top:1rem;}}
.btn:hover{{background:#9a2428;}}
table{{width:100%;border-collapse:collapse;}}
th{{text-align:left;font-size:.72rem;font-weight:900;letter-spacing:.08em;text-transform:uppercase;color:rgba(26,8,4,.4);padding:.5rem .75rem;border-bottom:2px solid rgba(26,8,4,.08);}}
td{{padding:.6rem .75rem;border-bottom:1px solid rgba(26,8,4,.06);font-size:.85rem;vertical-align:middle;}}
tr:hover td{{background:rgba(0,185,168,.04);}}
.empty{{text-align:center;color:rgba(26,8,4,.35);padding:2rem;font-size:.9rem;}}
.preview{{width:80px;height:80px;border-radius:50%;object-fit:cover;border:2px solid rgba(0,185,168,.3);margin-top:.5rem;display:none;}}
</style></head>
<body>
<header>
  <h1>Prepare To Dye</h1>
  <a href="/admin/logout">Log Out</a>
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
      <label>Photo</label>
      <input type="file" name="image" accept="image/*" required onchange="previewImg(this)">
      <img id="preview" class="preview">
      <br><button type="submit" class="btn">Add Product</button>
    </form>
  </div>

  <!-- PRODUCT LIST -->
  <div class="card">
    <h2>Products ({len(products)} total)</h2>
    {"<table><thead><tr><th>Photo</th><th>Name</th><th>Description</th><th>Price</th><th>Status</th><th>Actions</th></tr></thead><tbody>" + product_rows + "</tbody></table>" if products else '<p class="empty">No products yet — add one above and it will appear on the site.</p>'}
  </div>

</div>
<script>
function previewImg(input) {{
  var preview = document.getElementById('preview');
  if (input.files && input.files[0]) {{
    var reader = new FileReader();
    reader.onload = function(e) {{ preview.src = e.target.result; preview.style.display='block'; }};
    reader.readAsDataURL(input.files[0]);
  }}
}}
</script>
</body></html>'''

# ── ADMIN ACTIONS ──
@app.route('/admin/add', methods=['POST'])
@login_required
def admin_add():
    products = load_products()
    file = request.files.get('image')
    if not file:
        return redirect('/admin')

    ext = file.filename.rsplit('.', 1)[-1].lower()
    filename = str(uuid.uuid4()) + '.' + ext
    file.save(os.path.join(UPLOADS_DIR, filename))

    product = {
        'id':          str(uuid.uuid4()),
        'name':        request.form['name'],
        'description': request.form['description'],
        'price':       float(request.form['price']),
        'image':       '/uploads/' + filename,
        'active':      True,
        'created':     datetime.now().isoformat()
    }
    products.append(product)
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

# Update public API to only return active products
@app.route('/api/products')
def api_products_active():
    return jsonify([p for p in load_products() if p.get('active', True)])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=4001)
