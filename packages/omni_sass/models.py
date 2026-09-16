"""Data models for SASS stylesheet compilation, theming, and cloud workspace isolation."""


from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Dict, List


class OutputStyle(str, Enum):
    """Supported CSS output formats."""
    EXPANDED = "expanded"
    COMPRESSED = "compressed"
    NESTED = "nested"


class WorkspaceMode(str, Enum):
    """Operational mode for OmniBlocks environment."""
    STANDALONE = "standalone"
    OMNI_SAAS = "omni_saas"


class UserRole(str, Enum):
    """Role-based access levels for multi-tenant organizations."""
    OWNER = "owner"
    ADMIN = "admin"
    COLLABORATOR = "collaborator"
    VIEWER = "viewer"


@dataclass
class SassDeclaration:
    """Represents a single CSS property declaration."""
    property_name: str
    property_value: str
    is_important: bool = False
    is_default: bool = False

    def to_css(self) -> str:
        """Render the declaration as standard CSS string."""
        suffix = " !important" if self.is_important else ""
        return f"{self.property_name}: {self.property_value}{suffix};"


@dataclass
class SassRuleNode:
    """Represents a CSS rule block with selector and declarations."""
    selector: str
    declarations: List[SassDeclaration] = field(default_factory=list)
    nested_rules: List["SassRuleNode"] = field(default_factory=list)

    def add_declaration(self, name: str, value: str, important: bool = False) -> None:
        """Append a declaration to this rule node."""
        self.declarations.append(SassDeclaration(name, value, important))


@dataclass
class MixinDefinition:
    """Represents a reusable SASS mixin."""
    name: str
    parameters: List[str] = field(default_factory=list)
    defaults: Dict[str, str] = field(default_factory=dict)
    body: str = ""


@dataclass
class ThemeConfig:
    """Visual theme configuration for OmniBlocks block workspace."""
    name: str
    primary_color: str
    secondary_color: str
    workspace_background: str
    toolbox_background: str
    text_color: str
    border_radius: str = "4px"
    font_family: str = "sans-serif"
    accent_color: str = "#f59e0b"

    def to_dict(self) -> Dict[str, str]:
        """Convert theme configuration to dictionary format."""
        return {
            "name": self.name,
            "primary_color": self.primary_color,
            "secondary_color": self.secondary_color,
            "workspace_background": self.workspace_background,
            "toolbox_background": self.toolbox_background,
            "text_color": self.text_color,
            "border_radius": self.border_radius,
            "font_family": self.font_family,
            "accent_color": self.accent_color,
        }


@dataclass
class OmniProject:
    """Represents an OmniBlocks project in multi-tenant SaaS mode."""
    project_id: str
    tenant_id: str
    title: str
    size_bytes: int
    created_at: float
    is_public: bool = False


@dataclass
class TenantRecord:
    """Represents an organization tenant within OmniBlocks cloud."""
    tenant_id: str
    organization_name: str
    tier: str
    max_projects: int
    max_storage_bytes: int
    current_storage_bytes: int = 0
    projects: Dict[str, OmniProject] = field(default_factory=dict)
    members: Dict[str, UserRole] = field(default_factory=dict)


@dataclass
class EscrowCalculation:
    """Arbitrary-precision escrow calculation following REWARD_POLICY specifications."""
    bounty_usd: Decimal
    coin_reward: Decimal
    contributor_ratio: Decimal
    contributor_coins: Decimal
    cash_payout_usd: Decimal
    platform_fee_usd: Decimal
    exchange_rate_coin_to_usd: Decimal
    exchange_rate_usd_to_coin: Decimal
