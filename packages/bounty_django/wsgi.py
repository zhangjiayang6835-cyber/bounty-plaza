"""WSGI config for Bounty Plaza Django application."""

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "packages.bounty_django.settings")

application = get_wsgi_application()
