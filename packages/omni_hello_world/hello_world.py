"""
Core implementation of the OmniBlocks Hello World multilingual engine.
"""

import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

DEFAULT_LANGUAGE = "en"
DEFAULT_TARGET = "World"
DEFAULT_PUNCTUATION = "!"


class FormatType(str, Enum):
    """Supported output serialization formats."""

    TEXT = "text"
    JSON = "json"
    MARKDOWN = "markdown"
    HTML = "html"
    ANSI = "ansi"
    ASCII_BANNER = "ascii_banner"


FORMATS = {fmt.value: fmt.value for fmt in FormatType}

GREETINGS: Dict[str, str] = {
    "en": "Hello",
    "zh": "你好",
    "es": "Hola",
    "fr": "Bonjour",
    "de": "Hallo",
    "ja": "こんにちは",
    "ko": "안녕하세요",
    "ru": "Привет",
    "ar": "مرحبا",
    "hi": "नमस्ते",
    "pt": "Olá",
    "it": "Ciao",
    "nl": "Hallo",
    "tr": "Merhaba",
    "pl": "Cześć",
    "sv": "Hej",
    "el": "Γεια σας",
    "vi": "Xin chào",
    "id": "Halo",
    "sw": "Jambo",
}


@dataclass(frozen=True)
class GreetingResult:
    """Structured representation of a generated greeting."""

    greeting: str
    target: str
    punctuation: str
    message: str
    language: str
    shout: bool

    def to_dict(self) -> Dict[str, Any]:
        """Convert the result into a plain dictionary."""
        return {
            "greeting": self.greeting,
            "target": self.target,
            "punctuation": self.punctuation,
            "message": self.message,
            "language": self.language,
            "shout": self.shout,
        }

    def to_json(self) -> str:
        """Serialize the greeting result to formatted JSON string."""
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)


class HelloWorld:
    """Enterprise Hello World engine with multilingual and multi-format capabilities."""

    def __init__(
        self,
        default_language: str = DEFAULT_LANGUAGE,
        default_target: str = DEFAULT_TARGET,
        custom_greetings: Optional[Dict[str, str]] = None,
    ) -> None:
        """Initialize the engine with customizable defaults."""
        self.default_language = default_language
        self.default_target = default_target
        self.languages: Dict[str, str] = dict(GREETINGS)
        if custom_greetings:
            self.languages.update(custom_greetings)

    def get_supported_languages(self) -> List[str]:
        """Return the sorted list of supported ISO language codes."""
        return sorted(list(self.languages.keys()))

    def register_language(self, code: str, greeting: str) -> None:
        """Register a new language code and its corresponding greeting."""
        if not code or not isinstance(code, str):
            raise TypeError("Language code must be a non-empty string")
        if not greeting or not isinstance(greeting, str):
            raise TypeError("Greeting must be a non-empty string")
        self.languages[code.lower()] = greeting

    @staticmethod
    def render_ascii_banner(text: str) -> str:
        """Render a text message centered within an ASCII box banner."""
        pad = 2
        inner_width = len(text) + pad * 2
        border_h = "-" * inner_width
        spaces = " " * inner_width
        pad_space = " " * pad
        top = f"+{border_h}+"
        empty = f"|{spaces}|"
        middle = f"|{pad_space}{text}{pad_space}|"
        lines = [top, empty, middle, empty, top]
        return "\n".join(lines)

    def generate(
        self,
        target: Optional[str] = None,
        language: Optional[str] = None,
        punctuation: Optional[str] = None,
        shout: bool = False,
    ) -> GreetingResult:
        """Generate structured greeting data."""
        lang_code = (language or self.default_language).lower()
        greeting_word = self.languages.get(lang_code, self.languages[DEFAULT_LANGUAGE])

        effective_target = self.default_target
        if target is not None and str(target).strip():
            effective_target = str(target).strip()

        effective_punctuation = DEFAULT_PUNCTUATION
        if punctuation is not None:
            effective_punctuation = str(punctuation)

        message = f"{greeting_word}, {effective_target}{effective_punctuation}"
        if shout:
            message = message.upper()

        return GreetingResult(
            greeting=greeting_word,
            target=effective_target,
            punctuation=effective_punctuation,
            message=message,
            language=lang_code,
            shout=shout,
        )

    def greet(
        self,
        target: Optional[str] = None,
        language: Optional[str] = None,
        punctuation: Optional[str] = None,
        shout: bool = False,
        format_type: str = FormatType.TEXT.value,
    ) -> str:
        """Generate formatted greeting output string."""
        result = self.generate(
            target=target,
            language=language,
            punctuation=punctuation,
            shout=shout,
        )

        fmt = format_type.lower()
        if fmt == FormatType.JSON.value:
            return result.to_json()
        if fmt == FormatType.MARKDOWN.value:
            return f"# {result.message}"
        if fmt == FormatType.HTML.value:
            return f'<div class="greeting"><h1>{result.message}</h1></div>'
        if fmt == FormatType.ANSI.value:
            return f"\x1b[1;32m{result.message}\x1b[0m"
        if fmt == FormatType.ASCII_BANNER.value:
            return self.render_ascii_banner(result.message)
        return result.message


_DEFAULT_INSTANCE = HelloWorld()


def greet(
    target: Optional[str] = None,
    language: Optional[str] = None,
    punctuation: Optional[str] = None,
    shout: bool = False,
    format_type: str = FormatType.TEXT.value,
) -> str:
    """Convenience functional helper for default greeting generation."""
    return _DEFAULT_INSTANCE.greet(
        target=target,
        language=language,
        punctuation=punctuation,
        shout=shout,
        format_type=format_type,
    )
