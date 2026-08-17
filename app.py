from flask import Flask, request, jsonify, render_template_string, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime, timedelta
import secrets
import string
import os
import hashlib
import json
import base64

app = Flask(__name__)
app.secret_key = os.urandom(24)
CORS(app)

# ============ DATABASE ============
import sqlite3
import os

DATABASE_FILE = 'users.db'

def init_db():
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    ''')
    
    # Keys table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            device TEXT NOT NULL,
            expiry TEXT NOT NULL,
            created_at TEXT NOT NULL,
            used INTEGER DEFAULT 0,
            used_by TEXT,
            used_at TEXT
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Database initialized!")

init_db()

def get_db():
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    return conn

# ============ HTML TEMPLATES ============

HTML = {
    'login': '''
<!DOCTYPE html>
<html>
<head>
    <title>UNIQUE MODS ONLINE - Login</title>
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
        .btn-secondary { background: #1a1a2e; color: #FFD700; border: 1px solid #FFD700; margin-top: 10px; }
        .btn-secondary:hover { background: #2a2a4e; }
        .error { color: #ff4444; text-align: center; margin-top: 12px; font-size: 14px; }
        .footer { text-align: center; margin-top: 20px; color: #666; font-size: 12px; }
        .footer a { color: #FFD700; text-decoration: none; }
        .made { text-align: center; color: #444; font-size: 11px; margin-top: 15px; }
    </style>
</head>
<body>
<div class="container">
    <div class="logo">UNIQUE MODS ONLINE</div>
    <div class="sub">Key Generator System</div>
    {% if error %}
    <div class="error">{{ error }}</div>
    {% endif %}
    <form method="POST">
        <div class="input-group">
            <label>Username</label>
            <input type="text" name="username" required placeholder="Enter username">
        </div>
        <div class="input-group">
            <label>Password</label>
            <input type="password" name="password" required placeholder="Enter password">
        </div>
        <button type="submit" class="btn">LOGIN</button>
    </form>
    <a href="/signup"><button class="btn btn-secondary">SIGN UP</button></a>
    <div class="footer">
        Made by: <a href="https://t.me/+FsOBvTfVSjRlNmFl">Farhan Modz</a>
    </div>
    <div class="made">UNIQUE MODS &copy; 2026</div>
</div>
</body>
</html>
    ''',
    
    'signup': '''
<!DOCTYPE html>
<html>
<head>
    <title>UNIQUE MODS ONLINE - Sign Up</title>
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
        .btn-secondary { background: #1a1a2e; color: #FFD700; border: 1px solid #FFD700; margin-top: 10px; }
        .btn-secondary:hover { background: #2a2a4e; }
        .error { color: #ff4444; text-align: center; margin-top: 12px; font-size: 14px; }
        .footer { text-align: center; margin-top: 20px; color: #666; font-size: 12px; }
        .footer a { color: #FFD700; text-decoration: none; }
    </style>
</head>
<body>
<div class="container">
    <div class="logo">UNIQUE MODS ONLINE</div>
    <div class="sub">Create Your Account</div>
    {% if error %}
    <div class="error">{{ error }}</div>
    {% endif %}
    <form method="POST">
        <div class="input-group">
            <label>Username</label>
            <input type="text" name="username" required placeholder="Choose username">
        </div>
        <div class="input-group">
            <label>Password</label>
            <input type="password" name="password" required placeholder="Choose password">
        </div>
        <button type="submit" class="btn">SIGN UP</button>
    </form>
    <a href="/"><button class="btn btn-secondary">LOGIN</button></a>
    <div class="footer">
        Made by: <a href="https://t.me/+FsOBvTfVSjRlNmFl">Farhan Modz</a>
    </div>
</div>
</body>
</html>
    ''',
    
    'dashboard': '''
<!DOCTYPE html>
<html>
<head>
    <title>UNIQUE MODS ONLINE - Dashboard</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin:0; padding:0; box-sizing:border-box; }
        body { font-family: Arial, sans-serif; background: #0a0a0a; padding: 20px; }
        .container { max-width: 900px; margin: 0 auto; }
        .header { background: #1a1a2e; padding: 20px; border-radius: 12px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; }
        .logo { color: #FFD700; font-size: 20px; font-weight: bold; }
        .user { color: #888; }
        .user span { color: #FFD700; }
        .logout-btn { background: #ff4444; color: white; border: none; padding: 8px 20px; border-radius: 6px; cursor: pointer; }
        .logout-btn:hover { background: #cc0000; }
        .card { background: #1a1a2e; border-radius: 12px; padding: 20px; margin-bottom: 16px; }
        .card h2 { color: #FFD700; font-size: 18px; margin-bottom: 12px; }
        .card p { color: #aaa; font-size: 14px; }
        .input-group { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 12px; }
        .input-group input, .input-group select { flex: 1; min-width: 150px; padding: 10px 14px; background: #0d0d1a; border: 1px solid #333; border-radius: 6px; color: white; }
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
        .shortener-box { background: #0d0d1a; padding: 16px; border-radius: 8px; margin-top: 12px; }
        .shortener-box input { width: 70%; padding: 10px 14px; background: #1a1a2e; border: 1px solid #333; border-radius: 6px; color: white; }
        .shortener-box button { padding: 10px 20px; background: #FFD700; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; }
        .shortener-result { margin-top: 10px; color: #00ff88; word-break: break-all; }
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
            <div class="user">Welcome, <span>{{ username }}</span></div>
        </div>
        <a href="/telegram" target="_blank"><button class="btn-telegram">Join Updates</button></a>
        <a href="/logout"><button class="logout-btn">Logout</button></a>
    </div>

    <div class="card">
        <h2>Generate Key</h2>
        <form action="/api/key/generate" method="GET">
            <div class="input-group">
                <input type="text" name="device" placeholder="Device ID" required>
                <input type="text" name="expire" placeholder="Expiry (e.g. 18-August-2026)" required>
                <button type="submit">Generate</button>
            </div>
        </form>
    </div>

    <div class="card">
        <h2>Generate Shortener</h2>
        <div class="shortener-box">
            <p style="color:#888;font-size:13px;margin-bottom:10px;">Shorten any URL</p>
            <form action="/api/key/generate" method="GET" id="shortenerForm">
                <input type="text" name="url" placeholder="Enter URL to shorten" id="shortenerUrl" style="width:100%;margin-bottom:10px;">
                <div class="input-group">
                    <input type="text" name="device" placeholder="Device ID" required style="flex:1;">
                    <input type="text" name="expire" placeholder="Expiry (e.g. 18-August-2026)" required style="flex:1;">
                    <button type="submit">Generate</button>
                </div>
            </form>
            <div id="shortResult" class="shortener-result"></div>
        </div>
    </div>

    <div class="card">
        <h2>Your Keys</h2>
        <div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:12px;">
            <a href="/api/keys/lists"><button style="background:#333;color:white;border:none;padding:8px 16px;border-radius:6px;cursor:pointer;">All Keys</button></a>
            <a href="/api/key/use/lists"><button style="background:#333;color:white;border:none;padding:8px 16px;border-radius:6px;cursor:pointer;">Used Keys</button></a>
        </div>
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
            <p style="color:#666;text-align:center;">No keys generated yet</p>
            {% endfor %}
        </div>
    </div>

    <div class="card">
        <h2>Statistics</h2>
        <div class="stats">
            <div class="stat-box"><div class="num">{{ stats.total }}</div><div class="label">Total Keys</div></div>
            <div class="stat-box"><div class="num">{{ stats.active }}</div><div class="label">Active</div></div>
            <div class="stat-box"><div class="num">{{ stats.used }}</div><div class="label">Used</div></div>
        </div>
    </div>

    <div class="card">
        <h2>Join For Updates</h2>
        <p style="color:#888;margin-bottom:12px;">Stay updated with latest features and news</p>
        <a href="https://t.me/+FsOBvTfVSjRlNmFl" target="_blank" class="join-btn">Join Telegram Channel</a>
    </div>

    <div class="footer">
        Made by: <a href="https://t.me/+FsOBvTfVSjRlNmFl">Farhan Modz</a>
    </div>
    <div class="made">UNIQUE MODS ONLINE &copy; 2026 | All Rights Reserved</div>
</div>
</body>
</html>
    '''
}

# ============ ROUTES ============

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            return render_template_string(HTML['login'], error="Please fill all fields")
        
        conn = get_db()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        
        if user and user['password'] == hashlib.md5(password.encode()).hexdigest():
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect('/dashboard')
        else:
            return render_template_string(HTML['login'], error="Invalid credentials")
    
    return render_template_string(HTML['login'], error=None)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            return render_template_string(HTML['signup'], error="Please fill all fields")
        
        if len(username) < 3:
            return render_template_string(HTML['signup'], error="Username too short")
        
        if len(password) < 4:
            return render_template_string(HTML['signup'], error="Password too short")
        
        conn = get_db()
        try:
            conn.execute('INSERT INTO users (username, password, created_at) VALUES (?, ?, ?)',
                        (username, hashlib.md5(password.encode()).hexdigest(), datetime.now().isoformat()))
            conn.commit()
            conn.close()
            return redirect('/')
        except sqlite3.IntegrityError:
            conn.close()
            return render_template_string(HTML['signup'], error="Username already taken")
    
    return render_template_string(HTML['signup'], error=None)

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/')
    
    conn = get_db()
    keys = conn.execute('SELECT * FROM keys ORDER BY id DESC LIMIT 50').fetchall()
    stats = conn.execute('SELECT COUNT(*) as total FROM keys').fetchone()
    active = conn.execute('SELECT COUNT(*) as active FROM keys WHERE used = 0').fetchone()
    used = conn.execute('SELECT COUNT(*) as used FROM keys WHERE used = 1').fetchone()
    conn.close()
    
    keys_list = [dict(row) for row in keys]
    
    return render_template_string(HTML['dashboard'],
        username=session.get('username', 'User'),
        keys=keys_list,
        stats={'total': stats['total'], 'active': active['active'], 'used': used['used']}
    )

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/telegram')
def telegram():
    return redirect('https://t.me/+FsOBvTfVSjRlNmFl')

# ============ API ROUTES ============

@app.route('/api/connect')
def api_connect():
    return jsonify({
        'status': 'online',
        'service': 'UNIQUE MODS ONLINE',
        'made_by': 'Farhan Modz',
        'telegram': 'https://t.me/+FsOBvTfVSjRlNmFl',
        'version': '1.0.0'
    })

@app.route('/api/key/generate')
def api_generate():
    device = request.args.get('device')
    expiry = request.args.get('expire')
    url = request.args.get('url')
    
    if not device or not expiry:
        return jsonify({'error': 'Missing device or expire parameter'}), 400
    
    # Generate random key
    chars = string.ascii_letters + string.digits
    key = ''.join(secrets.choice(chars) for _ in range(32))
    
    # Parse expiry
    try:
        expiry_date = datetime.strptime(expiry, '%d-%B-%Y')
    except ValueError:
        expiry_date = datetime.now() + timedelta(days=30)
        expiry = expiry_date.strftime('%d-%B-%Y')
    
    conn = get_db()
    
    # Check if key exists
    existing = conn.execute('SELECT * FROM keys WHERE key = ?', (key,)).fetchone()
    if existing:
        key = ''.join(secrets.choice(chars) for _ in range(32))
    
    conn.execute('INSERT INTO keys (key, device, expiry, created_at, used) VALUES (?, ?, ?, ?, ?)',
                (key, device, expiry, datetime.now().isoformat(), 0))
    conn.commit()
    conn.close()
    
    # If URL provided, create shortener
    short_url = None
    if url:
        short_url = f"/s/{key[:8]}"
    
    return jsonify({
        'success': True,
        'key': key,
        'device': device,
        'expiry': expiry,
        'created_at': datetime.now().isoformat(),
        'short_url': short_url,
        'message': 'Key generated successfully!',
        'made_by': 'Farhan Modz',
        'telegram': 'https://t.me/+FsOBvTfVSjRlNmFl'
    })

@app.route('/api/key/use/<key>', methods=['POST'])
def api_use_key(key):
    data = request.get_json()
    device = data.get('device') if data else request.args.get('device')
    
    conn = get_db()
    key_record = conn.execute('SELECT * FROM keys WHERE key = ?', (key,)).fetchone()
    
    if not key_record:
        conn.close()
        return jsonify({'error': 'Key not found'}), 404
    
    if key_record['used'] == 1:
        conn.close()
        return jsonify({'error': 'Key already used'}), 400
    
    conn.execute('UPDATE keys SET used = 1, used_by = ?, used_at = ? WHERE key = ?',
                (device or 'unknown', datetime.now().isoformat(), key))
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True,
        'key': key,
        'message': 'Key used successfully!',
        'used_by': device or 'unknown',
        'used_at': datetime.now().isoformat()
    })

@app.route('/api/keys/lists')
def api_keys_lists():
    conn = get_db()
    keys = conn.execute('SELECT * FROM keys ORDER BY id DESC LIMIT 100').fetchall()
    conn.close()
    
    return jsonify({
        'success': True,
        'total': len(keys),
        'keys': [dict(row) for row in keys],
        'made_by': 'Farhan Modz'
    })

@app.route('/api/key/use/lists')
def api_used_keys():
    conn = get_db()
    keys = conn.execute('SELECT * FROM keys WHERE used = 1 ORDER BY id DESC LIMIT 100').fetchall()
    conn.close()
    
    return jsonify({
        'success': True,
        'total': len(keys),
        'keys': [dict(row) for row in keys],
        'made_by': 'Farhan Modz'
    })

@app.route('/api/stats')
def api_stats():
    conn = get_db()
    total = conn.execute('SELECT COUNT(*) as total FROM keys').fetchone()
    active = conn.execute('SELECT COUNT(*) as active FROM keys WHERE used = 0').fetchone()
    used = conn.execute('SELECT COUNT(*) as used FROM keys WHERE used = 1').fetchone()
    users = conn.execute('SELECT COUNT(*) as users FROM users').fetchone()
    conn.close()
    
    return jsonify({
        'success': True,
        'total_keys': total['total'],
        'active_keys': active['active'],
        'used_keys': used['used'],
        'total_users': users['users'],
        'made_by': 'Farhan Modz'
    })

@app.route('/s/<short_code>')
def redirect_short(short_code):
    conn = get_db()
    key_record = conn.execute('SELECT * FROM keys WHERE key LIKE ?', (short_code + '%',)).fetchone()
    conn.close()
    
    if key_record:
        return redirect(f'/dashboard?key={key_record["key"]}')
    return redirect('/')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)