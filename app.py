from flask import Flask, request, jsonify, render_template_string, redirect, url_for, session
from flask_cors import CORS
from datetime import datetime, timedelta
import secrets
import string
import os
import hashlib
import sqlite3
import base64
import time

app = Flask(__name__)
app.secret_key = os.urandom(24)
CORS(app)

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
            owner_username TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS key_usage_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT NOT NULL,
            used_by_user_id INTEGER NOT NULL,
            used_by_username TEXT NOT NULL,
            used_at TEXT NOT NULL,
            FOREIGN KEY (used_by_user_id) REFERENCES users(id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("Database initialized!")

def get_db():
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    return conn

init_db()

# ============ HELPER FUNCTIONS ============

def is_logged_in():
    return session.get('user_id') is not None

def get_user_by_id(user_id):
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    return user

def get_user_by_username(username):
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    conn.close()
    return user

def get_all_keys():
    conn = get_db()
    keys = conn.execute('SELECT * FROM keys ORDER BY id DESC LIMIT 100').fetchall()
    conn.close()
    return [dict(row) for row in keys]

def get_keys_by_user(user_id):
    conn = get_db()
    keys = conn.execute('SELECT * FROM keys WHERE user_id = ? ORDER BY id DESC', (user_id,)).fetchall()
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
    ''', (username, email, hashlib.md5(password.encode()).hexdigest(), 1, datetime.now().isoformat()))
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return user_id

def insert_key(key, device, expiry, user_id, username):
    conn = get_db()
    conn.execute('''
        INSERT INTO keys (key, device, expiry, created_at, user_id, used, owner_username)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (key, device, expiry, datetime.now().isoformat(), user_id, 0, username))
    conn.commit()
    conn.close()

