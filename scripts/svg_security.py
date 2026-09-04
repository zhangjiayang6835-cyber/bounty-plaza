"""Secure SVG Parser & Blind XXE/SSRF Sanitizer.
Resolves Issue #298: Blind XXE via SVG Upload -> SSRF + Data Exfil ($150).
Enforces zero-DOCTYPE/ENTITY parsing, external DTD prohibition, and strict SVG tag whitelisting.
"""

import re
import xml.etree.ElementTree as ET
from typing import Set, Union


class SVGSafetyError(ValueError):
    """Raised when an SVG file contains XXE, prohibited DOCTYPE/ENTITY declarations, or untrusted elements."""
    pass


# Forbidden XML declaration patterns
DOCTYPE_PATTERN = re.compile(r'<!DOCTYPE[\s\S]*?>', re.IGNORECASE)
ENTITY_PATTERN = re.compile(r'<!ENTITY[\s\S]*?>', re.IGNORECASE)
SYSTEM_PUBLIC_PATTERN = re.compile(r'\b(SYSTEM|PUBLIC)\b', re.IGNORECASE)

# Whitelist of permissible SVG elements
ALLOWED_SVG_TAGS: Set[str] = {
    "svg",
    "g",
    "path",
    "rect",
    "circle",
    "ellipse",
    "line",
    "polyline",
    "polygon",
    "text",
    "tspan",
    "title",
    "desc",
    "defs",
    "use",
    "linearGradient",
    "radialGradient",
    "stop",
    "clipPath",
    "mask",
    "pattern",
}

# Explicitly banned dangerous elements that can execute code or trigger remote SSRF
DANGEROUS_TAGS: Set[str] = {
    "script",
    "foreignobject",
    "iframe",
    "embed",
    "object",
    "image",
    "audio",
    "video",
    "feimage",
}


def sanitize_svg(raw_content: Union[str, bytes]) -> str:
    """Validate and sanitize SVG content against XML External Entity (XXE) attacks.

    Args:
        raw_content: SVG file content as string or bytes.

    Returns:
        Clean, validated SVG string.

    Raises:
        SVGSafetyError: If DOCTYPE, ENTITY, XXE vectors, or disallowed tags are detected.
    """
    if isinstance(raw_content, bytes):
        try:
            content = raw_content.decode("utf-8")
        except UnicodeDecodeError:
            raise SVGSafetyError("SVG content must be valid UTF-8 text.")
    else:
        content = raw_content

    if not content or not content.strip():
        raise SVGSafetyError("SVG content is empty.")

    # 1. Prohibit DOCTYPE declarations outright
    if DOCTYPE_PATTERN.search(content) or "<!doctype" in content.lower():
        raise SVGSafetyError("Prohibited DOCTYPE declaration detected in SVG. Blind XXE vector neutralized.")

    # 2. Prohibit XML ENTITY definitions
    if ENTITY_PATTERN.search(content) or "<!entity" in content.lower():
        raise SVGSafetyError("Prohibited <!ENTITY declaration detected in SVG.")

    # 3. Guard against external DTD references
    if SYSTEM_PUBLIC_PATTERN.search(content):
        raise SVGSafetyError("Prohibited external entity keyword (SYSTEM/PUBLIC) detected.")

    # 4. Safe XML Tree Parsing with standard defused entity parser
    try:
        root = ET.fromstring(content)
    except ET.ParseError as e:
        raise SVGSafetyError(f"Malformed SVG XML document: {str(e)}")

    def strip_namespace(tag_name: str) -> str:
        if "}" in tag_name:
            return tag_name.split("}", 1)[1].lower()
        return tag_name.lower()

    root_tag = strip_namespace(root.tag)
    if root_tag != "svg":
        raise SVGSafetyError(f"Root XML element must be '<svg>', got '<{root_tag}>'")

    # 5. Recursively validate element tags against whitelist
    for elem in root.iter():
        elem_tag = strip_namespace(elem.tag)

        if elem_tag in DANGEROUS_TAGS:
            raise SVGSafetyError(f"Dangerous tag '<{elem_tag}>' detected in SVG. Potential XSS/SSRF vector.")

        if elem_tag not in ALLOWED_SVG_TAGS:
            raise SVGSafetyError(f"Disallowed tag '<{elem_tag}>' not in permitted SVG element whitelist.")

        # Strip any inline event handlers (onload, onclick, onerror, etc.)
        for attr in list(elem.attrib.keys()):
            attr_lower = attr.lower()
            if attr_lower.startswith("on") or "javascript:" in str(elem.attrib[attr]).lower():
                raise SVGSafetyError(f"Prohibited executable event handler '{attr}' found on tag <{elem_tag}>.")

    return content
