"""Deterministic Unicode slugification toolkit conforming to RFC-3986 URL guidelines."""

from dataclasses import dataclass
import re
from typing import Any
import unicodedata


@dataclass(frozen=True)
class SlugOptions:
    """Configuration options for string slugification."""

    separator: str = "-"
    lowercase: bool = True
    strip_diacritics: bool = True
    strip_boundaries: bool = True


class Slugifier:
    """Transforms arbitrary string input into clean, URL-safe slugs."""

    def __init__(self, default_options: SlugOptions | None = None) -> None:
        """Initializes the Slugifier instance with baseline options."""
        self._default_options = default_options or SlugOptions()

    def slugify(self, value: Any, options: SlugOptions | None = None) -> str:
        """Converts an input string into a URL-friendly slug.

        Args:
            value: The string to slugify.
            options: Optional customization options overriding instance defaults.

        Returns:
            The normalized, URL-safe slug string.

        Raises:
            TypeError: If value is not an instance of str.
        """
        if not isinstance(value, str):
            raise TypeError("slugify expects a string")

        opts = options or self._default_options
        result = value

        if opts.strip_diacritics:
            normalized = unicodedata.normalize("NFKD", result)
            result = "".join(ch for ch in normalized if not unicodedata.combining(ch))

        if opts.lowercase:
            result = result.lower()

        escaped_sep = re.escape(opts.separator)
        result = re.sub(r"[^a-z0-9]+", opts.separator, result)

        if opts.strip_boundaries:
            boundary_pattern = rf"^{escaped_sep}+|{escaped_sep}+$"
            result = re.sub(boundary_pattern, "", result)

        return result

    @staticmethod
    def is_valid_slug(slug: str, separator: str = "-") -> bool:
        """Validates whether a string adheres to canonical slug rules.

        Args:
            slug: The slug candidate string to inspect.
            separator: The designated separator delimiter.

        Returns:
            True if the candidate contains only lower-case alphanumerics and single separators.
        """
        if not isinstance(slug, str):
            return False
        if not slug:
            return True
        escaped_sep = re.escape(separator)
        pattern = rf"^[a-z0-9]+({escaped_sep}[a-z0-9]+)*$"
        return bool(re.match(pattern, slug))


_DEFAULT_SLUGIFIER = Slugifier()


def slugify(value: Any, options: SlugOptions | None = None) -> str:
    """Convenience functional wrapper for standard slugification.

    Args:
        value: The string to slugify.
        options: Optional configuration overrides.

    Returns:
        The normalized URL slug.
    """
    return _DEFAULT_SLUGIFIER.slugify(value, options)
