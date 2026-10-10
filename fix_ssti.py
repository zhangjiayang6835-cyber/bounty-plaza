# fix_ssti.py
from jinja2 import Template, Environment, BaseLoader, SandboxedEnvironment

class SSTIProtection:
    """Protect against Server-Side Template Injection in email templates."""

    # Precompiled safe template
    SAFE_TEMPLATE_STR = "Hello {{ name }}"

    def __init__(self):
        self.env = SandboxedEnvironment(loader=BaseLoader(), autoescape=True)
        self.template = self.env.from_string(self.SAFE_TEMPLATE_STR)

    def render(self, user_input):
        """
        Render a template securely using a precompiled template.
        User input is only used as a variable value, never as template structure.
        """
        # Sanitize user input to prevent template injection
        safe_input = str(user_input).replace('{{', '').replace('{%', '').replace('{#', '')
        return self.template.render(name=safe_input)

    @staticmethod
    def render_email_template(user_input):
        """
        Render an email template securely.
        Uses a precompiled template and only replaces variables.
        """
        template = Template("Hello {{ name }}")
        # Sanitize input to prevent SSTI
        safe_name = str(user_input).replace('{{', '').replace('{%', '').replace('{#', '')
        return template.render(name=safe_name)