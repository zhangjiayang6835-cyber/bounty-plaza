import pytest
from scripts.safe_template_engine import (
    PrecompiledTemplate,
    SafeTemplateRegistry,
    TemplateSecurityError,
)


def test_safe_template_renders_plain_variables():
    tmpl = PrecompiledTemplate("welcome", "Hello {{ username }}, your ticket #{{ ticket_id }} is ready.")
    out = tmpl.render({"username": "Alice", "ticket_id": 9812})
    assert out == "Hello Alice, your ticket #9812 is ready."


def test_safe_template_blocks_introspection_in_expression():
    # Introspection payload attempting sandbox escape
    ssti_payloads = [
        "{{ __class__.__mro__[1].__subclasses__() }}",
        "{{ user.__globals__ }}",
        "{{ obj.__init__.__globals__['sys'] }}",
        "{{ ''.__class__.__base__ }}",
        "{{ __builtins__.__import__('os').system('id') }}",
    ]
    for payload in ssti_payloads:
        with pytest.raises(TemplateSecurityError) as excinfo:
            PrecompiledTemplate("malicious", payload)
        assert "Forbidden introspection attribute" in str(excinfo.value) or "Invalid placeholder expression" in str(excinfo.value)


def test_user_input_treated_as_literal_data_not_re_executed():
    tmpl = PrecompiledTemplate("email_notification", "Notification: {{ message }}", escape_html=True)
    # Attacker passes an SSTI payload inside the variable value
    malicious_user_input = "{{ ''.__class__.__mro__[1].__subclasses__() }}"
    rendered = tmpl.render({"message": malicious_user_input})

    # The payload MUST remain raw/escaped literal text and NEVER evaluate
    assert rendered == "Notification: {{ &#x27;&#x27;.__class__.__mro__[1].__subclasses__() }}"
    assert "<class" not in rendered


def test_safe_template_registry_workflow():
    registry = SafeTemplateRegistry()
    registry.register("bounty_merged", "Bounty #{{ bounty_id }} payout of {{ amount }} USD sent to {{ wallet }}.")

    result = registry.render("bounty_merged", {
        "bounty_id": 284,
        "amount": "200.00",
        "wallet": "0xb695eF78B452718E28ea4e410b001a18206D0aE9",
    })
    assert "Bounty #284 payout of 200.00 USD sent to 0xb695eF78B452718E28ea4e410b001a18206D0aE9." == result


def test_unregistered_template_raises():
    registry = SafeTemplateRegistry()
    with pytest.raises(KeyError):
        registry.render("nonexistent_id", {})
