from flask import Flask, request, jsonify, render_template_string, redirect, url_for, session
from flask_cors import CORS
from datetime import datetime, timedelta
import secrets
import string
import os
import hashlib
import sqlite3
import re
import base64

app = Flask(__name__)
app.secret_key = os.urandom(24)
CORS(app)

# ============ ENCRYPTION (KEY HARDCODED INSIDE) ============

def enc(text):
    k = "U7m9x2L5p8R4v1Y3n6Q0t9E2w7A4d6"
    result = ""
    for i, c in enumerate(text):
        result += chr(ord(c) ^ ord(k[i % len(k)]))
    return base64.b64encode(result.encode()).decode()

def dec(text):
    k = "U7m9x2L5p8R4v1Y3n6Q0t9E2w7A4d6"
    try:
        decoded = base64.b64decode(text.encode()).decode()
        result = ""
        for i, c in enumerate(decoded):
            result += chr(ord(c) ^ ord(k[i % len(k)]))
        return result
    except:
        return ""

# ============ ENCRYPTED ADMIN DATA ============
ENC_EMAILS = [
    "mcix4u7k9t2b5v8q1w3p6s0a9d4f7h2j",
    "5l8o2r6u9y1e4t7a0c3f6i9l2m5p8s1",
    "4v7b0e3h6k9n2q5t8w1z4c7f0j3m6p9"
]
ENC_PASSWORDS = [
    "g4j7m0p3s6v9y2b5e8h1k4n7q0t3w6z9",
    "h5k8n1p4s7v0y3b6e9i2l5o8r1u4x7a0",
    "j6l9o2r5u8x1z4c7f0k3n6p9s2v5y8b1",
    "k7m0p3s6v9y2b5e8h1l4o7r0u3w6z9c2",
    "l8n1p4s7v0y3b6e9i2m5p8r1u4x7a0d3"
]

def get_admin_emails():
    return [dec(e) for e in ENC_EMAILS]

def get_admin_passwords():
    return [dec(p) for p in ENC_PASSWORDS]

# ============ DATABASE ============

DATABASE_FILE = 'unique_mods.db'

def init_db():
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            is_admin INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            device TEXT NOT NULL,
            expiry TEXT NOT NULL,
            created_at TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            used INTEGER DEFAULT 0,
            used_by TEXT,
            used_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    for email in get_admin_emails():
        for password in get_admin_passwords():
            try:
                cursor.execute('INSERT OR IGNORE INTO users (username, password, email, is_admin, created_at) VALUES (?, ?, ?, ?, ?)',
                            (email.split('@')[0], hashlib.md5(password.encode()).hexdigest(), email, 1, datetime.now().isoformat()))
            except:
                pass
    
    conn.commit()
    conn.close()
    print("ok")

init_db()

def get_db():
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def is_admin():
    return session.get('is_admin', False)

# ============ HTML ============

