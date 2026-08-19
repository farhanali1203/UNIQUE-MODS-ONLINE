from flask import Flask, request, jsonify, render_template_string, redirect, url_for, session
from flask_cors import CORS
from datetime import datetime, timedelta
import secrets
import string
import os
import hashlib
import sqlite3
import base64

app = Flask(__name__)
app.secret_key = os.urandom(24)
CORS(app)

# ============ ENCRYPTION ============

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

DATABASE_FILE = os.path.join('/tmp', 'unique_mods.db') if os.path.exists('/tmp') else 'unique_mods.db'

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
                cursor.execute('''
                    INSERT OR IGNORE INTO users (username, password, email, is_admin, created_at) 
                    VALUES (?, ?, ?, ?, ?)
                ''', (email.split('@')[0], hashlib.md5(password.encode()).hexdigest(), email, 1, datetime.now().isoformat()))
            except:
                pass
    
    conn.commit()
    conn.close()

def get_db():
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    return conn

init_db()

# ============ HELPER FUNCTIONS ============

def is_admin():
    return session.get('is_admin', False)

def get_user_by_email(email):
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
    conn.close()
    return user

def get_user_by_username(username):
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    conn.close()
    return user

def get_user_by_id(user_id):
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    return user

def get_all_keys():
    conn = get_db()
    keys = conn.execute('SELECT * FROM keys ORDER BY id DESC LIMIT 100').fetchall()
    conn.close()
    return [dict(row) for row in keys]

def get_key_by_key(key):
    conn = get_db()
    key_record = conn.execute('SELECT * FROM keys WHERE key = ?', (key,)).fetchone()
    conn.close()
    return key_record

def get_stats():
    conn = get_db()
    total = conn.execute('SELECT COUNT(*) as total FROM keys').fetchone()
    active = conn.execute('SELECT COUNT(*) as active FROM keys WHERE used = 0').fetchone()
    used = conn.execute('SELECT COUNT(*) as used FROM keys WHERE used = 1').fetchone()
    users = conn.execute('SELECT COUNT(*) as users FROM users').fetchone()
    conn.close()
    return {
        'total': total['total'] if total else 0,
        'active': active['active'] if active else 0,
        'used': used['used'] if used else 0,
        'users': users['users'] if users else 0
    }

def insert_user(username, email, password):
    conn = get_db()
    cursor = conn.execute('''
        INSERT INTO users (username, email, password, is_admin, created_at)
        VALUES (?, ?, ?, ?, ?)
    ''', (username, email, hashlib.md5(password.encode()).hexdigest(), 0, datetime.now().isoformat()))
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return user_id

