"""HTTP and JSON API view controllers for hello world endpoints."""

from typing import Any
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.db import DatabaseError

from packages.bounty_django.apps.hello.models import GreetingRecord
from packages.bounty_django.apps.hello.services import (
    build_greeting,
    build_greeting_payload,
    get_supported_languages,
)
from packages.bounty_django.settlement import calculate_settlement


def extract_greeting_params(request: HttpRequest) -> dict[str, Any]:
    """Extract and sanitize query parameters from HTTP request."""
    target = request.GET.get("target", "World").strip() or "World"
    lang = request.GET.get("lang", "en").strip().lower() or "en"
    punct = request.GET.get("punct", "!").strip() or "!"
    shout_val = request.GET.get("shout", "").strip().lower()
    shout = shout_val in ("1", "true", "yes", "on")
    params = {
        "target": target,
        "lang": lang,
        "punct": punct,
        "shout": shout,
    }
    return params


def record_greeting_audit(recipient: str, message: str, language: str, format_type: str) -> None:
    """Safely persist greeting record to database if storage is available."""
    try:
        GreetingRecord.objects.create(
            recipient=recipient,
            message=message,
            language=language,
            format_type=format_type,
        )
    except (DatabaseError, RuntimeError):
        pass


def hello_world_text(request: HttpRequest) -> HttpResponse:
    """Return plain-text HTTP response with hello world greeting."""
    params = extract_greeting_params(request)
    message = build_greeting(
        target=params["target"],
        lang=params["lang"],
        punct=params["punct"],
        shout=params["shout"],
    )
    record_greeting_audit(
        recipient=params["target"],
        message=message,
        language=params["lang"],
        format_type="text",
    )
    response = HttpResponse(message, content_type="text/plain; charset=utf-8")
    return response


def hello_world_html(request: HttpRequest) -> HttpResponse:
    """Render HTML greeting template with context and styling."""
    params = extract_greeting_params(request)
    payload = build_greeting_payload(
        target=params["target"],
        lang=params["lang"],
        punct=params["punct"],
        shout=params["shout"],
    )
    record_greeting_audit(
        recipient=params["target"],
        message=payload["message"],
        language=params["lang"],
        format_type="html",
    )
    response = render(request, "hello/index.html", payload)
    return response


def hello_world_json(request: HttpRequest) -> JsonResponse:
    """Return structured JSON API response with greeting and metadata."""
    params = extract_greeting_params(request)
    payload = build_greeting_payload(
        target=params["target"],
        lang=params["lang"],
        punct=params["punct"],
        shout=params["shout"],
    )
    record_greeting_audit(
        recipient=params["target"],
        message=payload["message"],
        language=params["lang"],
        format_type="json",
    )
    response = JsonResponse(payload)
    return response


def languages_list(_request: HttpRequest) -> JsonResponse:
    """Return JSON mapping of all supported language codes and phrases."""
    languages = get_supported_languages()
    data = {
        "status": "success",
        "total_languages": len(languages),
        "languages": languages,
    }
    response = JsonResponse(data)
    return response


def bounty_settlement(_request: HttpRequest) -> JsonResponse:
    """Return financial settlement breakdown and payout routing for Issue #1584."""
    settlement = calculate_settlement()
    data = {
        "status": "success",
        "issue_id": 1584,
        "nominal_usd": str(settlement.nominal_usd),
        "total_coins": str(settlement.total_coins),
        "contributor_ratio": str(settlement.contributor_ratio),
        "contributor_coins": str(settlement.contributor_coins),
        "cash_payout_usd": str(settlement.cash_payout_usd),
        "platform_fee_usd": str(settlement.platform_fee_usd),
        "effective_payout_percentage": str(settlement.effective_payout_percentage),
        "payout_routing": {
            "evm": settlement.evm_address,
            "stellar": settlement.stellar_address,
        },
    }
    response = JsonResponse(data)
    return response
