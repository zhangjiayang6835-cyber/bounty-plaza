from flask import Flask, request, jsonify
import json
import hmac
import hashlib
import secrets
from functools import wraps

app = Flask(__name__)

# Configuration
SECRET_KEY = secrets.token_hex(32)  # Generate a secure secret key

# Simple in-memory storage for demonstration
# In a real application, this would be Redis or another cache system
cache_storage = {}

def verify_session_signature(session_data, signature):
    """Verify the HMAC signature of session data"""
    expected_signature = hmac.new(
        SECRET_KEY.encode(),
        session_data.encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected_signature, signature)

def get_session(session_id):
    """Retrieve session from cache with signature verification"""
    session_data = cache_storage.get(session_id)
    if not session_data:
        return None
    
    # Split stored data into actual data and signature
    if '|' not in session_data:
        return None  # Invalid format
    
    data, signature = session_data.rsplit('|', 1)
    
    if verify_session_signature(data, signature):
        return json.loads(data)
    return None

def set_session(session_id, data):
    """Store session in cache with HMAC signature"""
    data_str = json.dumps(data)
    signature = hmac.new(
        SECRET_KEY.encode(),
        data_str.encode(),
        hashlib.sha256
    ).hexdigest()
    cache_storage[session_id] = f"{data_str}|{signature}"

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        session_id = request.cookies.get('session_id')
        if not session_id:
            return jsonify({"error": "Unauthorized"}), 401
        
        session = get_session(session_id)
        if not session:
            return jsonify({"error": "Invalid session"}), 401
        
        # Add session data to request for access in route handlers
        request.session = session
        return f(*args, **kwargs)
    return decorated

@app.route('/login', methods=['POST'])
def login():
    username = request.json.get('username')
    password = request.json.get('password')
    
    # In a real app, you'd verify credentials against a database
    if username == 'admin' and password == 'password':
        session_id = secrets.token_urlsafe(16)
        session_data = {
            'user_id': 1,
            'username': username,
            'role': 'admin'
        }
        set_session(session_id, session_data)
        response = jsonify({"message": "Login successful"})
        response.set_cookie('session_id', session_id)
        return response
    
    return jsonify({"error": "Invalid credentials"}), 401

@app.route('/profile')
@require_auth
def profile():
    return jsonify({
        "user_id": request.session.get('user_id'),
        "username": request.session.get('username'),
        "role": request.session.get('role')
    })

@app.route('/admin')
@require_auth
def admin():
    # Only allow access to admin users
    if request.session.get('role') != 'admin':
        return jsonify({"error": "Unauthorized"}), 403
    
    return jsonify({"message": "Welcome to admin panel!"})

if __name__ == '__main__':
    app.run(debug=True)