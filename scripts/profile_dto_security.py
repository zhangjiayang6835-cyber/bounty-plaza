"""DTO-Based Whitelist Mass Assignment Defense for User Profile Updates.
Resolves Issue #281: Mass Assignment in User Profile Update -> Privilege Escalation ($120 USD).

Implements:
1. Strict DTO (Data Transfer Object) pattern for user profile mutations.
2. Explicit whitelist parameter binding, ignoring or rejecting unauthorized sensitive fields.
3. Blacklist guards against privilege escalation keys ('role', 'is_admin', 'permissions', 'balance', 'password_hash').
4. ViewModel presentation layer sanitization.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Set


class MassAssignmentSecurityError(ValueError):
    """Raised when an illegal attempt to bind protected model attributes is detected."""
    pass


class ValidationError(ValueError):
    """Raised when DTO validation constraints fail."""
    pass


# Strict whitelist of mutable fields for standard profile updates
ALLOWED_PROFILE_FIELDS: Set[str] = {
    "display_name",
    "bio",
    "avatar_url",
    "location",
    "website",
    "locale",
    "phone_number",
}

# Explicit protected sensitive fields that must never be bound via mass assignment
PROTECTED_SENSITIVE_FIELDS: Set[str] = {
    "id",
    "role",
    "roles",
    "is_admin",
    "is_superuser",
    "is_staff",
    "permissions",
    "balance",
    "credits",
    "password",
    "password_hash",
    "email_verified",
    "created_at",
    "updated_at",
    "token",
}


@dataclass
class UserProfileUpdateDTO:
    """Strict Data Transfer Object (DTO) for User Profile Updates."""
    display_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    location: Optional[str] = None
    website: Optional[str] = None
    locale: Optional[str] = None
    phone_number: Optional[str] = None

    @classmethod
    def from_dict(
        cls,
        payload: Dict[str, Any],
        strict_mode: bool = True
    ) -> "UserProfileUpdateDTO":
        """Constructs and validates DTO from untrusted request dictionary.

        Args:
            payload: Raw request dictionary from client.
            strict_mode: If True, raises MassAssignmentSecurityError when sensitive fields are supplied.
                         If False, silently filters them out according to whitelist.
        """
        if not isinstance(payload, dict):
            raise ValidationError("Payload must be a dictionary")

        # Detect hostile mass assignment attempts
        intercepted_sensitive = [k for k in payload.keys() if k.lower() in PROTECTED_SENSITIVE_FIELDS]
        if strict_mode and intercepted_sensitive:
            raise MassAssignmentSecurityError(
                f"Mass assignment attack blocked: Unauthorized attempt to mutate protected fields: {intercepted_sensitive}"
            )

        sanitized_kwargs: Dict[str, Any] = {}
        for k in ALLOWED_PROFILE_FIELDS:
            if k in payload:
                val = payload[k]
                if val is not None and not isinstance(val, str):
                    raise ValidationError(f"Field '{k}' must be a string")
                sanitized_kwargs[k] = val.strip() if isinstance(val, str) else None

        return cls(**sanitized_kwargs)

    def to_update_dict(self) -> Dict[str, Any]:
        """Returns clean dictionary containing only explicitly populated fields."""
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass
class UserViewModel:
    """Safe read-only presentation model returned to clients."""
    id: str
    username: str
    display_name: str
    bio: str
    avatar_url: str
    location: str
    website: str
    role: str

    @classmethod
    def from_model(cls, user_model: "UserModel") -> "UserViewModel":
        return cls(
            id=user_model.id,
            username=user_model.username,
            display_name=user_model.display_name,
            bio=user_model.bio,
            avatar_url=user_model.avatar_url,
            location=user_model.location,
            website=user_model.website,
            role=user_model.role,
        )


class UserModel:
    """Internal user entity with secure attribute binding."""

    def __init__(
        self,
        id: str,
        username: str,
        role: str = "user",
        is_admin: bool = False,
        balance: float = 0.0,
        display_name: str = "",
        bio: str = "",
        avatar_url: str = "",
        location: str = "",
        website: str = "",
    ):
        self.id = id
        self.username = username
        self.role = role
        self.is_admin = is_admin
        self.balance = balance
        self.display_name = display_name
        self.bio = bio
        self.avatar_url = avatar_url
        self.location = location
        self.website = website

    def update_from_dto(self, dto: UserProfileUpdateDTO) -> "UserModel":
        """Safely updates model attributes exclusively from validated DTO fields."""
        update_data = dto.to_update_dict()
        for field_name, value in update_data.items():
            if field_name in ALLOWED_PROFILE_FIELDS:
                setattr(self, field_name, value)
        return self
