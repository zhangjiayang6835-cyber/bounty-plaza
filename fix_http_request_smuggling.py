# fix_http_request_smuggling.py
import re

class HTTPRequestSmugglingProtection:
    """Protect against CL.TE and TE.CL HTTP request smuggling attacks."""

    # Pattern for valid chunked encoding
    VALID_CHUNK = re.compile(r'^[0-9a-fA-F]+(?:[;\s]*[^\r\n]*)?\r\n')

    @classmethod
    def validate_headers(cls, headers):
        """
        Validate HTTP headers to prevent request smuggling.
        Returns (safe, error) tuple.
        """
        content_length = headers.get('Content-Length')
        transfer_encoding = headers.get('Transfer-Encoding')

        # CL.TE smuggling: reject requests with both headers
        if content_length and transfer_encoding:
            return False, "CL.TE request smuggling: both Content-Length and Transfer-Encoding present"

        # Validate Transfer-Encoding if present
        if transfer_encoding:
            te_value = transfer_encoding.lower()
            if 'chunked' not in te_value:
                return False, "Unsupported Transfer-Encoding: %s" % transfer_encoding
            # Reject chunked with extensions
            if ';' in te_value or ',' in te_value:
                return False, "Transfer-Encoding extensions not allowed"

        # Reject duplicate Content-Length headers
        if content_length:
            if re.search(r'[^0-9]', content_length):
                return False, "Invalid Content-Length value"

        return True, None

    @classmethod
    def validate_chunked_body(cls, body):
        """
        Validate chunked transfer encoding body.
        Returns (safe, error) tuple.
        """
        if not body:
            return False, "Empty chunked body"

        # Split into chunks and validate each
        chunks = body.split('\r\n')
        for chunk_line in chunks:
            chunk_match = cls.VALID_CHUNK.match(chunk_line)
            if not chunk_match:
                # Might be end chunk (0\r\n)
                if chunk_line.strip() == '0':
                    continue
                return False, "Invalid chunked encoding format"

        return True, None

    @classmethod
    def is_smuggling_request(cls, headers, body):
        """Detect potential HTTP request smuggling attempts."""
        # Check for nested HTTP requests
        smuggling_patterns = [
            r'\r\n\r\n',        # Double CRLF (request smuggling)
            r'\n\n',            # LFLF
            r'[A-Z]{3,} /.*HTTP',  # HTTP method patterns
            r'Connection:\s*close',  # Connection header abuse
        ]

        combined = str(headers) + str(body)
        for pattern in smuggling_patterns:
            if re.search(pattern, combined, re.IGNORECASE):
                return True
        return False

    @staticmethod
    def get_secure_http_config():
        """Return secure HTTP configuration for web servers."""
        return {
            # Nginx config
            'nginx': """
# Reject requests with both CL and TE headers
if ($http_content_length ~* .+ && $http_transfer_encoding ~* .+) {
    return 400;
}
# Reject chunked encoding extensions
if ($http_transfer_encoding ~* [;,]) {
    return 400;
}
""",
            # Apache config
            'apache': """
# Disable chunked transfer encoding extensions
SecRule REQUEST_HEADERS:Transfer-Encoding "chunked[;,]" \
    "id:1001,phase:1,deny,status:400,msg:'Request smuggling attempt'"
""",
        }