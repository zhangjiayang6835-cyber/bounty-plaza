# fix_sqli_login.py
import bcrypt

class SQLInjectionProtection:
    """Protect against SQL injection in the login endpoint."""

    # Valid character set for usernames
    VALID_USERNAME_CHARS = set('abcdefghijklmnopqrstuvwxyz0123456789_.-@')

    @staticmethod
    def validate_username(username):
        """Validate username format to prevent injection."""
        if not username or len(username) > 64:
            return False
        return all(c in SQLInjectionProtection.VALID_USERNAME_CHARS for c in username.lower())

    @staticmethod
    def validate_password(password):
        """Validate password format."""
        if not password or len(password) < 8 or len(password) > 128:
            return False
        return True

    @staticmethod
    def secure_login_query(cursor, username, password):
        """
        Execute a secure login query using parameterized statements.
        Uses bcrypt for password comparison.
        """
        # Validate inputs first
        if not SQLInjectionProtection.validate_username(username):
            return None, "Invalid username format"
        if not SQLInjectionProtection.validate_password(password):
            return None, "Invalid password format"

        # Parameterized query - NEVER concatenate user input
        query = "SELECT id, username, password_hash, role FROM users WHERE username = ? AND active = 1"
        cursor.execute(query, (username,))
        result = cursor.fetchone()

        if result:
            stored_hash = result[2]
            if bcrypt.checkpw(password.encode('utf-8'), stored_hash):
                return {
                    'id': result[0],
                    'username': result[1],
                    'role': result[3]
                }, None
            return None, "Invalid password"
        return None, "User not found"

    @staticmethod
    def hash_password(password):
        """Hash a password using bcrypt."""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(12))