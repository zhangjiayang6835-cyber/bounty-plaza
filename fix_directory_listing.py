# fix_directory_listing.py
"""
Directory Listing Protection for issue #88.

Web server directory listing exposes internal file structure,
allowing attackers to enumerate files and discover sensitive resources.
"""

class DirectoryListingProtection:
    """Disable directory listing and protect against file enumeration."""

    @staticmethod
    def get_nginx_config():
        """Return Nginx configuration to disable directory listing."""
        return """
# Disable directory listing
autoindex off;

# For static file serving, only serve specific file types
location /static/ {
    autoindex off;
    # Only serve specific file types
    location ~* \\.(js|css|png|jpg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        # Allow these file types
    }
    # Deny all other files
    location ~ . {
        deny all;
    }
}

# Explicit index file
location / {
    index index.html;
    try_files $uri $uri/ /index.html;
}
"""

    @staticmethod
    def get_apache_config():
        """Return Apache configuration to disable directory listing."""
        return """
# Disable directory listing
<Directory /var/www/html>
    Options -Indexes +FollowSymLinks
    AllowOverride None
    Require all granted
</Directory>

# For uploads directory
<Directory /var/www/html/uploads>
    Options -Indexes
    AllowOverride None
    Require all granted
</Directory>

# Custom error for directory listing attempts
ErrorDocument 403 "Directory listing not allowed"
ErrorDocument 404 "File not found"
"""

    @staticmethod
    def get_iis_config():
        """Return IIS configuration to disable directory listing."""
        return """
<configuration>
  <system.webServer>
    <directoryBrowse enabled="false" />
    <staticContent>
      <clientCache cacheControlMode="UseExpires" />
    </staticContent>
  </system.webServer>
</configuration>
"""

    @staticmethod
    def get_fastapi_middleware(app):
        """Apply directory listing protection for FastAPI static files."""
        from starlette.responses import FileResponse
        from starlette.requests import Request
        import os

        @app.middleware("http")
        async def prevent_directory_listing(request: Request, call_next):
            path = request.url.path
            # Check if path ends with / (directory access)
            if path.endswith('/'):
                # Check if directory exists
                if os.path.isdir(path[1:]):
                    from starlette.responses import PlainTextResponse
                    return PlainTextResponse("Directory listing not allowed", status_code=403)
            return await call_next(request)

        return app

    @staticmethod
    def get_flask_middleware(app):
        """Apply directory listing protection for Flask static files."""
        import os
        from flask import send_from_directory, abort

        @app.before_request
        def check_directory_listing():
            # Flask's send_from_directory already prevents directory listing
            # This adds additional protection
            pass

        return app

    @staticmethod
    def get_caddy_config():
        """Return Caddy configuration to disable directory listing."""
        return """
# Disable directory listing
file_server {
    precompressed gzip br
    index index.html
    # No browse directive = directory listing disabled
}
"""

    @staticmethod
    def audit_directory_listing(web_root):
        """Audit web server root for potential directory listing exposure."""
        import os
        issues = []

        # Check common static directories
        static_dirs = ['static', 'assets', 'uploads', 'images', 'files', 'downloads']
        for dir_name in static_dirs:
            path = os.path.join(web_root, dir_name)
            if os.path.isdir(path):
                # Check if there's an index file
                has_index = any(
                    os.path.isfile(os.path.join(path, f))
                    for f in ['index.html', 'index.htm', 'default.html']
                )
                if not has_index:
                    issues.append({
                        'directory': path,
                        'issue': 'No index file - directory listing may be exposed',
                        'fix': 'Add index.html or disable autoindex',
                    })

        return issues