# fix_idor_graphql.py
from functools import wraps

class GraphQLIDORProtection:
    """Protect against Insecure Direct Object Reference in GraphQL queries."""

    @staticmethod
    def authorize_resource_access(resolver_func):
        """Decorator: authorize access to a resource based on user context."""
        @wraps(resolver_func)
        def wrapper(obj, info, **kwargs):
            user = info.context.get('user')
            if not user:
                raise PermissionError("Authentication required")

            # Get the resource ID from kwargs
            resource_id = kwargs.get('id') or kwargs.get('userId') or kwargs.get('email')

            # Check if user has access to this resource
            user_id = user.get('id')
            user_role = user.get('role', 'user')

            # Admin can access any resource
            if user_role == 'admin':
                return resolver_func(obj, info, **kwargs)

            # Regular users can only access their own resources
            if resource_id and str(resource_id) != str(user_id):
                # Check if the resource belongs to the user through other means
                owner_id = kwargs.get('ownerId')
                if owner_id and str(owner_id) != str(user_id):
                    raise PermissionError("Access denied: cannot access other users' data")

            return resolver_func(obj, info, **kwargs)
        return wrapper

    @staticmethod
    def secure_batch_resolver(resolver_func):
        """Decorator: secure batch resolver with access control."""
        @wraps(resolver_func)
        def wrapper(keys, info):
            user = info.context.get('user')
            if not user:
                raise PermissionError("Authentication required")

            # Filter keys to only include authorized ones
            user_id = str(user.get('id'))
            user_role = user.get('role', 'user')

            if user_role == 'admin':
                return resolver_func(keys, info)

            # Non-admin: only access own data
            authorized_keys = [k for k in keys if str(k) == user_id]
            return resolver_func(authorized_keys, info)
        return wrapper