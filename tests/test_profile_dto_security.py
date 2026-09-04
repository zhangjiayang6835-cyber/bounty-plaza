"""Unit and security test suite for DTO-Based Mass Assignment Defense.
Resolves Issue #281: Mass Assignment in User Profile Update -> Privilege Escalation ($120 USD).
"""

import pytest
from scripts.profile_dto_security import (
    UserModel,
    UserProfileUpdateDTO,
    UserViewModel,
    MassAssignmentSecurityError,
    ValidationError,
)


@pytest.fixture
def base_user():
    return UserModel(
        id="usr_007",
        username="agent_bond",
        role="user",
        is_admin=False,
        balance=50.0,
        display_name="James",
        bio="Licensed agent",
        location="London",
        website="https://mi6.gov.uk",
    )


def test_valid_profile_update_via_dto(base_user):
    payload = {
        "display_name": "Commander Bond",
        "bio": "Senior field intelligence operative",
        "location": "Geneva",
    }
    dto = UserProfileUpdateDTO.from_dict(payload)
    base_user.update_from_dto(dto)

    assert base_user.display_name == "Commander Bond"
    assert base_user.bio == "Senior field intelligence operative"
    assert base_user.location == "Geneva"
    # Unchanged fields
    assert base_user.role == "user"
    assert base_user.is_admin is False
    assert base_user.balance == 50.0


def test_mass_assignment_role_escalation_blocked(base_user):
    """Hostile payload attempting to inject role=admin and is_admin=True."""
    hostile_payload = {
        "display_name": "Attacker",
        "role": "admin",
        "is_admin": True,
        "balance": 999999.0,
    }

    with pytest.raises(MassAssignmentSecurityError, match="Mass assignment attack blocked"):
        UserProfileUpdateDTO.from_dict(hostile_payload, strict_mode=True)

    # Confirm user model remains uncompromised
    assert base_user.role == "user"
    assert base_user.is_admin is False
    assert base_user.balance == 50.0


def test_mass_assignment_permissive_filtering_ignores_sensitive_keys(base_user):
    """When strict_mode=False, sensitive keys are filtered out without error."""
    payload = {
        "display_name": "Clean Name",
        "role": "superadmin",
        "is_admin": True,
        "permissions": ["ALL"],
    }
    dto = UserProfileUpdateDTO.from_dict(payload, strict_mode=False)
    base_user.update_from_dto(dto)

    assert base_user.display_name == "Clean Name"
    assert base_user.role == "user"
    assert base_user.is_admin is False


def test_dto_rejects_non_string_fields():
    with pytest.raises(ValidationError, match="must be a string"):
        UserProfileUpdateDTO.from_dict({"display_name": 12345})


def test_user_view_model_presentation_sanitization(base_user):
    vm = UserViewModel.from_model(base_user)
    assert vm.id == "usr_007"
    assert vm.username == "agent_bond"
    assert vm.display_name == "James"
    # View model exposes safe view fields, not internal mutation setters
    assert not hasattr(vm, "password_hash")
    assert not hasattr(vm, "update_from_dto")
