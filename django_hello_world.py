#!/usr/bin/env python3
"""Standalone executable and entrypoint for Django Hello World operations."""

import argparse
import json
import os
import sys
from typing import Any

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "packages.bounty_django.settings")

import django

django.setup()

from django.test import RequestFactory
from packages.bounty_django.apps.hello.services import (
    build_greeting,
    build_greeting_payload,
    get_supported_languages,
)
from packages.bounty_django.apps.hello.views import (
    hello_world_text,
    hello_world_html,
    hello_world_json,
)
from packages.bounty_django.settlement import calculate_settlement


def get_greeting(
    target: str = "World",
    lang: str = "en",
    punct: str = "!",
    shout: bool = False,
) -> str:
    """Generate a Hello World greeting string via Django service layer."""
    greeting = build_greeting(target=target, lang=lang, punct=punct, shout=shout)
    return greeting


def get_greeting_data(
    target: str = "World",
    lang: str = "en",
    punct: str = "!",
    shout: bool = False,
) -> dict[str, Any]:
    """Generate a Hello World structured metadata payload."""
    payload = build_greeting_payload(
        target=target, lang=lang, punct=punct, shout=shout
    )
    return payload


def render_http_text(target: str = "World", lang: str = "en") -> str:
    """Simulate HTTP plain text response using Django RequestFactory."""
    factory = RequestFactory()
    request = factory.get("/", {"target": target, "lang": lang})
    response = hello_world_text(request)
    content = response.content.decode("utf-8")
    return content


def render_http_html(target: str = "World", lang: str = "en") -> str:
    """Simulate HTTP HTML template response using Django RequestFactory."""
    factory = RequestFactory()
    request = factory.get("/hello/", {"target": target, "lang": lang})
    response = hello_world_html(request)
    content = response.content.decode("utf-8")
    return content


def render_http_json(target: str = "World", lang: str = "en") -> dict[str, Any]:
    """Simulate HTTP JSON response using Django RequestFactory."""
    factory = RequestFactory()
    request = factory.get("/api/hello/", {"target": target, "lang": lang})
    response = hello_world_json(request)
    data = json.loads(response.content.decode("utf-8"))
    return data


def get_payout_details() -> dict[str, Any]:
    """Retrieve financial settlement breakdown for Issue #1584."""
    settlement = calculate_settlement()
    info = {
        "nominal_usd": str(settlement.nominal_usd),
        "total_coins": str(settlement.total_coins),
        "contributor_coins": str(settlement.contributor_coins),
        "cash_payout_usd": str(settlement.cash_payout_usd),
        "platform_fee_usd": str(settlement.platform_fee_usd),
        "evm": settlement.evm_address,
        "stellar": settlement.stellar_address,
    }
    return info


def build_parser() -> argparse.ArgumentParser:
    """Construct argument parser for CLI execution."""
    parser = argparse.ArgumentParser(
        description="Bounty Plaza Django Hello World Runner"
    )
    parser.add_argument(
        "--target",
        type=str,
        default="World",
        help="Target recipient name",
    )
    parser.add_argument(
        "--lang",
        type=str,
        default="en",
        help="Language code",
    )
    parser.add_argument(
        "--punct",
        type=str,
        default="!",
        help="Punctuation mark",
    )
    parser.add_argument(
        "--shout",
        action="store_true",
        help="Uppercase shouting mode",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["text", "json", "html", "settlement", "languages"],
        default="text",
        help="Output format",
    )
    return parser


def main() -> int:
    """CLI entrypoint for standalone hello world execution."""
    parser = build_parser()
    args = parser.parse_args()

    if args.format == "json":
        data = get_greeting_data(
            target=args.target,
            lang=args.lang,
            punct=args.punct,
            shout=args.shout,
        )
        sys.stdout.write(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    elif args.format == "html":
        rendered = render_http_html(target=args.target, lang=args.lang)
        sys.stdout.write(rendered + "\n")
    elif args.format == "settlement":
        payout = get_payout_details()
        sys.stdout.write(json.dumps(payout, indent=2) + "\n")
    elif args.format == "languages":
        languages = get_supported_languages()
        sys.stdout.write(json.dumps(languages, ensure_ascii=False, indent=2) + "\n")
    else:
        greeting = get_greeting(
            target=args.target,
            lang=args.lang,
            punct=args.punct,
            shout=args.shout,
        )
        sys.stdout.write(greeting + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
