"""Comprehensive test suite for Django Hello World implementation (Issue #1584)."""

import io
import json
import os
from decimal import Decimal
import pytest

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "packages.bounty_django.settings")

import django

django.setup()

from django.apps import apps
from django.core.management import call_command
from django.test import Client, RequestFactory

from packages.bounty_django.apps.hello.models import GreetingRecord
from packages.bounty_django.apps.hello.services import (
    build_greeting,
    build_greeting_payload,
    get_supported_languages,
)
from packages.bounty_django.apps.hello.views import (
    hello_world_text,
    hello_world_html,
    hello_world_json,
    languages_list,
    bounty_settlement,
)
from packages.bounty_django.settlement import (
    calculate_settlement,
    get_contributor_ratio,
    validate_evm_address,
    validate_stellar_address,
    EVM_PAYOUT_ADDRESS,
    STELLAR_PAYOUT_ADDRESS,
)


@pytest.fixture(scope="session", autouse=True)
def setup_django_db():
    """Migrate database schema for the test session."""
    call_command("migrate", verbosity=0)


def test_django_app_registered() -> None:
    """Verify that hello application is successfully registered in Django registry."""
    app_config = apps.get_app_config("bounty_hello")
    assert app_config.name == "packages.bounty_django.apps.hello"
    assert app_config.verbose_name == "Bounty Plaza Hello World"


def test_service_build_greeting_default() -> None:
    """Verify default greeting generation in service layer."""
    greeting = build_greeting()
    assert greeting == "Hello, World!"


def test_service_build_greeting_multilingual() -> None:
    """Verify multilingual greeting phrases across diverse world languages."""
    assert build_greeting(target="世界", lang="zh") == "你好，世界!"
    assert build_greeting(target="Mundo", lang="es") == "Hola, Mundo!"
    assert build_greeting(target="Monde", lang="fr") == "Bonjour, Monde!"
    assert build_greeting(target="Welt", lang="de") == "Hallo, Welt!"
    assert build_greeting(target="世界", lang="ja") == "こんにちは，世界!"
    assert build_greeting(target="Мир", lang="ru") == "Привет, Мир!"


def test_service_build_greeting_shout_and_punct() -> None:
    """Verify shouting mode and custom punctuation formatting."""
    greeting = build_greeting(target="Swarm", lang="en", punct="!?", shout=True)
    assert greeting == "HELLO, SWARM!?"


def test_service_build_greeting_fallback_language() -> None:
    """Verify unknown language code falls back to English."""
    greeting = build_greeting(target="Universe", lang="unknown_lang")
    assert greeting == "Hello, Universe!"


def test_service_get_supported_languages() -> None:
    """Verify supported language registry returns populated mapping."""
    languages = get_supported_languages()
    assert len(languages) >= 20
    assert languages["en"] == "Hello"
    assert languages["zh"] == "你好"
    assert languages["es"] == "Hola"


def test_service_build_greeting_payload() -> None:
    """Verify structured metadata payload generation."""
    payload = build_greeting_payload(target="Plaza", lang="zh", punct="~", shout=False)
    assert payload["status"] == "success"
    assert payload["greeting"] == "你好"
    assert payload["target"] == "Plaza"
    assert payload["language"] == "zh"
    assert payload["punctuation"] == "~"
    assert payload["shout"] is False
    assert payload["message"] == "你好，Plaza~"


def test_view_hello_world_text() -> None:
    """Verify plain text HTTP response view."""
    factory = RequestFactory()
    request = factory.get("/")
    response = hello_world_text(request)
    assert response.status_code == 200
    assert response["Content-Type"] == "text/plain; charset=utf-8"
    assert response.content.decode("utf-8") == "Hello, World!"


def test_view_hello_world_text_custom_params() -> None:
    """Verify plain text view with query parameter customizations."""
    factory = RequestFactory()
    request = factory.get("/?target=Engineer&lang=es&punct=.")
    response = hello_world_text(request)
    assert response.status_code == 200
    assert response.content.decode("utf-8") == "Hola, Engineer."


def test_view_hello_world_html() -> None:
    """Verify HTML template rendering with accessible DOM structure."""
    factory = RequestFactory()
    request = factory.get("/hello/?target=Auditor&lang=en")
    response = hello_world_html(request)
    assert response.status_code == 200
    assert "text/html" in response["Content-Type"]
    html_content = response.content.decode("utf-8")
    assert "<!DOCTYPE html>" in html_content
    assert "Hello, Auditor!" in html_content
    assert "Bounty Plaza Django Hello World Engine" in html_content
    assert 'aria-label="Hello World Greeting Container"' in html_content


def test_view_hello_world_json() -> None:
    """Verify JSON API view returns valid JSON with all required keys."""
    factory = RequestFactory()
    request = factory.get("/api/hello/?target=Orchestrator&lang=fr")
    response = hello_world_json(request)
    assert response.status_code == 200
    data = json.loads(response.content.decode("utf-8"))
    assert data["status"] == "success"
    assert data["greeting"] == "Bonjour"
    assert data["target"] == "Orchestrator"
    assert data["language"] == "fr"
    assert data["message"] == "Bonjour, Orchestrator!"


def test_view_languages_list() -> None:
    """Verify JSON endpoint returning catalog of supported languages."""
    factory = RequestFactory()
    request = factory.get("/api/languages/")
    response = languages_list(request)
    assert response.status_code == 200
    data = json.loads(response.content.decode("utf-8"))
    assert data["status"] == "success"
    assert data["total_languages"] >= 20
    assert "en" in data["languages"]


