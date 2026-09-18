"""
Orchestrator for Boxy pull request review bot, integrating authorization and humor gates.
"""

from typing import Optional
from packages.omni_boxy_guard.humor_engine import HumorAnalysisEngine
from packages.omni_boxy_guard.models import (
    Contributor,
    PRAction,
    PullRequest,
    ReviewVerdict,
)
from packages.omni_boxy_guard.preemptive_guard import PreemptiveGuard
from packages.omni_boxy_guard.whitelist import WhitelistManager


class BoxyReviewBot:
    """Automated review bot that executes pre-emptive closing and humor policy enforcement."""

    def __init__(
        self,
        whitelist_manager: Optional[WhitelistManager] = None,
        organization: str = PreemptiveGuard.DEFAULT_ORGANIZATION,
        ping_target: str = PreemptiveGuard.DEFAULT_PING_TARGET,
    ) -> None:
        """Initialize BoxyReviewBot with guard and humor analysis engines.

        Args:
            whitelist_manager: WhitelistManager instance for contributor filtering.
            organization: Target GitHub organization name.
            ping_target: Team mention target when pre-emptively closing PRs.
        """
        self.whitelist = whitelist_manager or WhitelistManager()
        self.guard = PreemptiveGuard(
            whitelist_manager=self.whitelist,
            organization=organization,
            ping_target=ping_target,
        )
        self.humor_engine = HumorAnalysisEngine()

    def evaluate_pull_request(self, pr: PullRequest) -> ReviewVerdict:
        """Execute complete evaluation pipeline on an incoming pull request.

        Args:
            pr: Pull request entity to inspect.

        Returns:
            ReviewVerdict containing decisions, notifications, and review comments.
        """
        preemptive_result = self.guard.check_pull_request(pr)

        if preemptive_result.should_close:
            summary = (
                f"PR #{pr.pr_number} pre-emptively closed. Author @{pr.author.username} is not "
                f"in organization nor whitelisted. Paging {self.guard.ping_target}."
            )
            return ReviewVerdict(
                pr_number=pr.pr_number,
                preemptive_result=preemptive_result,
                humor_result=None,
                final_action=PRAction.CLOSE,
                summary_message=summary,
            )

        humor_result = self.humor_engine.evaluate_pull_request(pr)

        if humor_result.action == PRAction.REQUEST_CHANGES:
            summary = (
                f"PR #{pr.pr_number} review requested changes: PR attempts to remove humor from the codebase."
            )
            final_action = PRAction.REQUEST_CHANGES
        elif humor_result.action == PRAction.APPROVE:
            summary = (
                f"PR #{pr.pr_number} approved: PR successfully contributes humor to the codebase."
            )
            final_action = PRAction.APPROVE
        else:
            summary = (
                f"PR #{pr.pr_number} passed humor check with neutral score. Continuing to code analysis."
            )
            final_action = PRAction.CONTINUE_REVIEW

        return ReviewVerdict(
            pr_number=pr.pr_number,
            preemptive_result=preemptive_result,
            humor_result=humor_result,
            final_action=final_action,
            summary_message=summary,
        )

    def handle_reopen_request(self, pr: PullRequest, actor: Contributor) -> tuple[bool, str]:
        """Process a request to reopen a pre-emptively closed pull request.

        Args:
            pr: Target pull request.
            actor: Contributor requesting reopen.

        Returns:
            Tuple of (is_success, response_message).
        """
        success, message = self.guard.evaluate_reopen_request(pr, actor)
        if success:
            pr.state = "open"
        return success, message

    def build_github_close_payload(self, verdict: ReviewVerdict) -> dict:
        """Generate GitHub REST API payload for closing a pull request.

        Args:
            verdict: Computed ReviewVerdict.

        Returns:
            Dictionary payload for GitHub API issue/pull update.
        """
        return {
            "state": "closed",
            "state_reason": "not_planned",
            "comment": verdict.preemptive_result.notification_body,
        }

    def build_github_review_payload(self, verdict: ReviewVerdict) -> dict:
        """Generate GitHub REST API payload for creating a pull request review.

        Args:
            verdict: Computed ReviewVerdict.

        Returns:
            Dictionary payload for GitHub API pull request review creation.
        """
        if not verdict.humor_result:
            return {
                "event": "COMMENT",
                "body": verdict.preemptive_result.notification_body,
            }

        event_mapping = {
            PRAction.APPROVE: "APPROVE",
            PRAction.REQUEST_CHANGES: "REQUEST_CHANGES",
            PRAction.CONTINUE_REVIEW: "COMMENT",
            PRAction.CLOSE: "COMMENT",
        }

        return {
            "event": event_mapping.get(verdict.final_action, "COMMENT"),
            "body": verdict.humor_result.review_comment,
        }

    def build_github_status_payload(self, verdict: ReviewVerdict) -> dict:
        """Generate GitHub REST API payload for updating commit status check.

        Args:
            verdict: Computed ReviewVerdict.

        Returns:
            Dictionary payload for GitHub API status check creation.
        """
        if verdict.preemptive_result.should_close:
            return {
                "state": "failure",
                "context": "boxy/authorization-gate",
                "description": "Pre-emptively closed: Author is not an org member or whitelisted.",
            }

        if verdict.humor_result:
            return {
                "state": verdict.humor_result.status_state,
                "context": verdict.humor_result.status_context,
                "description": (
                    "Humor policy passed."
                    if verdict.humor_result.status_state == "success"
                    else "Humor removal detected. Rejected."
                ),
            }

        return {
            "state": "success",
            "context": "boxy/gate",
            "description": "All pre-flight checks passed.",
        }
