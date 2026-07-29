import re

def render_email_template_safely(template_string: str, context: dict) -> str:
    """Safely renders email templates preventing Jinja2 SSTI Sandbox Escape RCE (Issue #284)."""
    # Reject dangerous attribute navigation patterns (__class__, __mro__, __subclasses__, __globals__)
    dangerous_patterns = [r'__class__', r'__mro__', r'__subclasses__', r'__globals__', r'__builtins__']
    
    for pattern in dangerous_patterns:
        if re.search(pattern, template_string, re.IGNORECASE):
            raise ValueError(f"SSTI Security Block: Forbidden template pattern detected '{pattern}'.")

    # Perform safe pre-compiled variable substitution without exposing template engine internals
    rendered = template_string
    for key, value in context.items():
        placeholder = "{{" + key + "}}"
        rendered = rendered.replace(placeholder, str(value))

    return rendered
