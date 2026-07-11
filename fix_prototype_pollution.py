# fix_prototype_pollution.py
"""
Server-Side Prototype Pollution Protection.

Prototype pollution attacks modify Object.prototype to affect all objects in the
JavaScript runtime. Common attack patterns:
  - {"__proto__": {"polluted": "value"}}
  - {"constructor": {"prototype": {"polluted": "value"}}}
  - {"prototype": {"polluted": "value"}}

Python implementation for Flask/FastAPI middleware.
"""

class PrototypePollutionProtection:
    """Protect against server-side prototype pollution in Python/JS applications."""

    # Dangerous keys that should never be set from user input
    DANGEROUS_KEYS = {
        '__proto__',
        'prototype',
        'constructor',
        '__class__',
        '__globals__',
        '__builtins__',
        '__bases__',
        '__mro__',
        '__subclasses__',
        'toString',
        'valueOf',
    }

    @classmethod
    def is_dangerous_key(cls, key):
        """Check if a key is dangerous for prototype pollution."""
        return key in cls.DANGEROUS_KEYS

    @classmethod
    def sanitize_dict(cls, data, max_depth=10):
        """
        Recursively sanitize a dictionary, removing dangerous keys.
        Returns a clean dictionary safe for merge operations.
        """
        if max_depth <= 0:
            return {}
        if not isinstance(data, dict):
            return data

        result = {}
        for key, value in data.items():
            if cls.is_dangerous_key(key):
                continue
            # Recursively sanitize nested dicts
            if isinstance(value, dict):
                result[key] = cls.sanitize_dict(value, max_depth - 1)
            elif isinstance(value, list):
                result[key] = [
                    cls.sanitize_dict(item, max_depth - 1) if isinstance(item, dict)
                    else item for item in value
                ]
            else:
                result[key] = value

        return result

    @classmethod
    def safe_merge(cls, target, source):
        """
        Safely merge source into target without prototype pollution.
        """
        sanitized = cls.sanitize_dict(source)
        for key, value in sanitized.items():
            if isinstance(value, dict) and isinstance(target.get(key), dict):
                cls.safe_merge(target[key], value)
            else:
                target[key] = value
        return target

    @staticmethod
    def safe_deep_merge(target, source):
        """Deep merge two dictionaries safely."""
        import copy
        result = copy.deepcopy(target)
        return PrototypePollutionProtection.safe_merge(result, source)

    @classmethod
    def create_prototype_free_dict(cls):
        """Create a dictionary with no prototype (like Object.create(null))."""
        # In Python, all dicts are prototype-free by default
        return {}