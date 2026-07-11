# fix_ssti.py
from jinja2 import Template

def render_email_template(user_input):
    """
    Renderiza una plantilla de correo de forma segura.
    Usa plantillas precompiladas y solo reemplaza variables.
    """
    template = Template("Hello {{ name }}")
    output = template.render(name=user_input)
    return output