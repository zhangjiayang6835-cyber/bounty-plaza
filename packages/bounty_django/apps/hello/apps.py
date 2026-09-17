"""Application configuration for the hello world app."""

from django.apps import AppConfig


class HelloConfig(AppConfig):
    """AppConfig definition for hello app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "packages.bounty_django.apps.hello"
    label = "bounty_hello"
    verbose_name = "Bounty Plaza Hello World"
