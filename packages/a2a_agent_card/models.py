"""Data models representing A2A Agent Card specifications and schemas."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field


@dataclass
class AgentCardModes:
    """Input and output transfer mode configurations.

    Attributes:
        input_modes: Permitted ingestion mime types.
        output_modes: Permitted emission mime types.
    """

    input_modes: list[str] = field(
        default_factory=lambda: ["application/json", "text/plain"]
    )
    output_modes: list[str] = field(
        default_factory=lambda: ["application/json", "text/plain"]
    )


@dataclass
class AgentCardInterface:
    """Declared protocol interface binding for the agent card.

    Attributes:
        url: Canonical endpoint URL for direct agent communications.
        protocol_version: Specification version string, strictly 1.0.
        protocol_binding: Formal binding identifier URI.
    """

    url: str
    protocol_version: str = "1.0"
    protocol_binding: str = "https://agentbounties.app/docs/a2a-direct-api-binding-v1"

    def to_dict(self) -> dict:
        """Convert interface representation to wire format dictionary.

        Returns:
            Dictionary matching A2A wire schema.
        """
        return {
            "url": self.url,
            "protocolVersion": self.protocol_version,
            "protocolBinding": self.protocol_binding,
        }


@dataclass
class AgentCardSkill:
    """Distinct capability or workflow exposed by the agent card.

    Attributes:
        skill_id: Unique slug identifier for the capability.
        name: Human and machine readable display title.
        description: Functional summary of skill inputs and outcomes.
        tags: Categorization tags.
    """

    skill_id: str
    name: str
    description: str
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert skill representation to dictionary format.

        Returns:
            Dictionary representation of skill.
        """
        return {
            "id": self.skill_id,
            "name": self.name,
            "description": self.description,
            "tags": list(self.tags),
        }


@dataclass
class AgentCard:
    """Canonical A2A Agent Card document root.

    Attributes:
        name: Product or agent entity name.
        description: Summary of role and boundary conditions.
        version: Semantic release version string.
        capabilities: Feature support dictionary.
        modes: Configured input and output modes.
        supported_interfaces: Collection of declared API bindings.
        skills: Collection of registered operational capabilities.
    """

    name: str = "Agent Bounties"
    description: str = (
        "Canonical discovery card for autonomous claimable work and "
        "verified settlement receipts."
    )
    version: str = "1.0.0"
    capabilities: dict = field(
        default_factory=lambda: {
            "streaming": False,
            "pushNotifications": False,
            "extendedAgentCard": False,
        }
    )
    modes: AgentCardModes = field(default_factory=AgentCardModes)
    supported_interfaces: list[AgentCardInterface] = field(
        default_factory=lambda: [
            AgentCardInterface(
                url="https://api.agentbounties.app/a2a/v1",
                protocol_version="1.0",
                protocol_binding="https://agentbounties.app/docs/a2a-direct-api-binding-v1",
            )
        ]
    )
    skills: list[AgentCardSkill] = field(default_factory=list)

    @classmethod
    def create_canonical(cls) -> AgentCard:
        """Construct the canonical production-ready agent card instance.

        Returns:
            Fully populated canonical AgentCard.
        """
        raw_skills = (
            (
                "discover-funded-work",
                "Discover funded work",
                "Queries canonical claimable opportunities with verified funding.",
                ["discovery", "claimable", "bounties"],
            ),
            (
                "plan-bounty-claim",
                "Plan bounty claim",
                "Analyzes acceptance criteria and constructs deterministic claim evidence.",
                ["planning", "claimable", "verification"],
            ),
            (
                "submit-bounty-evidence",
                "Submit bounty evidence",
                "Submits work artifacts to canonical verifier quorums.",
                ["submission", "evidence", "canonical"],
            ),
            (
                "check-bounty-settlement",
                "Check bounty settlement",
                "Inspects on-chain settlement receipts for bountysettled status.",
                ["settlement", "bountysettled", "receipt"],
            ),
            (
                "post-bounty",
                "Post bounty",
                "Registers new escrow-backed tasks into the canonical registry.",
                ["deposit", "escrow", "canonical"],
            ),
        )

        skill_objs = [
            AgentCardSkill(
                skill_id=s[0],
                name=s[1],
                description=s[2],
                tags=list(s[3]),
            )
            for s in raw_skills
        ]

        return cls(
            name="Agent Bounties",
            description=(
                "Canonical discovery card for autonomous claimable work and "
                "verified settlement receipts."
            ),
            version="1.0.0",
            capabilities={
                "streaming": False,
                "pushNotifications": False,
                "extendedAgentCard": False,
            },
            modes=AgentCardModes(),
            supported_interfaces=[
                AgentCardInterface(
                    url="https://api.agentbounties.app/a2a/v1",
                    protocol_version="1.0",
                    protocol_binding="https://agentbounties.app/docs/a2a-direct-api-binding-v1",
                )
            ],
            skills=skill_objs,
        )

    def to_dict(self) -> dict:
        """Serialize agent card instance into schema-compliant dictionary.

        Returns:
            Clean dictionary representation without root protocolVersion.
        """
        data = {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "capabilities": dict(self.capabilities),
            "defaultInputModes": list(self.modes.input_modes),
            "defaultOutputModes": list(self.modes.output_modes),
            "supportedInterfaces": [
                item.to_dict() for item in self.supported_interfaces
            ],
            "skills": [item.to_dict() for item in self.skills],
        }
        return data

    def to_json(self, indent: int = 2) -> str:
        """Produce deterministic formatted JSON serialization.

        Args:
            indent: Formatting whitespace indentation level.

        Returns:
            JSON string representation.
        """
        payload = json.dumps(
            self.to_dict(),
            indent=indent,
            ensure_ascii=False,
            sort_keys=True,
        )
        return f"{payload}\n"

    def compute_sha256(self) -> str:
        """Compute cryptographic SHA-256 digest of serialized card.

        Returns:
            Hex-encoded hash string.
        """
        digest = hashlib.sha256(self.to_json().encode("utf-8")).hexdigest()
        return f"{digest}"

    def compute_etag(self) -> str:
        """Compute HTTP entity tag for cache negotiation.

        Returns:
            Formatted quoted ETag header value.
        """
        raw_hash = self.compute_sha256()[:32]
        return f'"{raw_hash}"'
