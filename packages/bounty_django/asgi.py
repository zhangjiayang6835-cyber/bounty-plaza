"""ASGI config for Bounty Plaza Django application."""

import os
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "packages.bounty_django.settings")

application = get_asgi_application()
