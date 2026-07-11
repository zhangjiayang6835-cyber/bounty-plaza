# fix_http_parameter_pollution.py
"""
HTTP Parameter Pollution Protection.

HTTP Parameter Pollution (HPP) occurs when an attacker submits
duplicate query parameters to manipulate application behavior.

Example attack:
  ?role=user&role=admin  → Application may use last value
"""

from urllib.parse import parse_qs, parse_qsl

class HTTPParameterPollutionProtection:
    """Protect against HTTP Parameter Pollution attacks."""

    @staticmethod
    def detect_duplicate_parameters(query_string):
        """
        Detect if the query string contains duplicate parameters.
        Returns (has_duplicates, duplicate_params) tuple.
        """
        if not query_string:
            return False, []

        # Parse all parameters with their values
        params = parse_qs(query_string, keep_blank_values=True)

        # Check for duplicates (params with more than one value)
        duplicates = {k: v for k, v in params.items() if len(v) > 1}

        return bool(duplicates), list(duplicates.keys())

    @staticmethod
    def deduplicate_parameters(query_string, strategy='first'):
        """
        Deduplicate query parameters.
        Strategy: 'first' (keep first value) or 'last' (keep last value).
        """
        if not query_string:
            return ''

        # Parse all parameters
        params = parse_qs(query_string, keep_blank_values=True)

        # Build deduplicated query string
        deduplicated = {}
        for key, values in params.items():
            if strategy == 'first':
                deduplicated[key] = values[0]
            else:
                deduplicated[key] = values[-1]

        # Rebuild query string
        items = ['%s=%s' % (k, v) for k, v in deduplicated.items()]
        return '&'.join(items)

    @staticmethod
    def validate_parameter_count(query_string, max_params=50):
        """
        Validate that the number of parameters doesn't exceed maximum.
        Returns (valid, param_count) tuple.
        """
        if not query_string:
            return True, 0

        params = parse_qsl(query_string, keep_blank_values=True)
        count = len(params)

        if count > max_params:
            return False, count

        return True, count

    @staticmethod
    def safe_get_parameter(request, name):
        """
        Safely get a single parameter from the request.
        Uses first value and rejects duplicates.
        """
        # Get all values for this parameter
        all_values = request.args.getlist(name)

        if not all_values:
            return None

        if len(all_values) > 1:
            raise ValueError(
                "HTTP Parameter Pollution detected: duplicate parameter '%s'" % name
            )

        return all_values[0]

    @staticmethod
    def is_polluted_request(request):
        """Check if the request has duplicate parameters."""
        has_duplicates, duplicate_params = HTTPParameterPollutionProtection.detect_duplicate_parameters(
            request.query_string.decode() if hasattr(request, 'query_string') else ''
        )
        return has_duplicates, duplicate_params

    @staticmethod
    def get_security_config():
        """Return HPP security configuration."""
        return {
            'reject_duplicates': True,
            'deduplication_strategy': 'first',
            'max_parameters': 50,
            'log_pollution_attempts': True,
        }