def update_key_used(key, used_by_user_id, used_by_username):
    conn = get_db()
    conn.execute('''
        UPDATE keys SET used = 1, used_by = ?, used_at = ? WHERE key = ?
    ''', (used_by_username, datetime.now().isoformat(), key))
    conn.execute('''
        INSERT INTO key_usage_history (key, used_by_user_id, used_by_username, used_at)
        VALUES (?, ?, ?, ?)
    ''', (key, used_by_user_id, used_by_username, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def delete_user_by_id(user_id):
    conn = get_db()
    conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()

def get_all_users():
    conn = get_db()
    users = conn.execute('SELECT id, username, email, created_at FROM users').fetchall()
    conn.close()
    return [dict(row) for row in users]

def get_key_usage_history(key):
    conn = get_db()
    history = conn.execute('SELECT * FROM key_usage_history WHERE key = ? ORDER BY used_at DESC', (key,)).fetchall()
    conn.close()
    return [dict(row) for row in history]

def generate_unique_username():
    """Generate a unique username"""
    adjectives = ['happy', 'cool', 'smart', 'brave', 'swift', 'lucky', 'wild', 'mighty', 'epic', 'hero']
    nouns = ['user', 'player', 'gamer', 'master', 'pro', 'star', 'legend', 'champ', 'ace', 'king']
    
    import random
    base = random.choice(adjectives) + random.choice(nouns)
    username = base + str(random.randint(100, 999))
    
    # Check if exists
    existing = get_user_by_username(username)
    if existing:
        return generate_unique_username()
    return username

def create_user_account():
    """Create a new user account with unique details"""
    username = generate_unique_username()
    email = username + '@unique.com'
    password = secrets.token_hex(8)
    
    user_id = insert_user(username, email, password)
    
    return {
        'id': user_id,
        'username': username,
        'email': email,
        'password': password
    }

# ============ HTML ============

AGREE_PAGE = '''
<!DOCTYPE html>
<html>
<head>
    <title>UNIQUE MODS ONLINE</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin:0; padding:0; box-sizing:border-box; }
        body { 
            font-family: Arial, sans-serif; 
            background: #0a0a0a; 
            display: flex; 
            justify-content: center; 
            align-items: center; 
            min-height: 100vh;
            background: radial-gradient(circle at center, #1a1a2e 0%, #0a0a0a 100%);
        }
        .container { 
            background: rgba(26, 26, 46, 0.95); 
            padding: 50px 40px; 
            border-radius: 20px; 
            width: 500px; 
            max-width: 92%; 
            box-shadow: 0 20px 60px rgba(255,215,0,0.15);
            border: 1px solid rgba(255,215,0,0.1);
            text-align: center;
        }
        .logo { 
            font-size: 28px; 
            font-weight: 800; 
            color: #FFD700; 
            margin-bottom: 10px;
            letter-spacing: 1px;
        }
        .sub { 
            color: #888; 
            font-size: 14px; 
            margin-bottom: 30px;
        }
        .icon { font-size: 60px; margin-bottom: 20px; }
        .info-box {
            background: #0d0d1a;
            padding: 20px;
            border-radius: 12px;
            margin: 20px 0;
            border: 1px solid #222;
        }
        .info-box p {
            color: #aaa;
            font-size: 14px;
            line-height: 1.8;
        }
        .info-box strong {
            color: #FFD700;
        }
        .btn {
            width: 100%;
            padding: 16px;
            background: linear-gradient(135deg, #FFD700, #f5c400);
            color: #0a0a0a;
            border: none;
            border-radius: 10px;
            font-size: 18px;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 30px rgba(255,215,0,0.3);
        }
        .btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
        }
        .loading {
            display: none;
            margin: 15px 0;
        }
        .loading.active {
            display: block;
        }
        .spinner {
            width: 40px;
            height: 40px;
            margin: 0 auto;
            border: 4px solid #333;
            border-top: 4px solid #FFD700;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .status-text {
            color: #FFD700;
            font-size: 14px;
            margin-top: 10px;
        }
        .footer { 
            margin-top: 25px; 
            color: #555; 
            font-size: 12px; 
        }
        .footer a { 
            color: #FFD700; 
            text-decoration: none; 
        }
        .checkbox-group { 
            display: flex; 
            align-items: center; 
            gap: 10px; 
            margin: 20px 0;
            text-align: left;
        }
        .checkbox-group input[type="checkbox"] { 
            width: 20px; 
            height: 20px; 
            accent-color: #FFD700; 
            cursor: pointer; 
        }
        .checkbox-group label { 
            color: #aaa; 
            font-size: 14px; 
            cursor: pointer; 
        }
        .checkbox-group a { 
            color: #FFD700; 
            text-decoration: none; 
        }
        .checkbox-group a:hover { text-decoration: underline; }
        .countdown {
            color: #FFD700;
            font-size: 20px;
            font-weight: bold;
            margin: 10px 0;
        }
        .credentials {
            background: #0d0d1a;
            padding: 15px;
            border-radius: 8px;
            margin: 15px 0;
            border: 1px solid #00ff88;
            display: none;
        }
        .credentials.show {
            display: block;
        }
        .credentials p {
            color: #00ff88;
            font-size: 13px;
            font-family: monospace;
            margin: 5px 0;
        }
        .credentials strong {
            color: #aaa;
        }
    </style>
</head>
<body>
<div class="container">
    <div class="icon">🚀</div>
    <div class="logo">UNIQUE MODS ONLINE</div>
    <div class="sub">Welcome to the Platform</div>
    
    <div class="info-box">
        <p>By clicking "I Agree", you will be automatically registered.</p>
        <p>Your account will be created in <strong>10 seconds</strong>.</p>
        <p style="margin-top:10px;color:#666;font-size:12px;">You will be redirected to the dashboard automatically.</p>
    </div>
    
    <div class="checkbox-group">
        <input type="checkbox" id="agreeTerms" onchange="toggleButton()">
        <label for="agreeTerms">
            I agree to the <a href="/privacy" target="_blank">Privacy Policy</a> and 
            <a href="/terms" target="_blank">Terms of Service</a>
        </label>
    </div>
    
    <button id="agreeBtn" class="btn" disabled onclick="startAgreement()">I AGREE</button>
    
    <div id="loadingSection" class="loading">
        <div class="spinner"></div>
        <div id="countdownDisplay" class="countdown">10</div>
        <div id="statusText" class="status-text">Creating your account...</div>
    </div>
    
    <div id="credentials" class="credentials">
        <p><strong>Account Created!</strong></p>
        <p>Username: <span id="credUsername"></span></p>
        <p>Email: <span id="credEmail"></span></p>
        <p>Password: <span id="credPassword"></span></p>
        <p style="color:#666;font-size:11px;margin-top:10px;">Redirecting to dashboard...</p>
    </div>
    
    <div class="footer">
        Made by: <a href="https://t.me/+FsOBvTfVSjRlNmFl">Farhan Modz</a>
    </div>
</div>

<script>
let countdown = 10;
let timer = null;

function toggleButton() {
    const checkbox = document.getElementById('agreeTerms');
    const btn = document.getElementById('agreeBtn');
    btn.disabled = !checkbox.checked;
}

function startAgreement() {
    const btn = document.getElementById('agreeBtn');
    btn.disabled = true;
    document.getElementById('loadingSection').classList.add('active');
    document.getElementById('statusText').textContent = 'Creating your account...';
    
    // Start countdown
    timer = setInterval(() => {
        countdown--;
        document.getElementById('countdownDisplay').textContent = countdown;
        
        if (countdown <= 0) {
            clearInterval(timer);
            createAccount();
        }
    }, 1000);
}

function createAccount() {
    document.getElementById('statusText').textContent = 'Generating your account...';
    
    fetch('/api/create-account', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
    })
    .then(res => res.json())
    .then(data => {
        if (data.error) {
            document.getElementById('statusText').textContent = 'Error: ' + data.error;
            return;
        }
        
        // Show credentials
        document.getElementById('credentials').classList.add('show');
        document.getElementById('credUsername').textContent = data.username;
        document.getElementById('credEmail').textContent = data.email;
        document.getElementById('credPassword').textContent = data.password;
        document.getElementById('statusText').textContent = 'Account created successfully!';
        
        // Auto login
        setTimeout(() => {
            window.location.href = '/dashboard';
        }, 3000);
    })
    .catch(err => {
        document.getElementById('statusText').textContent = 'Error: ' + err.message;
    });
}
</script>
</body>
</html>
'''

PRIVACY_PAGE = '''
<!DOCTYPE html>
<html>
<head>
    <title>UNIQUE MODS - Privacy Policy</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin:0; padding:0; box-sizing:border-box; }
        body { font-family: Arial, sans-serif; background: #0a0a0a; padding: 20px; }
        .container { max-width: 800px; margin: 0 auto; background: #1a1a2e; padding: 40px; border-radius: 16px; box-shadow: 0 0 40px rgba(255,215,0,0.1); }
        .logo { text-align: center; font-size: 24px; font-weight: bold; color: #FFD700; margin-bottom: 20px; }
        h2 { color: #FFD700; margin: 20px 0 10px 0; }
        p, li { color: #aaa; line-height: 1.8; font-size: 14px; }
        ul { padding-left: 20px; }
        .back-btn { display: inline-block; padding: 10px 24px; background: #FFD700; color: #0a0a0a; text-decoration: none; border-radius: 8px; font-weight: bold; margin-top: 20px; }
        .back-btn:hover { background: #e6c200; }
        .footer { text-align: center; margin-top: 30px; color: #444; font-size: 12px; }
        .footer a { color: #FFD700; text-decoration: none; }
    </style>
</head>
<body>
<div class="container">
    <div class="logo">UNIQUE MODS</div>
    <h1 style="color:#FFD700;font-size:28px;margin-bottom:10px;">Privacy Policy</h1>
    <p>Last updated: August 19, 2026</p>
    
    <h2>1. Information We Collect</h2>
    <ul>
        <li><strong>Account Information:</strong> Username, email address, and hashed password</li>
        <li><strong>Usage Data:</strong> Key usage history and device information</li>
        <li><strong>Cookies:</strong> Session cookies for authentication</li>
    </ul>
    
    <h2>2. How We Use Your Information</h2>
    <ul>
        <li>To provide and maintain our service</li>
        <li>To authenticate your identity</li>
        <li>To track key usage and prevent abuse</li>
        <li>To communicate with you about updates</li>
    </ul>
    
    <h2>3. Data Security</h2>
    <ul>
        <li>Passwords are stored using MD5 hashing</li>
        <li>All data is stored in encrypted SQLite database</li>
        <li>We implement session-based authentication</li>
    </ul>
    
    <h2>4. Data Sharing</h2>
    <ul>
        <li>We do not sell or share your personal data</li>
        <li>Key usage history is logged for security</li>
    </ul>
    
    <h2>5. Your Rights</h2>
    <ul>
        <li>You can delete your account at any time</li>
        <li>You can request data export</li>
    </ul>
    
    <h2>6. Contact</h2>
    <p>For privacy concerns, contact us via <a href="https://t.me/+FsOBvTfVSjRlNmFl" style="color:#FFD700;">Telegram</a></p>
    
    <a href="/" class="back-btn">Back</a>
    
    <div class="footer">
        Made by: <a href="https://t.me/+FsOBvTfVSjRlNmFl">Farhan Modz</a>
    </div>
</div>
</body>
</html>
'''

TERMS_PAGE = '''
<!DOCTYPE html>
<html>
<head>
    <title>UNIQUE MODS - Terms of Service</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin:0; padding:0; box-sizing:border-box; }
        body { font-family: Arial, sans-serif; background: #0a0a0a; padding: 20px; }
        .container { max-width: 800px; margin: 0 auto; background: #1a1a2e; padding: 40px; border-radius: 16px; box-shadow: 0 0 40px rgba(255,215,0,0.1); }
        .logo { text-align: center; font-size: 24px; font-weight: bold; color: #FFD700; margin-bottom: 20px; }
        h2 { color: #FFD700; margin: 20px 0 10px 0; }
        p, li { color: #aaa; line-height: 1.8; font-size: 14px; }
        ul { padding-left: 20px; }
        .back-btn { display: inline-block; padding: 10px 24px; background: #FFD700; color: #0a0a0a; text-decoration: none; border-radius: 8px; font-weight: bold; margin-top: 20px; }
        .back-btn:hover { background: #e6c200; }
        .footer { text-align: center; margin-top: 30px; color: #444; font-size: 12px; }
        .footer a { color: #FFD700; text-decoration: none; }
    </style>
</head>
<body>
<div class="container">
    <div class="logo">UNIQUE MODS</div>
    <h1 style="color:#FFD700;font-size:28px;margin-bottom:10px;">Terms of Service</h1>
    <p>Last updated: August 19, 2026</p>
    
    <h2>1. Acceptance of Terms</h2>
    <p>By using UNIQUE MODS, you agree to these terms.</p>
    
    <h2>2. User Accounts</h2>
    <ul>
        <li>You must provide accurate information</li>
        <li>You are responsible for your account security</li>
        <li>One account per user</li>
    </ul>
    
    <h2>3. Key Usage</h2>
    <ul>
        <li>Keys are for personal use only</li>
        <li>Sharing keys is prohibited</li>
        <li>Keys have expiry dates</li>
    </ul>
    
    <h2>4. Prohibited Activities</h2>
    <ul>
        <li>Unauthorized access to system</li>
        <li>Abusing the key system</li>
        <li>Creating multiple accounts</li>
    </ul>
    
    <h2>5. Account Termination</h2>
    <ul>
        <li>We reserve the right to terminate accounts</li>
        <li>Violation of terms results in suspension</li>
    </ul>
    
    <h2>6. Changes to Terms</h2>
    <p>We may update terms with notice to users.</p>
    
    <a href="/" class="back-btn">Back</a>
    
    <div class="footer">
        Made by: <a href="https://t.me/+FsOBvTfVSjRlNmFl">Farhan Modz</a>
    </div>
</div>
</body>
</html>
'''

DASHBOARD = '''
<!DOCTYPE html>
<html>
<head>
    <title>UNIQUE MODS - Dashboard</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin:0; padding:0; box-sizing:border-box; }
        body { font-family: Arial, sans-serif; background: #0a0a0a; padding: 20px; }
        .container { max-width: 1000px; margin: 0 auto; }
        .header { background: #1a1a2e; padding: 20px; border-radius: 12px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; }
        .logo { color: #FFD700; font-size: 20px; font-weight: bold; }
        .user { color: #888; }
        .user span { color: #FFD700; }
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
        .key-item .owner { color: #6c5ce7; font-size: 12px; }
        .footer { text-align: center; margin-top: 30px; color: #444; font-size: 12px; }
        .footer a { color: #FFD700; text-decoration: none; }
        .made { text-align: center; color: #333; font-size: 11px; margin-top: 10px; }
        .join-btn { display: inline-block; background: #0088cc; color: white; padding: 10px 24px; border-radius: 6px; text-decoration: none; font-weight: bold; margin: 10px 0; }
        .join-btn:hover { background: #006699; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 12px; }
        .stat-box { background: #0d0d1a; padding: 12px; border-radius: 8px; text-align: center; }
        .stat-box .num { color: #FFD700; font-size: 22px; font-weight: bold; }
        .stat-box .label { color: #666; font-size: 12px; }
        .tabs { display: flex; margin-bottom: 20px; border-bottom: 1px solid #333; flex-wrap: wrap; }
        .tab { padding: 10px 20px; color: #888; cursor: pointer; border-bottom: 3px solid transparent; transition: 0.3s; }
        .tab.active { color: #FFD700; border-bottom-color: #FFD700; }
        .tab:hover { color: #FFD700; }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        .success { color: #00ff88; text-align: center; margin-top: 12px; font-size: 14px; }
        .error { color: #ff4444; text-align: center; margin-top: 12px; font-size: 14px; }
        .result-box { padding: 10px; margin-top: 10px; border-radius: 6px; }
        .btn-users { background: #6c5ce7; color: white; border: none; padding: 8px 20px; border-radius: 6px; cursor: pointer; }
        .btn-users:hover { background: #5a4bd1; }
        .header-buttons { display: flex; gap: 10px; flex-wrap: wrap; }
        .username-display { background: #0d0d1a; padding: 5px 15px; border-radius: 20px; border: 1px solid #FFD700; }
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <div>
            <div class="logo">UNIQUE MODS</div>
            <div class="user">Welcome, <span>{{ username }}</span></div>
        </div>
        <div class="header-buttons">
            <a href="/users"><button class="btn-users">Users</button></a>
            <a href="/telegram" target="_blank"><button class="btn-telegram">Join Updates</button></a>
        </div>
    </div>

    <div class="tabs">
        <div class="tab active" onclick="showTab('generate')">Generate Key</div>
        <div class="tab" onclick="showTab('allkeys')">All Keys</div>
        <div class="tab" onclick="showTab('stats')">Statistics</div>
        <div class="tab" onclick="showTab('connect')">Connect API</div>
        <div class="tab" onclick="showTab('use')">Use Key</div>
    </div>

    <div id="generate-tab" class="tab-content active">
        <div class="card">
            <h2>Generate Custom Key</h2>
            <div class="input-group">
                <input type="text" id="customDevice" placeholder="Device ID" required>
                <input type="text" id="customExpire" placeholder="Expiry (e.g. 18-August-2026)" required>
                <input type="text" id="customKeyInput" placeholder="Enter Custom Key" required>
                <button onclick="generateCustomKey()">Generate</button>
            </div>
            <div id="customResult" class="result-box"></div>
        </div>
    </div>

    <div id="allkeys-tab" class="tab-content">
        <div class="card">
            <h2>All Keys</h2>
            <div id="allKeysList"></div>
        </div>
    </div>

    <div id="stats-tab" class="tab-content">
        <div class="card">
            <h2>Statistics</h2>
            <div class="stats">
                <div class="stat-box"><div class="num">{{ stats.total }}</div><div class="label">Total Keys</div></div>
                <div class="stat-box"><div class="num">{{ stats.active }}</div><div class="label">Active</div></div>
                <div class="stat-box"><div class="num">{{ stats.used }}</div><div class="label">Used</div></div>
                <div class="stat-box"><div class="num">{{ stats.users }}</div><div class="label">Total Users</div></div>
            </div>
        </div>
    </div>

    <div id="connect-tab" class="tab-content">
        <div class="card">
            <h2>API Connect Status</h2>
            <div id="apiStatus" class="result-box">
                <p style="color:#666;">Checking API status...</p>
            </div>
            <button onclick="checkAPI()" style="background:#FFD700;color:#0a0a0a;border:none;padding:10px 24px;border-radius:6px;font-weight:bold;cursor:pointer;margin-top:12px;">Check API</button>
        </div>
    </div>

    <div id="use-tab" class="tab-content">
        <div class="card">
            <h2>Use a Key</h2>
            <p>Enter a key to mark it as used</p>
            <div class="input-group">
                <input type="text" id="useKeyInput" placeholder="Enter key to use" required>
                <button onclick="useKey()">Use Key</button>
            </div>
            <div id="useResult" class="result-box"></div>
        </div>
    </div>

    <div class="card">
        <h2>Join For Updates</h2>
        <a href="https://t.me/+FsOBvTfVSjRlNmFl" target="_blank" class="join-btn">Join Telegram Channel</a>
    </div>

    <div class="footer">
        Made by: <a href="https://t.me/+FsOBvTfVSjRlNmFl">Farhan Modz</a>
    </div>
    <div class="made">UNIQUE MODS &copy; 2026</div>
</div>

<script>
function showTab(tab) {
    document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.tab').forEach(el => el.classList.remove('active'));
    document.getElementById(tab + '-tab').classList.add('active');
    document.querySelector('.tab[onclick="showTab(\'' + tab + '\')"]').classList.add('active');
    
    if (tab === 'allkeys') {
        loadAllKeys();
    }
}

function generateCustomKey() {
    const device = document.getElementById('customDevice').value;
    const expire = document.getElementById('customExpire').value;
    const customKey = document.getElementById('customKeyInput').value;
    const resultDiv = document.getElementById('customResult');
    
    if (!device || !expire || !customKey) {
        resultDiv.innerHTML = '<div class="error">Please fill all fields</div>';
        return;
    }
    
    resultDiv.innerHTML = '<p style="color:#FFD700;">Generating...</p>';
    
    fetch('/api/key/generate?device=' + encodeURIComponent(device) + '&expire=' + encodeURIComponent(expire) + '&custom_key=' + encodeURIComponent(customKey))
    .then(res => res.json())
    .then(data => {
        if (data.error) {
            resultDiv.innerHTML = '<div class="error">Error: ' + data.error + '</div>';
        } else {
            resultDiv.innerHTML = '<div class="success">Custom key generated: <strong style="color:#00ff88;">' + data.key + '</strong><br>Device: ' + data.device + '<br>Expires: ' + data.expiry + '<br>Owner: ' + data.owner + '</div>';
            document.getElementById('customDevice').value = '';
            document.getElementById('customExpire').value = '';
            document.getElementById('customKeyInput').value = '';
            loadAllKeys();
        }
    })
    .catch(err => {
        resultDiv.innerHTML = '<div class="error">Error: ' + err.message + '</div>';
    });
}

function useKey() {
    const key = document.getElementById('useKeyInput').value.trim();
    const resultDiv = document.getElementById('useResult');
    
    if (!key) {
        resultDiv.innerHTML = '<div class="error">Please enter a key</div>';
        return;
    }
    
    resultDiv.innerHTML = '<p style="color:#FFD700;">Processing...</p>';
    
    fetch('/api/key/use', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key: key })
    })
    .then(res => res.json())
    .then(data => {
        if (data.error) {
            resultDiv.innerHTML = '<div class="error">' + data.error + '</div>';
        } else {
            resultDiv.innerHTML = '<div class="success">Key used successfully!<br>Key: ' + data.key + '<br>Used by: ' + data.used_by + '<br>Used at: ' + data.used_at + '</div>';
            document.getElementById('useKeyInput').value = '';
            loadAllKeys();
        }
    })
    .catch(err => {
        resultDiv.innerHTML = '<div class="error">Error: ' + err.message + '</div>';
    });
}

function loadAllKeys() {
    const listDiv = document.getElementById('allKeysList');
    listDiv.innerHTML = '<p style="color:#666;">Loading...</p>';
    
    fetch('/api/keys/all')
    .then(res => res.json())
    .then(data => {
        if (data.error) {
            listDiv.innerHTML = '<p style="color:#ff4444;">Error: ' + data.error + '</p>';
            return;
        }
        
        if (data.keys && data.keys.length > 0) {
            let html = '<div class="key-list">';
            data.keys.forEach(key => {
                const status = key.used ? '<span class="status-used">USED</span>' : '<span class="status-active">ACTIVE</span>';
                html += '<div class="key-item">' +
                    '<span class="key">' + key.key + '</span>' +
                    '<span class="info">Device: ' + key.device + ' | Expires: ' + key.expiry + '</span>' +
                    '<span class="owner">Owner: ' + key.owner_username + '</span>' +
                    status +
                '</div>';
            });
            html += '</div>';
            listDiv.innerHTML = html;
        } else {
            listDiv.innerHTML = '<p style="color:#666;">No keys found</p>';
        }
    })
    .catch(err => {
        listDiv.innerHTML = '<p style="color:#ff4444;">Error loading keys</p>';
    });
}

function checkAPI() {
    const statusDiv = document.getElementById('apiStatus');
    statusDiv.innerHTML = '<p style="color:#FFD700;">Connecting to API...</p>';
    
    fetch('/api/connect')
    .then(res => res.json())
    .then(data => {
        if (data.error) {
            statusDiv.innerHTML = '<div class="error">Error: ' + data.error + '</div>';
        } else {
            statusDiv.innerHTML = '<div class="success">' +
                'Status: ' + data.status + '<br>' +
                'Made by: ' + data.made_by + '<br>' +
                'User: ' + data.user + '<br>' +
                'Admin: ' + data.is_admin +
            '</div>';
        }
    })
    .catch(err => {
        statusDiv.innerHTML = '<div class="error">Error: ' + err.message + '</div>';
    });
}

// Load data on page load
document.addEventListener('DOMContentLoaded', function() {
    loadAllKeys();
    checkAPI();
});
</script>
</body>
</html>
'''

USERS_PAGE = '''
<!DOCTYPE html>
<html>
<head>
    <title>UNIQUE MODS - Users</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin:0; padding:0; box-sizing:border-box; }
        body { font-family: Arial, sans-serif; background: #0a0a0a; padding: 20px; }
        .container { max-width: 1000px; margin: 0 auto; }
        .header { background: #1a1a2e; padding: 20px; border-radius: 12px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; }
        .logo { color: #FFD700; font-size: 20px; font-weight: bold; }
        .back-btn { background: #FFD700; color: #0a0a0a; border: none; padding: 8px 20px; border-radius: 6px; cursor: pointer; font-weight: bold; }
        .back-btn:hover { background: #e6c200; }
        .card { background: #1a1a2e; border-radius: 12px; padding: 20px; margin-bottom: 16px; }
        .card h2 { color: #FFD700; font-size: 18px; margin-bottom: 12px; }
        .user-item { background: #0d0d1a; padding: 12px 16px; border-radius: 6px; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; border-left: 3px solid #6c5ce7; }
        .user-item .username { color: #00ff88; font-weight: bold; }
        .user-item .email { color: #888; font-size: 14px; }
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
            <div class="logo">UNIQUE MODS</div>
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
                </div>
                <div style="display: flex; gap: 8px; align-items: center;">
                    <span style="color: #666; font-size: 12px;">Joined: {{ user.created_at[:10] }}</span>
                    <button class="delete-btn" onclick="deleteUser('{{ user.id }}', '{{ user.username }}')">Delete</button>
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

@app.route('/')
def index():
    # Check if user is already logged in
    if is_logged_in():
        return redirect('/dashboard')
    return render_template_string(AGREE_PAGE)

@app.route('/api/create-account', methods=['POST'])
def create_account():
    try:
        # Create new user account
        user = create_user_account()
        
        # Auto login
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['email'] = user['email']
        session['is_admin'] = True
        
        return jsonify({
            'success': True,
            'id': user['id'],
            'username': user['username'],
            'email': user['email'],
            'password': user['password']
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/dashboard')
def dashboard():
    if not is_logged_in():
        return redirect('/')
    
    user = get_user_by_id(session['user_id'])
    
    if not user:
        session.clear()
        return redirect('/')
    
    stats = get_stats()
    return render_template_string(DASHBOARD,
        username=session.get('username', 'User'),
        stats=stats
    )

@app.route('/users')
def list_users():
    if not is_logged_in():
        return redirect('/')
    
    users = get_all_users()
    return render_template_string(USERS_PAGE, users=users)

@app.route('/privacy')
def privacy():
    return render_template_string(PRIVACY_PAGE)

@app.route('/terms')
def terms():
    return render_template_string(TERMS_PAGE)

@app.route('/telegram')
def telegram():
    return redirect('https://t.me/+FsOBvTfVSjRlNmFl')

# ============ API ENDPOINTS ============

@app.route('/api/connect', methods=['GET'])
def api_connect():
    if not is_logged_in():
        return jsonify({'error': 'Unauthorized'}), 401
    
    return jsonify({
        'status': 'online',
        'made_by': 'Farhan Modz',
        'user': session.get('username'),
        'is_admin': True
    })

@app.route('/api/key/generate', methods=['GET', 'POST'])
def api_generate():
    if not is_logged_in():
        return jsonify({'error': 'Unauthorized'}), 401
    
    if request.method == 'POST':
        data = request.get_json()
        device = data.get('device') if data else None
        expiry = data.get('expire') if data else None
        custom_key = data.get('custom_key') if data else None
    else:
        device = request.args.get('device')
        expiry = request.args.get('expire')
        custom_key = request.args.get('custom_key')
    
    if not device or not expiry:
        return jsonify({'error': 'Missing parameters: device and expire required'}), 400
    
    if not custom_key:
        return jsonify({'error': 'Custom key is required'}), 400
    
    key = ''.join(c for c in custom_key if c.isalnum())
    if len(key) < 4:
        return jsonify({'error': 'Key too short (min 4 chars)'}), 400
    
    try:
        expiry_date = datetime.strptime(expiry, '%d-%B-%Y')
        expiry = expiry_date.strftime('%d-%B-%Y')
    except:
        return jsonify({'error': 'Invalid expiry format. Use DD-Month-YYYY (e.g. 18-August-2026)'}), 400
    
    existing = get_key_by_key(key)
    if existing:
        return jsonify({'error': 'Key already exists'}), 400
    
    try:
        username = session.get('username')
        insert_key(key, device, expiry, session['user_id'], username)
        return jsonify({
            'success': True,
            'key': key,
            'device': device,
            'expiry': expiry,
            'owner': username
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/key/use', methods=['POST'])
def api_use_key():
    if not is_logged_in():
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    key = data.get('key')
    if not key:
        return jsonify({'error': 'Key is required'}), 400
    
    key_record = get_key_by_key(key)
    
    if not key_record:
        return jsonify({'error': 'Key not found'}), 404
    
    if key_record['used'] == 1:
        return jsonify({'error': 'Key already used'}), 400
    
    try:
        update_key_used(key, session['user_id'], session['username'])
        return jsonify({
            'success': True,
            'key': key,
            'used_by': session['username'],
            'used_at': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/keys/all', methods=['GET'])
def api_all_keys():
    if not is_logged_in():
        return jsonify({'error': 'Unauthorized'}), 401
    
    keys = get_all_keys()
    return jsonify({
        'total': len(keys),
        'keys': keys
    })

@app.route('/api/stats', methods=['GET'])
def api_stats():
    if not is_logged_in():
        return jsonify({'error': 'Unauthorized'}), 401
    
    stats = get_stats()
    return jsonify(stats)

@app.route('/api/user/delete/<int:user_id>', methods=['DELETE'])
def api_delete_user(user_id):
    if not is_logged_in():
        return jsonify({'error': 'Unauthorized'}), 401
    
    if user_id == session.get('user_id'):
        return jsonify({'error': 'Cannot delete yourself'}), 400
    
    try:
        delete_user_by_id(user_id)
        return jsonify({'success': True, 'message': 'User deleted successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/user/all', methods=['GET'])
def api_all_users():
    if not is_logged_in():
        return jsonify({'error': 'Unauthorized'}), 401
    
    users = get_all_users()
    return jsonify({
        'total': len(users),
        'users': users
    })

@app.route('/api/key/check/<key>', methods=['GET'])
def api_check_key(key):
    if not is_logged_in():
        return jsonify({'error': 'Unauthorized'}), 401
    
    key_record = get_key_by_key(key)
    
    if not key_record:
        return jsonify({'exists': False, 'message': 'Key not found'}), 404
    
    return jsonify({
        'exists': True,
        'key': key_record['key'],
        'device': key_record['device'],
        'expiry': key_record['expiry'],
        'used': bool(key_record['used']),
        'status': 'USED' if key_record['used'] == 1 else 'ACTIVE',
        'owner': key_record['owner_username']
    })

@app.route('/api/profile', methods=['GET'])
def api_profile():
    if not is_logged_in():
        return jsonify({'error': 'Unauthorized'}), 401
    
    user = get_user_by_id(session['user_id'])
    
    if not user:
        session.clear()
        return jsonify({'error': 'User not found'}), 404
    
    keys = get_keys_by_user(session['user_id'])
    
    return jsonify({
        'id': user['id'],
        'username': user['username'],
        'email': user['email'],
        'created_at': user['created_at'],
        'keys_generated': len(keys)
    })

@app.route('/api/key/history/<key>', methods=['GET'])
def api_key_history(key):
    if not is_logged_in():
        return jsonify({'error': 'Unauthorized'}), 401
    
    key_record = get_key_by_key(key)
    if not key_record:
        return jsonify({'error': 'Key not found'}), 404
    
    history = get_key_usage_history(key)
    return jsonify({
        'key': key,
        'history': history
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)