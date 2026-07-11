# fix_mongodb_nosql.py
import bcrypt
import re

class NoSQLInjectionProtection:
    """Protect against MongoDB NoSQL injection in authentication."""

    # MongoDB query operators that should never be in user input
    MONGODB_OPERATORS = {
        '$gt', '$gte', '$lt', '$lte', '$ne', '$eq',
        '$in', '$nin', '$regex', '$exists', '$type',
        '$mod', '$all', '$size', '$text', '$where',
        '$elemMatch', '$push', '$pull', '$unset',
    }

    @staticmethod
    def is_operator(key):
        """Check if a key is a MongoDB query operator."""
        return key.startswith('$')

    @staticmethod
    def validate_login_input(username, password):
        """Validate that username and password are plain strings."""
        # Username must be a plain string
        if not isinstance(username, str) or not username.strip():
            return False, "Invalid username"

        # Password must be a plain string
        if not isinstance(password, str) or len(password) < 8:
            return False, "Invalid password"

        # Check for MongoDB operators in string values
        for val in [username, password]:
            for op in NoSQLInjectionProtection.MONGODB_OPERATORS:
                if op in val:
                    return False, "Invalid input: contains query operator"
            # Check for regex patterns
            if re.search(r'[\{\}\\\[\]]', val):
                return False, "Invalid input: contains special characters"

        return True, None

    @staticmethod
    def secure_login_query(db, username, password):
        """
        Securely query MongoDB for user authentication.
        Validates types to prevent NoSQL injection.
        """
        valid, error = NoSQLInjectionProtection.validate_login_input(username, password)
        if not valid:
            return None, error

        # Use type-safe query - only compare string values
        # NEVER pass user input as an object
        user = db.users.find_one({
            'username': {'$type': 2, '$eq': username},  # $type: 2 = string
        })

        if user and user.get('active', True):
            stored_hash = user.get('password_hash')
            if bcrypt.checkpw(password.encode('utf-8'), stored_hash):
                return {'id': str(user['_id']), 'username': user['username']}, None

        return None, "Invalid credentials"