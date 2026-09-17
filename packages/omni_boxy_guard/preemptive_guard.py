"""
Pre-emptive pull request closure and contributor authorization gate.
"""

from typing import Optional
from packages.omni_boxy_guard.models import (
    Contributor,
    MembershipStatus,
    PreemptiveCloseResult,
    PullRequest,
)
from packages.omni_boxy_guard.whitelist import WhitelistManager


class PreemptiveGuard:
    """Enforces organizational membership and contributor whitelisting on pull requests."""

    DEFAULT_ORGANIZATION = "OmniBlocks"
    DEFAULT_PING_TARGET = "@OmniBlocks/coders"

    def __init__(
        self,
        whitelist_manager: Optional[WhitelistManager] = None,
        organization: str = DEFAULT_ORGANIZATION,
        ping_target: str = DEFAULT_PING_TARGET,
    ) -> None:
        """Initialize PreemptiveGuard with whitelist manager and organizational settings.

        Args:
            whitelist_manager: WhitelistManager instance holding authorized contributors.
            organization: Name of GitHub organization.
            ping_target: GitHub team or handle to mention upon pre-emptive closure.
        """
        self.whitelist = whitelist_manager or WhitelistManager()
        self.organization = organization
        self.ping_target = ping_target

    def resolve_membership_status(self, contributor: Contributor) -> MembershipStatus:
        """Determine membership and authorization tier of a contributor.

        Args:
            contributor: Contributor entity to inspect.

        Returns:
            MembershipStatus enum value.
        """
        if contributor.is_bot or contributor.username.endswith("[bot]"):
            return MembershipStatus.BOT
        if contributor.organization_member:
            return MembershipStatus.ORGANIZATION_MEMBER
        if contributor.role.upper() in ("OWNER", "MEMBER", "COLLABORATOR"):
            return MembershipStatus.ORGANIZATION_MEMBER
        if self.whitelist.is_whitelisted(contributor.username):
            return MembershipStatus.WHITELISTED
        return MembershipStatus.EXTERNAL_CONTRIBUTOR

    def check_pull_request(self, pr: PullRequest) -> PreemptiveCloseResult:
        """Evaluate whether a pull request must be pre-emptively closed.

        Args:
            pr: Pull request entity to evaluate.

        Returns:
            PreemptiveCloseResult detailing gate outcome and notification text.
        """
        status = self.resolve_membership_status(pr.author)

        if status in (MembershipStatus.BOT, MembershipStatus.ORGANIZATION_MEMBER, MembershipStatus.WHITELISTED):
            return PreemptiveCloseResult(
                should_close=False,
                author_status=status,
                target_role_ping="",
                notification_body="",
                audit_reason=f"Contributor @{pr.author.username} authorized under tier {status.value}.",
            )

        notification = (
            f"Notice: Pull request #{pr.pr_number} by @{pr.author.username} has been pre-emptively closed.\n\n"
            f"Under the {self.organization} security policy, pull requests from contributors outside the "
            f"organization who are not on the explicit whitelist must be closed pending triage.\n\n"
            f"Paging {self.ping_target} to review contributor credentials and reopen this pull request "
            f"before initiating automated code review.\n\n"
            f"Contributor: @{pr.author.username}\n"
            f"Status: Non-Member / Unlisted\n"
            f"Action Required: Team member verification and manual reopening."
        )

        audit_reason = (
            f"Pre-emptive closure triggered for PR #{pr.pr_number}: @{pr.author.username} is an external "
            f"contributor not present on the {self.organization} whitelist."
        )

        return PreemptiveCloseResult(
            should_close=True,
            author_status=status,
            target_role_ping=self.ping_target,
            notification_body=notification,
            audit_reason=audit_reason,
        )

    def can_reopen(self, actor: Contributor) -> bool:
        """Validate whether an actor is authorized to reopen a pre-emptively closed pull request.

        Args:
            actor: Contributor attempting the reopen action.

        Returns:
            True if actor has organizational authorization, False otherwise.
        """
        if actor.is_bot:
            return False
        if actor.organization_member:
            return True
        return actor.role.upper() in ("OWNER", "MEMBER", "COLLABORATOR")

    def evaluate_reopen_request(self, pr: PullRequest, actor: Contributor) -> tuple[bool, str]:
        """Process a pull request reopen attempt and generate response message.

        Args:
            pr: Target pull request.
            actor: Contributor triggering reopen.

        Returns:
            Tuple of (is_approved, explanation_message).
        """
        if not self.can_reopen(actor):
            message = (
                f"Reopen rejected: @{actor.username} lacks required organizational authorization. "
                f"Only members of {self.organization} or repository maintainers may reopen pre-emptively closed PRs."
            )
            return False, message

        message = (
            f"Pull request #{pr.pr_number} successfully validated and reopened by @{actor.username} "
            f"({actor.role}). Automated code review pipeline is now unblocked."
        )
        return True, message