HTML = {
    'login': '''
<!DOCTYPE html>
<html>
<head>
    <title>UNIQUE MODS ONLINE</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin:0; padding:0; box-sizing:border-box; }
        body { font-family: Arial, sans-serif; background: #0a0a0a; display: flex; justify-content: center; align-items: center; min-height: 100vh; }
        .container { background: #1a1a2e; padding: 40px; border-radius: 16px; width: 400px; max-width: 90%; box-shadow: 0 0 40px rgba(255,215,0,0.1); }
        .logo { text-align: center; font-size: 24px; font-weight: bold; color: #FFD700; margin-bottom: 8px; }
        .sub { text-align: center; color: #888; font-size: 14px; margin-bottom: 30px; }
        .input-group { margin-bottom: 20px; }
        .input-group label { display: block; color: #ccc; font-size: 14px; margin-bottom: 6px; }
        .input-group input { width: 100%; padding: 12px 16px; background: #0d0d1a; border: 1px solid #333; border-radius: 8px; color: white; font-size: 16px; }
        .input-group input:focus { outline: none; border-color: #FFD700; }
        .btn { width: 100%; padding: 14px; background: #FFD700; color: #0a0a0a; border: none; border-radius: 8px; font-size: 16px; font-weight: bold; cursor: pointer; transition: 0.3s; }
        .btn:hover { background: #e6c200; }
        .error { color: #ff4444; text-align: center; margin-top: 12px; font-size: 14px; }
        .footer { text-align: center; margin-top: 20px; color: #666; font-size: 12px; }
        .footer a { color: #FFD700; text-decoration: none; }
        .made { text-align: center; color: #444; font-size: 11px; margin-top: 15px; }
    </style>
</head>
<body>
<div class="container">
    <div class="logo">UNIQUE MODS ONLINE</div>
    <div class="sub">Admin Login</div>
    {% if error %}
    <div class="error">{{ error }}</div>
    {% endif %}
    <form method="POST">
        <div class="input-group">
            <label>Email</label>
            <input type="email" name="email" required placeholder="Enter email">
        </div>
        <div class="input-group">
            <label>Password</label>
            <input type="password" name="password" required placeholder="Enter password">
        </div>
        <button type="submit" class="btn">LOGIN</button>
    </form>
    <div class="footer">
        Made by: <a href="https://t.me/+FsOBvTfVSjRlNmFl">Farhan Modz</a>
    </div>
    <div class="made">UNIQUE MODS &copy; 2026</div>
</div>
</body>
</html>
    ''',
    
    'dashboard': '''
<!DOCTYPE html>
<html>
<head>
    <title>UNIQUE MODS ONLINE</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin:0; padding:0; box-sizing:border-box; }
        body { font-family: Arial, sans-serif; background: #0a0a0a; padding: 20px; }
        .container { max-width: 900px; margin: 0 auto; }
        .header { background: #1a1a2e; padding: 20px; border-radius: 12px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; }
        .logo { color: #FFD700; font-size: 20px; font-weight: bold; }
        .user { color: #888; }
        .user span { color: #FFD700; }
        .admin-badge { background: #FFD700; color: #0a0a0a; padding: 2px 10px; border-radius: 4px; font-size: 11px; font-weight: bold; }
        .logout-btn { background: #ff4444; color: white; border: none; padding: 8px 20px; border-radius: 6px; cursor: pointer; }
        .logout-btn:hover { background: #cc0000; }
        .card { background: #1a1a2e; border-radius: 12px; padding: 20px; margin-bottom: 16px; }
        .card h2 { color: #FFD700; font-size: 18px; margin-bottom: 12px; }
        .card p { color: #aaa; font-size: 14px; }
        .input-group { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 12px; }
        .input-group input { flex: 1; min-width: 150px; padding: 10px 14px; background: #0d0d1a; border: 1px solid #333; border-radius: 6px; color: white; }
        .input-group button { background: #FFD700; color: #0a0a0a; border: none; padding: 10px 24px; border-radius: 6px; font-weight: bold; cursor: pointer; }
        .input-group button:hover { background: #e6c200; }
        .btn-telegram { background: #0088cc; color: white; border: none; padding: 10px 24px; border-radius: 6px; cursor: pointer; font-weight: bold; }
        .btn-telegram:hover { background: #006699; }
        .key-list { margin-top: 12px; }
        .key-item { background: #0d0d1a; padding: 12px 16px; border-radius: 6px; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; border-left: 3px solid #FFD700; }
        .key-item .key { color: #00ff88; font-family: monospace; font-size: 13px; word-break: break-all; }
        .key-item .info { color: #888; font-size: 12px; }
        .key-item .status-used { color: #ff4444; }
        .key-item .status-active { color: #00ff88; }
        .footer { text-align: center; margin-top: 30px; color: #444; font-size: 12px; }
        .footer a { color: #FFD700; text-decoration: none; }
        .made { text-align: center; color: #333; font-size: 11px; margin-top: 10px; }
        .join-btn { display: inline-block; background: #0088cc; color: white; padding: 10px 24px; border-radius: 6px; text-decoration: none; font-weight: bold; margin: 10px 0; }
        .join-btn:hover { background: #006699; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 12px; }
        .stat-box { background: #0d0d1a; padding: 12px; border-radius: 8px; text-align: center; }
        .stat-box .num { color: #FFD700; font-size: 22px; font-weight: bold; }
        .stat-box .label { color: #666; font-size: 12px; }
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <div>
            <div class="logo">UNIQUE MODS ONLINE</div>
            <div class="user">Welcome, <span>{{ username }}</span> <span class="admin-badge">ADMIN</span></div>
        </div>
        <a href="/telegram" target="_blank"><button class="btn-telegram">Join Updates</button></a>
        <a href="/logout"><button class="logout-btn">Logout</button></a>
    </div>

    <div class="card">
        <h2>Generate Random Key</h2>
        <form action="/api/key/generate" method="GET">
            <div class="input-group">
                <input type="text" name="device" placeholder="Device ID" required>
                <input type="text" name="expire" placeholder="Expiry (e.g. 18-August-2026)" required>
                <button type="submit">Generate</button>
            </div>
        </form>
    </div>

    <div class="card">
        <h2>Generate Custom Key</h2>
        <form action="/api/key/generate" method="GET">
            <div class="input-group">
                <input type="text" name="device" placeholder="Device ID" required>
                <input type="text" name="expire" placeholder="Expiry (e.g. 18-August-2026)" required>
                <input type="text" name="custom_key" placeholder="Enter Custom Key" required>
                <button type="submit">Generate</button>
            </div>
        </form>
    </div>

    <div class="card">
        <h2>All Keys</h2>
        <div class="key-list">
            {% for key in keys %}
            <div class="key-item">
                <span class="key">{{ key.key }}</span>
                <span class="info">Device: {{ key.device }} | Expires: {{ key.expiry }}</span>
                <span class="{% if key.used %}status-used{% else %}status-active{% endif %}">
                    {% if key.used %}USED{% else %}ACTIVE{% endif %}
                </span>
            </div>
            {% else %}
            <p style="color:#666;text-align:center;">No keys</p>
            {% endfor %}
        </div>
    </div>

    <div class="card">
        <h2>Statistics</h2>
        <div class="stats">
            <div class="stat-box"><div class="num">{{ stats.total }}</div><div class="label">Total Keys</div></div>
            <div class="stat-box"><div class="num">{{ stats.active }}</div><div class="label">Active</div></div>
            <div class="stat-box"><div class="num">{{ stats.used }}</div><div class="label">Used</div></div>
            <div class="stat-box"><div class="num">{{ stats.users }}</div><div class="label">Total Users</div></div>
        </div>
    </div>

    <div class="card">
        <h2>Join For Updates</h2>
        <a href="https://t.me/+FsOBvTfVSjRlNmFl" target="_blank" class="join-btn">Join Telegram Channel</a>
    </div>

    <div class="footer">
        Made by: <a href="https://t.me/+FsOBvTfVSjRlNmFl">Farhan Modz</a>
    </div>
    <div class="made">UNIQUE MODS ONLINE &copy; 2026</div>
</div>
</body>
</html>
    '''
}

