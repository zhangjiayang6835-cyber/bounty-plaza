<content>
import json
import hmac
import hashlib
from flask import Flask, request, jsonify
from functools import wraps
import pickle
import os

app = Flask(__name__)

# Secret key for HMAC signing
SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-here')

def verify_pickle_data(data, signature):
    """Verify the integrity of pickle data using HMAC"""
    expected_signature = hmac.new(SECRET_KEY.encode(), data, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected_signature, signature)

@app.route('/session', methods=['GET', 'POST'])
def session_handler():
    if request.method == 'POST':
        # This is the old vulnerable code - left for comparison
        # session_data = pickle.dumps(request.json)
        # app.redis.set('user_session', session_data)
        
        # New secure implementation using JSON
        session_data = json.dumps(request.json).encode('utf-8')
        
        # Create HMAC signature for integrity verification
        signature = hmac.new(SECRET_KEY.encode(), session_data, hashlib.sha256).hexdigest()
        
        # Store both data and signature
        app.redis.set('user_session', session_data)
        app.redis.set('user_session_sig', signature)
        
        return jsonify({"status": "Session saved"}), 200
    
    if request.method == 'GET':
        # Get session data and signature
        session_data = app.redis.get('user_session')
        signature = app.redis.get('user_session_sig')
        
        if not session_data or not signature:
            return jsonify({"error": "No session found"}), 404
        
        # Verify the integrity of the data
        if not verify_pickle_data(session_data, signature):
            return jsonify({"error": "Invalid session data"}), 400
        
        # Deserialize JSON data instead of pickle
        try:
            session = json.loads(session_data.decode('utf-8'))
            return jsonify(session), 200
        except json.JSONDecodeError:
            return jsonify({"error": "Invalid session format"}), 400
    
    return jsonify({"error": "Method not allowed"}), 405

if __name__ == '__main__':
    # Mock Redis for demonstration
    class MockRedis:
        def __init__(self):
            self.data = {}
        
        def get(self, key):
            return self.data.get(key)
        
        def set(self, key, value):
            self.data[key] = value
    
    app.redis = MockRedis()
    app.run(debug=True)
</content>