# fix_web_cache_deception.py
from flask import request, Response
import re

class CacheProtectionMiddleware:
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        # Obtener la ruta y el tipo de contenido
        path = environ.get('PATH_INFO', '')
        content_type = environ.get('CONTENT_TYPE', '')

        # 1. No cachear URLs con parámetros sensibles
        if '?' in path or '&' in path:
            # Añadir headers de no-cache
            return self._add_no_cache_headers(environ, start_response)

        # 2. Configurar caché basada en Content-Type
        if content_type and 'text/html' in content_type:
            # No cachear páginas HTML
            return self._add_no_cache_headers(environ, start_response)

        # 3. Usar X-Content-Type-Options
        def _start_response(status, headers, exc_info=None):
            headers.append(('X-Content-Type-Options', 'nosniff'))
            # Añadir Vary: Accept-Encoding para evitar cachés incorrectos
            headers.append(('Vary', 'Accept-Encoding'))
            return start_response(status, headers, exc_info)

        return self.app(environ, _start_response)

    def _add_no_cache_headers(self, environ, start_response):
        def _start_response(status, headers, exc_info=None):
            headers.append(('Cache-Control', 'no-store, no-cache, must-revalidate'))
            headers.append(('Pragma', 'no-cache'))
            headers.append(('Expires', '0'))
            return start_response(status, headers, exc_info)
        return self.app(environ, _start_response)