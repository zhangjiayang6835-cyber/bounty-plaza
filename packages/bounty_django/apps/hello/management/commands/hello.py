"""Django management command to generate hello world greetings via CLI."""

import json
from argparse import ArgumentParser
from django.core.management.base import BaseCommand
from packages.bounty_django.apps.hello.models import GreetingRecord
from packages.bounty_django.apps.hello.services import (
    build_greeting,
    build_greeting_payload,
)


class Command(BaseCommand):
    """Management command outputting formatted hello world greetings."""

    help = "Generate multilingual Hello World greetings"

    def add_arguments(self, parser: ArgumentParser) -> None:
        """Register CLI flags and parameters."""
        parser.add_argument(
            "--target",
            type=str,
            default="World",
            help="Target recipient name for greeting",
        )
        parser.add_argument(
            "--lang",
            type=str,
            default="en",
            help="ISO 639-1 language code (e.g. en, zh, es, fr)",
        )
        parser.add_argument(
            "--punct",
            type=str,
            default="!",
            help="Trailing punctuation character",
        )
        parser.add_argument(
            "--shout",
            action="store_true",
            help="Transform greeting into uppercase shouting mode",
        )
        parser.add_argument(
            "--format",
            type=str,
            choices=["text", "json"],
            default="text",
            help="Output formatting serialization type",
        )
        parser.add_argument(
            "--audit",
            action="store_true",
            help="Persist greeting to database audit log",
        )

    def handle(self, *args, **options) -> None:
        """Execute command logic with provided arguments."""
        target = options["target"]
        lang = options["lang"]
        punct = options["punct"]
        shout = options["shout"]
        format_type = options["format"]
        audit = options["audit"]

        if format_type == "json":
            payload = build_greeting_payload(
                target=target, lang=lang, punct=punct, shout=shout
            )
            output = json.dumps(payload, ensure_ascii=False, indent=2)
            self.stdout.write(output)
            message = payload["message"]
        else:
            message = build_greeting(
                target=target, lang=lang, punct=punct, shout=shout
            )
            self.stdout.write(message)

        if audit:
            GreetingRecord.objects.create(
                recipient=target,
                message=message,
                language=lang,
                format_type=format_type,
            )