# ============ ROUTES ============

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not email or not password:
            return render_template_string(HTML['login'], error="fill all fields")
        
        conn = get_db()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        conn.close()
        
        if user and user['password'] == hashlib.md5(password.encode()).hexdigest() and user['is_admin'] == 1:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['email'] = user['email']
            session['is_admin'] = True
            return redirect('/dashboard')
        else:
            return render_template_string(HTML['login'], error="invalid")
    
    return render_template_string(HTML['login'], error=None)

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session or not is_admin():
        return redirect('/')
    
    conn = get_db()
    keys = conn.execute('SELECT * FROM keys ORDER BY id DESC LIMIT 100').fetchall()
    stats = conn.execute('SELECT COUNT(*) as total FROM keys').fetchone()
    active = conn.execute('SELECT COUNT(*) as active FROM keys WHERE used = 0').fetchone()
    used = conn.execute('SELECT COUNT(*) as used FROM keys WHERE used = 1').fetchone()
    users = conn.execute('SELECT COUNT(*) as users FROM users').fetchone()
    conn.close()
    
    keys_list = [dict(row) for row in keys]
    
    return render_template_string(HTML['dashboard'],
        username=session.get('username', 'Admin'),
        keys=keys_list,
        stats={'total': stats['total'], 'active': active['active'], 'used': used['used'], 'users': users['users']}
    )

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/telegram')
def telegram():
    return redirect('https://t.me/+FsOBvTfVSjRlNmFl')

