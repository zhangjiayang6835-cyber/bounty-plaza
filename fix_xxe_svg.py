# fix_xxe_svg.py
import xml.etree.ElementTree as ET
from lxml import etree

class XXESVGProtection:
    """Protect against Blind XXE in SVG upload."""

    # Allowed SVG elements and attributes
    ALLOWED_ELEMENTS = {
        'svg', 'g', 'path', 'circle', 'rect', 'line', 'polygon',
        'ellipse', 'text', 'use', 'defs', 'style', 'symbol',
        'linearGradient', 'radialGradient', 'stop',
    }

    ALLOWED_ATTRIBUTES = {
        'x', 'y', 'width', 'height', 'cx', 'cy', 'r', 'rx', 'ry',
        'd', 'points', 'fill', 'stroke', 'stroke-width', 'opacity',
        'transform', 'id', 'class', 'style', 'viewBox',
        'x1', 'y1', 'x2', 'y2', 'href', 'xlink:href',
    }

    @staticmethod
    def create_secure_parser():
        """Create an XML parser with XXE protections enabled."""
        # Lxml parser with safe defaults
        parser = etree.XMLParser(
            resolve_entities=False,   # Disable entity resolution
            no_network=True,          # Disable network access
            remove_blank_text=True,
            recover=False,            # Fail on errors
        )
        return parser

    @staticmethod
    def validate_svg(svg_content):
        """
        Validate SVG content and check for XXE attacks.
        Returns True if safe, raises ValueError if malicious.
        """
        if not svg_content:
            raise ValueError("Empty SVG content")

        # Check for common XXE patterns in raw text
        xxe_patterns = [
            '<?xml',
            '<!DOCTYPE',
            '<!ENTITY',
            '<!ATTLIST',
            'SYSTEM',
            'PUBLIC',
            'file://',
            'ftp://',
            'expect://',
        ]

        for pattern in xxe_patterns:
            if pattern.lower() in svg_content.lower():
                raise ValueError(f"XXE pattern detected: {pattern}")

        # Parse with secure parser
        try:
            parser = XXESVGProtection.create_secure_parser()
            tree = etree.fromstring(svg_content, parser)
        except etree.XMLSyntaxError:
            raise ValueError("Invalid XML/SVG syntax")

        # Validate elements
        def check_element(elem):
            tag = elem.tag.lower().split('}')[-1]  # Handle namespace
            if tag not in XXESVGProtection.ALLOWED_ELEMENTS:
                raise ValueError(f"Disallowed SVG element: {tag}")
            for child in elem:
                check_element(child)

        check_element(tree)
        return True

    @staticmethod
    def safe_parse_svg(svg_content):
        """Parse SVG content safely, stripping dangerous content."""
        XXESVGProtection.validate_svg(svg_content)
        parser = XXESVGProtection.create_secure_parser()
        return etree.fromstring(svg_content, parser)