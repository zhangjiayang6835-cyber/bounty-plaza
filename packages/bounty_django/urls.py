"""Root URL configuration for Bounty Plaza Django application."""

from django.urls import path, include

urlpatterns = [
    path("", include("packages.bounty_django.apps.hello.urls")),
]