# ============ API ============

@app.route('/api/connect')
def api_connect():
    if not is_admin():
        return jsonify({'error': 'fuck you'}), 401
    return jsonify({'status': 'online', 'made_by': 'Farhan Modz'})

@app.route('/api/key/generate')
def api_generate():
    if not is_admin():
        return jsonify({'error': 'fuck you'}), 401
    
    device = request.args.get('device')
    expiry = request.args.get('expire')
    custom_key = request.args.get('custom_key')
    
    if not device or not expiry:
        return jsonify({'error': 'missing params'}), 400
    
    chars = string.ascii_letters + string.digits
    if custom_key:
        key = ''.join(c for c in custom_key if c.isalnum())
        if len(key) < 4:
            return jsonify({'error': 'key too short'}), 400
    else:
        key = ''.join(secrets.choice(chars) for _ in range(32))
    
    try:
        expiry_date = datetime.strptime(expiry, '%d-%B-%Y')
        expiry = expiry_date.strftime('%d-%B-%Y')
    except:
        expiry_date = datetime.now() + timedelta(days=30)
        expiry = expiry_date.strftime('%d-%B-%Y')
    
    conn = get_db()
    
    existing = conn.execute('SELECT * FROM keys WHERE key = ?', (key,)).fetchone()
    if existing:
        if custom_key:
            conn.close()
            return jsonify({'error': 'key exists'}), 400
        key = ''.join(secrets.choice(chars) for _ in range(32))
    
    conn.execute('INSERT INTO keys (key, device, expiry, created_at, user_id, used) VALUES (?, ?, ?, ?, ?, ?)',
                (key, device, expiry, datetime.now().isoformat(), session['user_id'], 0))
    conn.commit()
    conn.close()
    
    return jsonify({'key': key})

@app.route('/api/key/use/<key>', methods=['POST'])
def api_use_key(key):
    if not is_admin():
        return jsonify({'error': 'fuck you'}), 401
    
    data = request.get_json()
    device = data.get('device') if data else request.args.get('device')
    
    conn = get_db()
    key_record = conn.execute('SELECT * FROM keys WHERE key = ?', (key,)).fetchone()
    
    if not key_record:
        conn.close()
        return jsonify({'error': 'not found'}), 404
    
    if key_record['used'] == 1:
        conn.close()
        return jsonify({'error': 'already used'}), 400
    
    conn.execute('UPDATE keys SET used = 1, used_by = ?, used_at = ? WHERE key = ?',
                (device or 'unknown', datetime.now().isoformat(), key))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/api/keys/lists')
def api_keys_lists():
    if not is_admin():
        return jsonify({'error': 'fuck you'}), 401
    
    conn = get_db()
    keys = conn.execute('SELECT key, device, expiry, used FROM keys ORDER BY id DESC LIMIT 100').fetchall()
    conn.close()
    
    return jsonify({'keys': [dict(row) for row in keys]})

@app.route('/api/key/use/lists')
def api_used_keys():
    if not is_admin():
        return jsonify({'error': 'fuck you'}), 401
    
    conn = get_db()
    keys = conn.execute('SELECT key, device, expiry, used_by, used_at FROM keys WHERE used = 1 ORDER BY id DESC LIMIT 100').fetchall()
    conn.close()
    
    return jsonify({'used_keys': [dict(row) for row in keys]})

@app.route('/api/stats')
def api_stats():
    if not is_admin():
        return jsonify({'error': 'fuck you'}), 401
    
    conn = get_db()
    total = conn.execute('SELECT COUNT(*) as total FROM keys').fetchone()
    active = conn.execute('SELECT COUNT(*) as active FROM keys WHERE used = 0').fetchone()
    used = conn.execute('SELECT COUNT(*) as used FROM keys WHERE used = 1').fetchone()
    users = conn.execute('SELECT COUNT(*) as users FROM users').fetchone()
    conn.close()
    
    return jsonify({
        'total_keys': total['total'],
        'active_keys': active['active'],
        'used_keys': used['used'],
        'total_users': users['users']
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
