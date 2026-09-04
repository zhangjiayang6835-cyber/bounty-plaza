import pytest
from scripts.safe_merge import (
    safe_merge,
    safe_json_loads,
    sanitize_keys,
    PrototypePollutionError,
)


def test_safe_merge_standard_objects():
    target = {"app": {"name": "bounty-plaza", "version": "1.0"}}
    source = {"app": {"version": "1.1", "author": "security-team"}, "debug": True}
    result = safe_merge(target, source)
    assert result == {
        "app": {"name": "bounty-plaza", "version": "1.1", "author": "security-team"},
        "debug": True,
    }


def test_safe_merge_blocks_proto():
    target = {}
    malicious_source = {"__proto__": {"polluted": True}}
    with pytest.raises(PrototypePollutionError) as excinfo:
        safe_merge(target, malicious_source)
    assert "__proto__" in str(excinfo.value)


def test_safe_merge_blocks_constructor_and_prototype():
    target = {}
    with pytest.raises(PrototypePollutionError):
        safe_merge(target, {"constructor": {"prototype": {"admin": True}}})

    with pytest.raises(PrototypePollutionError):
        safe_merge(target, {"prototype": {"isAdmin": True}})


def test_safe_json_loads_valid():
    raw = '{"user": {"name": "alice", "roles": ["developer", "auditor"]}}'
    data = safe_json_loads(raw)
    assert data["user"]["name"] == "alice"
    assert data["user"]["roles"] == ["developer", "auditor"]


def test_safe_json_loads_detects_nested_proto():
    raw_payload = '{"settings": {"theme": "dark", "__proto__": {"isAdmin": true}}}'
    with pytest.raises(PrototypePollutionError) as excinfo:
        safe_json_loads(raw_payload)
    assert "Illegal key '__proto__'" in str(excinfo.value)


def test_sanitize_keys_nested_list():
    payload = [
        {"valid": 1},
        {"nested": [{"constructor": "malicious"}]}
    ]
    with pytest.raises(PrototypePollutionError):
        sanitize_keys(payload)