def test_view_bounty_settlement_issue_1584() -> None:
    """Verify financial settlement API endpoint returns correct values for Issue #1584."""
    factory = RequestFactory()
    request = factory.get("/api/settlement/")
    response = bounty_settlement(request)
    assert response.status_code == 200
    data = json.loads(response.content.decode("utf-8"))
    assert data["status"] == "success"
    assert data["issue_id"] == 1584
    assert data["nominal_usd"] == "1500.00"
    assert data["total_coins"] == "1875.0000"
    assert data["contributor_ratio"] == "0.85"
    assert data["contributor_coins"] == "1593.7500"
    assert data["cash_payout_usd"] == "1147.50"
    assert data["platform_fee_usd"] == "352.50"
    assert data["effective_payout_percentage"] == "76.50"
    assert data["payout_routing"]["evm"] == EVM_PAYOUT_ADDRESS
    assert data["payout_routing"]["stellar"] == STELLAR_PAYOUT_ADDRESS


def test_client_http_endpoints_integration() -> None:
    """Verify end-to-end routing integration through Django test client."""
    client = Client()

    res_root = client.get("/")
    assert res_root.status_code == 200
    assert res_root.content.decode("utf-8") == "Hello, World!"

    res_html = client.get("/hello/")
    assert res_html.status_code == 200
    assert "Hello, World!" in res_html.content.decode("utf-8")

    res_api = client.get("/api/hello/")
    assert res_api.status_code == 200
    json_data = res_api.json()
    assert json_data["status"] == "success"

    res_settle = client.get("/api/settlement/")
    assert res_settle.status_code == 200
    settle_data = res_settle.json()
    assert settle_data["issue_id"] == 1584


def test_model_greeting_record_crud() -> None:
    """Verify creation, querying, and string representation of GreetingRecord."""
    GreetingRecord.objects.filter(recipient="Tester").delete()
    record = GreetingRecord.objects.create(
        recipient="Tester",
        message="Hello, Tester!",
        language="en",
        format_type="text",
    )
    assert record.id is not None
    assert record.recipient == "Tester"
    assert str(record) == "GreetingRecord(recipient=Tester, language=en)"

    queried = GreetingRecord.objects.filter(recipient="Tester").first()
    assert queried is not None
    assert queried.message == "Hello, Tester!"


def test_management_command_hello_stdout() -> None:
    """Verify Django management command executing to standard output."""
    out = io.StringIO()
    call_command("hello", stdout=out)
    output = out.getvalue().strip()
    assert output == "Hello, World!"


def test_management_command_hello_custom_flags() -> None:
    """Verify Django management command with custom target, language, and JSON formatting."""
    out = io.StringIO()
    call_command(
        "hello",
        "--target=Maintainer",
        "--lang=de",
        "--format=json",
        stdout=out,
    )
    output = out.getvalue().strip()
    data = json.loads(output)
    assert data["status"] == "success"
    assert data["target"] == "Maintainer"
    assert data["language"] == "de"
    assert data["message"] == "Hallo, Maintainer!"


def test_settlement_bracket_calculations() -> None:
    """Verify all tiers in the REWARD_POLICY tiered commission matrix."""
    assert get_contributor_ratio(Decimal("30.00")) == Decimal("0.95")
    assert get_contributor_ratio(Decimal("100.00")) == Decimal("0.92")
    assert get_contributor_ratio(Decimal("350.00")) == Decimal("0.90")
    assert get_contributor_ratio(Decimal("750.00")) == Decimal("0.87")
    assert get_contributor_ratio(Decimal("1500.00")) == Decimal("0.85")
    assert get_contributor_ratio(Decimal("2000.00")) == Decimal("0.85")


def test_settlement_exact_dollar_payouts() -> None:
    """Verify exact payout and coin numbers across standard benchmark bounties."""
    s30 = calculate_settlement(Decimal("30.00"))
    assert s30.total_coins == Decimal("37.5000")
    assert s30.contributor_coins == Decimal("35.6250")
    assert s30.cash_payout_usd == Decimal("25.65")

    s100 = calculate_settlement(Decimal("100.00"))
    assert s100.total_coins == Decimal("125.0000")
    assert s100.contributor_coins == Decimal("115.0000")
    assert s100.cash_payout_usd == Decimal("82.80")

    s1500 = calculate_settlement(Decimal("1500.00"))
    assert s1500.total_coins == Decimal("1875.0000")
    assert s1500.contributor_coins == Decimal("1593.7500")
    assert s1500.cash_payout_usd == Decimal("1147.50")
    assert s1500.platform_fee_usd == Decimal("352.50")
    assert s1500.effective_payout_percentage == Decimal("76.50")


def test_payout_address_validators() -> None:
    """Verify EVM and Stellar address validation functions."""
    assert validate_evm_address(EVM_PAYOUT_ADDRESS) is True
    assert validate_evm_address("0xInvalidLength") is False
    assert validate_evm_address("InvalidPrefix0xF46C9F6d70C50BF81ef3588AB523a90a594a2F89") is False

    assert validate_stellar_address(STELLAR_PAYOUT_ADDRESS) is True
    assert validate_stellar_address("GShort") is False
    assert validate_stellar_address("1InvalidStartGCL6OXAMLD75BMTINA6EMRUDWK5THQUSHMYNLSNBCJAPZJHNYJTUNIBC") is False
