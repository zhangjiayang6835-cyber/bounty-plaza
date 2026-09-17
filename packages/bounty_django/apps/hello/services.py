"""Service layer for hello world multilingual greeting generation."""

from typing import Any

GREETING_REGISTRY: dict[str, str] = {
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
    "el": "Γειά σας",
    "vi": "Xin chào",
    "id": "Halo",
    "sw": "Jambo",
}


def get_supported_languages() -> dict[str, str]:
    """Return dictionary of supported language codes and their base greetings."""
    languages_copy = dict(GREETING_REGISTRY)
    return languages_copy


def build_greeting(
    target: str = "World",
    lang: str = "en",
    punct: str = "!",
    shout: bool = False,
) -> str:
    """Build a formatted greeting string for the specified target and language."""
    clean_target = target.strip() or "World"
    clean_lang = lang.lower().strip()
    salutation = GREETING_REGISTRY.get(clean_lang, GREETING_REGISTRY["en"])

    if clean_lang in ("zh", "ja"):
        greeting_text = f"{salutation}，{clean_target}{punct}"
    else:
        greeting_text = f"{salutation}, {clean_target}{punct}"

    if shout:
        greeting_text = greeting_text.upper()

    return greeting_text


def build_greeting_payload(
    target: str = "World",
    lang: str = "en",
    punct: str = "!",
    shout: bool = False,
) -> dict[str, Any]:
    """Construct structured metadata payload representing the greeting."""
    message = build_greeting(target=target, lang=lang, punct=punct, shout=shout)
    payload = {
        "status": "success",
        "greeting": GREETING_REGISTRY.get(lang.lower().strip(), GREETING_REGISTRY["en"]),
        "target": target.strip() or "World",
        "language": lang.lower().strip(),
        "punctuation": punct,
        "shout": shout,
        "message": message,
    }
    return payload