def insert_key(key, device, expiry, user_id):
    conn = get_db()
    conn.execute('''
        INSERT INTO keys (key, device, expiry, created_at, user_id, used)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (key, device, expiry, datetime.now().isoformat(), user_id, 0))
    conn.commit()
    conn.close()

def update_key_used(key, used_by):
    conn = get_db()
    conn.execute('''
        UPDATE keys SET used = 1, used_by = ?, used_at = ? WHERE key = ?
    ''', (used_by, datetime.now().isoformat(), key))
    conn.commit()
    conn.close()

def delete_user_by_id(user_id):
    conn = get_db()
    conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()

def get_all_users():
    conn = get_db()
    users = conn.execute('SELECT id, username, email, is_admin, created_at FROM users').fetchall()
    conn.close()
    return [dict(row) for row in users]

# ============ HTML ============

LOGIN_PAGE = '''
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
        .error { color: #ff4444; text-align: center; margin-top: 12px; font-size: 14px; }
        .footer { text-align: center; margin-top: 20px; color: #666; font-size: 12px; }
        .footer a { color: #FFD700; text-decoration: none; }
        .made { text-align: center; color: #444; font-size: 11px; margin-top: 15px; }
        .login-link { text-align: center; margin-top: 15px; color: #888; }
        .login-link a { color: #FFD700; text-decoration: none; }
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
    <div class="login-link">
        Don't have an account? <a href="/signup">Sign Up</a>
    </div>
    <div class="footer">
        Made by: <a href="https://t.me/+FsOBvTfVSjRlNmFl">Farhan Modz</a>
    </div>
    <div class="made">UNIQUE MODS &copy; 2026</div>
</div>
</body>
</html>
'''

SIGNUP_PAGE = '''
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
        .error { color: #ff4444; text-align: center; margin-top: 12px; font-size: 14px; }
        .success { color: #00ff88; text-align: center; margin-top: 12px; font-size: 14px; }
        .footer { text-align: center; margin-top: 20px; color: #666; font-size: 12px; }
        .footer a { color: #FFD700; text-decoration: none; }
        .made { text-align: center; color: #444; font-size: 11px; margin-top: 15px; }
        .login-link { text-align: center; margin-top: 15px; color: #888; }
        .login-link a { color: #FFD700; text-decoration: none; }
    </style>
</head>
<body>
<div class="container">
    <div class="logo">UNIQUE MODS ONLINE</div>
    <div class="sub">Create Account</div>
    {% if error %}
    <div class="error">{{ error }}</div>
    {% endif %}
    {% if success %}
    <div class="success">{{ success|safe }}</div>
    {% endif %}
    <form method="POST">
        <div class="input-group">
            <label>Username</label>
            <input type="text" name="username" required placeholder="Choose username" minlength="3">
        </div>
        <div class="input-group">
            <label>Email</label>
            <input type="email" name="email" required placeholder="Enter email">
        </div>
        <div class="input-group">
            <label>Password</label>
            <input type="password" name="password" required placeholder="Min 6 characters" minlength="6">
        </div>
        <div class="input-group">
            <label>Confirm Password</label>
            <input type="password" name="confirm_password" required placeholder="Confirm password">
        </div>
        <button type="submit" class="btn">SIGN UP</button>
    </form>
    <div class="login-link">
        Already have an account? <a href="/">Login</a>
    </div>
    <div class="footer">
        Made by: <a href="https://t.me/+FsOBvTfVSjRlNmFl">Farhan Modz</a>
    </div>
    <div class="made">UNIQUE MODS &copy; 2026</div>
</div>
</body>
</html>
'''

DASHBOARD_PAGE = '''
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
        .btn-users { background: #6c5ce7; color: white; border: none; padding: 8px 20px; border-radius: 6px; cursor: pointer; }
        .btn-users:hover { background: #5a4bd1; }
        .header-buttons { display: flex; gap: 10px; flex-wrap: wrap; }
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <div>
            <div class="logo">UNIQUE MODS ONLINE</div>
            <div class="user">Welcome, <span>{{ username }}</span> <span class="admin-badge">ADMIN</span></div>
        </div>
        <div class="header-buttons">
            <a href="/users"><button class="btn-users">Users</button></a>
            <a href="/telegram" target="_blank"><button class="btn-telegram">Join Updates</button></a>
            <a href="/logout"><button class="logout-btn">Logout</button></a>
        </div>
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

USERS_PAGE = '''
<!DOCTYPE html>
<html>
<head>
    <title>UNIQUE MODS ONLINE - Users</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin:0; padding:0; box-sizing:border-box; }
        body { font-family: Arial, sans-serif; background: #0a0a0a; padding: 20px; }
        .container { max-width: 900px; margin: 0 auto; }
        .header { background: #1a1a2e; padding: 20px; border-radius: 12px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; }
        .logo { color: #FFD700; font-size: 20px; font-weight: bold; }
        .back-btn { background: #FFD700; color: #0a0a0a; border: none; padding: 8px 20px; border-radius: 6px; cursor: pointer; font-weight: bold; }
        .back-btn:hover { background: #e6c200; }
        .card { background: #1a1a2e; border-radius: 12px; padding: 20px; margin-bottom: 16px; }
        .card h2 { color: #FFD700; font-size: 18px; margin-bottom: 12px; }
        .user-item { background: #0d0d1a; padding: 12px 16px; border-radius: 6px; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; border-left: 3px solid #6c5ce7; }
        .user-item .username { color: #00ff88; font-weight: bold; }
        .user-item .email { color: #888; font-size: 14px; }
        .user-item .admin-badge { background: #FFD700; color: #0a0a0a; padding: 2px 10px; border-radius: 4px; font-size: 11px; font-weight: bold; }
        .delete-btn { background: #ff4444; color: white; border: none; padding: 4px 12px; border-radius: 4px; cursor: pointer; font-size: 12px; }
        .delete-btn:hover { background: #cc0000; }
        .footer { text-align: center; margin-top: 30px; color: #444; font-size: 12px; }
        .footer a { color: #FFD700; text-decoration: none; }
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <div>
            <div class="logo">UNIQUE MODS ONLINE</div>
            <div style="color: #888; font-size: 14px;">User Management</div>
        </div>
        <a href="/dashboard"><button class="back-btn">Back to Dashboard</button></a>
    </div>

    <div class="card">
        <h2>All Users ({{ users|length }})</h2>
        <div style="margin-top: 12px;">
            {% for user in users %}
            <div class="user-item">
                <div>
                    <span class="username">{{ user.username }}</span>
                    <span class="email">{{ user.email }}</span>
                    {% if user.is_admin == 1 %}
                    <span class="admin-badge">ADMIN</span>
                    {% endif %}
                </div>
                <div style="display: flex; gap: 8px; align-items: center;">
                    <span style="color: #666; font-size: 12px;">Joined: {{ user.created_at[:10] }}</span>
                    {% if user.is_admin != 1 %}
                    <button class="delete-btn" onclick="deleteUser('{{ user.id }}', '{{ user.username }}')">Delete</button>
                    {% endif %}
                </div>
            </div>
            {% else %}
            <p style="color:#666;text-align:center;">No users</p>
            {% endfor %}
        </div>
    </div>

    <div class="footer">
        Made by: <a href="https://t.me/+FsOBvTfVSjRlNmFl">Farhan Modz</a>
    </div>
</div>

<script>
function deleteUser(userId, username) {
    if(confirm('Delete user "' + username + '"?')) {
        fetch('/api/user/delete/' + userId, {
            method: 'DELETE'
        })
        .then(res => res.json())
        .then(data => {
            if(data.success) {
                location.reload();
            } else {
                alert('Error: ' + data.error);
            }
        })
        .catch(err => alert('Error: ' + err));
    }
}
</script>
</body>
</html>
'''

# ============ ROUTES ============

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not email or not password:
            return render_template_string(LOGIN_PAGE, error="Please fill all fields")
        
        user = get_user_by_email(email)
        
        if user and user['password'] == hashlib.md5(password.encode()).hexdigest() and user['is_admin'] == 1:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['email'] = user['email']
            session['is_admin'] = True
            return redirect('/dashboard')
        else:
            return render_template_string(LOGIN_PAGE, error="Invalid credentials or not admin")
    
    return render_template_string(LOGIN_PAGE, error=None)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if not username or not email or not password:
            return render_template_string(SIGNUP_PAGE, error="All fields are required")
        
        if len(username) < 3:
            return render_template_string(SIGNUP_PAGE, error="Username must be at least 3 characters")
        
        if '@' not in email or '.' not in email:
            return render_template_string(SIGNUP_PAGE, error="Invalid email address")
        
        if len(password) < 6:
            return render_template_string(SIGNUP_PAGE, error="Password must be at least 6 characters")
        
        if password != confirm_password:
            return render_template_string(SIGNUP_PAGE, error="Passwords do not match")
        
        existing_user = get_user_by_email(email)
        if existing_user:
            return render_template_string(SIGNUP_PAGE, error="Email already registered")
        
        existing_username = get_user_by_username(username)
        if existing_username:
            return render_template_string(SIGNUP_PAGE, error="Username already taken")
        
        try:
            insert_user(username, email, password)
            return render_template_string(SIGNUP_PAGE, success='Account created successfully! <a href="/" style="color:#FFD700;">Login here</a>')
        except Exception as e:
            return render_template_string(SIGNUP_PAGE, error="Error: " + str(e))
    
    return render_template_string(SIGNUP_PAGE, error=None, success=None)

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session or not is_admin():
        return redirect('/')
    
    keys = get_all_keys()
    stats = get_stats()
    
    return render_template_string(DASHBOARD_PAGE,
        username=session.get('username', 'Admin'),
        keys=keys,
        stats=stats
    )

@app.route('/users')
def list_users():
    if 'user_id' not in session or not is_admin():
        return redirect('/')
    
    users = get_all_users()
    return render_template_string(USERS_PAGE, users=users)

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
        return jsonify({'error': 'Unauthorized'}), 401
    return jsonify({'status': 'online', 'made_by': 'Farhan Modz'})

@app.route('/api/key/generate')
def api_generate():
    if not is_admin():
        return jsonify({'error': 'Unauthorized'}), 401
    
    device = request.args.get('device')
    expiry = request.args.get('expire')
    custom_key = request.args.get('custom_key')
    
    if not device or not expiry:
        return jsonify({'error': 'Missing parameters'}), 400
    
    chars = string.ascii_letters + string.digits
    if custom_key:
        key = ''.join(c for c in custom_key if c.isalnum())
        if len(key) < 4:
            return jsonify({'error': 'Key too short (min 4 chars)'}), 400
    else:
        key = ''.join(secrets.choice(chars) for _ in range(32))
    
    try:
        expiry_date = datetime.strptime(expiry, '%d-%B-%Y')
        expiry = expiry_date.strftime('%d-%B-%Y')
    except:
        expiry_date = datetime.now() + timedelta(days=30)
        expiry = expiry_date.strftime('%d-%B-%Y')
    
    existing = get_key_by_key(key)
    if existing:
        if custom_key:
            return jsonify({'error': 'Key already exists'}), 400
        key = ''.join(secrets.choice(chars) for _ in range(32))
    
    try:
        insert_key(key, device, expiry, session['user_id'])
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    return jsonify({'key': key})

@app.route('/api/key/use/<key>', methods=['POST'])
def api_use_key(key):
    if not is_admin():
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    device = data.get('device') if data else request.args.get('device')
    
    key_record = get_key_by_key(key)
    
    if not key_record:
        return jsonify({'error': 'Key not found'}), 404
    
    if key_record['used'] == 1:
        return jsonify({'error': 'Key already used'}), 400
    
    try:
        update_key_used(key, device or 'unknown')
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    return jsonify({'success': True})

@app.route('/api/keys/lists')
def api_keys_lists():
    if not is_admin():
        return jsonify({'error': 'Unauthorized'}), 401
    
    keys = get_all_keys()
    return jsonify({'keys': keys})

@app.route('/api/key/use/lists')
def api_used_keys():
    if not is_admin():
        return jsonify({'error': 'Unauthorized'}), 401
    
    conn = get_db()
    keys = conn.execute('SELECT key, device, expiry, used_by, used_at FROM keys WHERE used = 1 ORDER BY id DESC LIMIT 100').fetchall()
    conn.close()
    
    return jsonify({'used_keys': [dict(row) for row in keys]})

@app.route('/api/stats')
def api_stats():
    if not is_admin():
        return jsonify({'error': 'Unauthorized'}), 401
    
    stats = get_stats()
    return jsonify({
        'total_keys': stats['total'],
        'active_keys': stats['active'],
        'used_keys': stats['used'],
        'total_users': stats['users']
    })

@app.route('/api/user/delete/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    if not is_admin():
        return jsonify({'error': 'Unauthorized'}), 401
    
    if user_id == session.get('user_id'):
        return jsonify({'error': 'Cannot delete yourself'}), 400
    
    try:
        delete_user_by_id(user_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/user/all')
def api_all_users():
    if not is_admin():
        return jsonify({'error': 'Unauthorized'}), 401
    
    users = get_all_users()
    return jsonify({'users': users})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)