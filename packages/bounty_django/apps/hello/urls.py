"""URL routing for hello application endpoints."""

from django.urls import path
from packages.bounty_django.apps.hello import views

app_name = "bounty_hello"

urlpatterns = [
    path("", views.hello_world_text, name="hello_text"),
    path("hello/", views.hello_world_html, name="hello_html"),
    path("api/hello/", views.hello_world_json, name="hello_json"),
    path("api/languages/", views.languages_list, name="languages_list"),
    path("api/settlement/", views.bounty_settlement, name="bounty_settlement"),
]
