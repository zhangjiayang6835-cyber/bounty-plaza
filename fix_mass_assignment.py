# fix_mass_assignment.py

class MassAssignmentProtection:
    """Protect against mass assignment / privilege escalation attacks."""

    # Whitelist of fields that users are allowed to update
    ALLOWED_UPDATE_FIELDS = {
        'display_name',
        'bio',
        'avatar_url',
        'email',
        'phone',
        'preferences',
    }

    # Sensitive fields that must never be set via user input
    SENSITIVE_FIELDS = {
        'role',
        'is_admin',
        'is_superuser',
        'permissions',
        'account_balance',
        'credit_score',
        'password_hash',
        'password',
        'token',
        'api_key',
        'is_verified',
        'account_status',
    }

    @classmethod
    def filter_allowed_fields(cls, data):
        """Filter request data to only include allowed fields."""
        return {
            key: value
            for key, value in data.items()
            if key in cls.ALLOWED_UPDATE_FIELDS
        }

    @classmethod
    def detect_mass_assignment_attempt(cls, data):
        """Check if the request contains any sensitive fields."""
        sensitive_keys = cls.SENSITIVE_FIELDS.intersection(data.keys())
        return sensitive_keys

    @classmethod
    def secure_update(cls, user_data, request_data):
        """Securely update user data, preventing mass assignment."""
        # Check for mass assignment attempts
        sensitive = cls.detect_mass_assignment_attempt(request_data)
        if sensitive:
            raise ValueError(f"Mass assignment attempt detected: {sensitive}")

        # Only allow whitelisted fields
        allowed_data = cls.filter_allowed_fields(request_data)
        user_data.update(allowed_data)
        return user_data