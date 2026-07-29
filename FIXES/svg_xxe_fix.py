from xml.etree import ElementTree as ET

def safe_parse_svg_xml(svg_content: str):
    """Parses SVG XML safely disabling external entity expansion to prevent Blind XXE (Issue #298)."""
    parser = ET.XMLParser(resolve_entities=False)
    try:
        return ET.fromstring(svg_content, parser=parser)
    except Exception as e:
        raise ValueError(f"XXE Protection Block: Invalid or malicious SVG content. {str(e)}")
