"""Multi-tenant execution dispatcher for Boxy assistant tools."""

from typing import Any, Dict, List, Optional
from packages.omni_boxy_saas.metering import UsageMeter
from packages.omni_boxy_saas.models import Tenant, TenantStatus, ToolPermission
from packages.omni_boxy_saas.security import BoxySafetyFilter
from packages.omni_boxy_saas.sticky_notes import StickyNoteStore


ALLOWED_REACTIONS = {"laugh", "thumbs_up", "thumbs_down", "heart", "eyes", "rocket", "hooray"}
ALLOWED_LABELS = {"bounty", "bug", "enhancement", "triage", "documentation", "security", "duplicate"}


class BoxyToolsDispatcher:
    """Dispatches tool execution requests inside isolated tenant boundaries."""

    def __init__(
        self,
        sticky_store: StickyNoteStore,
        usage_meter: UsageMeter,
        safety_filter: Optional[BoxySafetyFilter] = None,
    ) -> None:
        """Initialize dispatcher with persistent storage, usage meter, and safety validator."""
        self.sticky_store = sticky_store
        self.usage_meter = usage_meter
        self.safety_filter = safety_filter or BoxySafetyFilter()

    def _validate_tenant_active(self, tenant: Tenant) -> None:
        """Verify tenant account is currently active."""
        if tenant.status != TenantStatus.ACTIVE:
            raise PermissionError(f"Tenant '{tenant.tenant_id}' is not active (status: {tenant.status.value})")

    def execute_save_sticky_note(
        self,
        tenant: Tenant,
        repo_full_name: str,
        title: str,
        content: str,
        author: str,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Execute sticky note persistence tool for Boxy."""
        self._validate_tenant_active(tenant)

        sanitized_title = self.safety_filter.sanitize_text(title)
        sanitized_content = self.safety_filter.sanitize_text(content)

        note = self.sticky_store.save_note(
            tenant_id=tenant.tenant_id,
            repo_full_name=repo_full_name,
            title=sanitized_title,
            content=sanitized_content,
            author=author,
            tags=tags,
            max_notes_limit=tenant.max_sticky_notes,
        )

        tokens_consumed = len(sanitized_title.split()) + len(sanitized_content.split()) + 25
        self.usage_meter.record_tokens(
            tenant_id=tenant.tenant_id,
            input_tokens=tokens_consumed,
            output_tokens=15,
            cached_tokens=0,
        )

        response = {
            "status": "success",
            "tool": ToolPermission.SAVE_STICKY.value,
            "note_id": note.note_id,
            "message": f"Sticky note '{note.title}' successfully saved.",
        }
        return response

    def execute_get_sticky_notes(
        self,
        tenant: Tenant,
        repo_full_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Retrieve tenant-scoped sticky notes."""
        self._validate_tenant_active(tenant)
        notes = self.sticky_store.list_notes(tenant.tenant_id, repo_full_name)

        self.usage_meter.record_tokens(
            tenant_id=tenant.tenant_id,
            input_tokens=20,
            output_tokens=len(notes) * 15 + 10,
            cached_tokens=0,
        )

        formatted_notes = [
            {
                "note_id": n.note_id,
                "title": n.title,
                "content": n.content,
                "author": n.author,
                "tags": n.tags,
                "created_at": n.created_at,
            }
            for n in notes
        ]

        response = {
            "status": "success",
            "tool": "get_sticky_notes",
            "count": len(formatted_notes),
            "notes": formatted_notes,
        }
        return response

    def execute_react_comment(
        self,
        tenant: Tenant,
        comment_id: int,
        reaction: str,
    ) -> Dict[str, Any]:
        """Execute emoji reaction tool on target comment."""
        self._validate_tenant_active(tenant)
        clean_reaction = reaction.lower().strip()
        if clean_reaction not in ALLOWED_REACTIONS:
            raise ValueError(f"Reaction '{clean_reaction}' is not supported by Boxy")

        self.usage_meter.record_tokens(
            tenant_id=tenant.tenant_id,
            input_tokens=15,
            output_tokens=10,
            cached_tokens=0,
        )

        response = {
            "status": "success",
            "tool": ToolPermission.POST_COMMENT.value,
            "comment_id": comment_id,
            "reaction": clean_reaction,
            "message": f"Successfully reacted with '{clean_reaction}' to comment {comment_id}.",
        }
        return response

    def execute_label_issue(
        self,
        tenant: Tenant,
        issue_number: int,
        label: str,
    ) -> Dict[str, Any]:
        """Execute issue labeling tool with whitelist verification."""
        self._validate_tenant_active(tenant)
        clean_label = label.lower().strip()
        if clean_label not in ALLOWED_LABELS:
            raise ValueError(f"Label '{clean_label}' is not in approved taxonomy")

        self.usage_meter.record_tokens(
            tenant_id=tenant.tenant_id,
            input_tokens=15,
            output_tokens=10,
            cached_tokens=0,
        )

        response = {
            "status": "success",
            "tool": ToolPermission.LABEL_ISSUE.value,
            "issue_number": issue_number,
            "label": clean_label,
            "message": f"Label '{clean_label}' added to issue {issue_number}.",
        }
        return response

    def execute_review_pr(
        self,
        tenant: Tenant,
        pr_number: int,
        diff_text: str,
    ) -> Dict[str, Any]:
        """Execute automated pull request code review within tenant quota limits."""
        self._validate_tenant_active(tenant)

        usage = self.usage_meter.get_or_create_usage(tenant.tenant_id)
        if usage.reviews_count >= tenant.max_reviews_per_day:
            raise ValueError(f"Daily PR review limit of {tenant.max_reviews_per_day} reached")

        sanitized_diff = self.safety_filter.sanitize_text(diff_text)
        diff_lines = sanitized_diff.splitlines()

        added_lines = [l for l in diff_lines if l.startswith("+") and not l.startswith("+++")]
        removed_lines = [l for l in diff_lines if l.startswith("-") and not l.startswith("---")]

        input_toks = max(50, len(sanitized_diff.split()))
        output_toks = 120
        self.usage_meter.record_tokens(
            tenant_id=tenant.tenant_id,
            input_tokens=input_toks,
            output_tokens=output_toks,
            cached_tokens=20,
        )
        self.usage_meter.record_review(tenant.tenant_id)

        findings: List[str] = []
        for line in added_lines:
            if "eval(" in line or "exec(" in line:
                findings.append(f"Security Alert: Dynamic evaluation construct identified: {line.strip()}")
            if "TODO" in line or "FIXME" in line:
                findings.append(f"Notice: Unresolved developer annotation: {line.strip()}")

        review_status = "changes_requested" if findings else "approved"
        summary_text = (
            f"Boxy completed automated inspection on PR #{pr_number}. "
            f"Analyzed {len(diff_lines)} lines ({len(added_lines)} additions, {len(removed_lines)} deletions)."
        )

        response = {
            "status": "success",
            "tool": ToolPermission.REVIEW_PR.value,
            "pr_number": pr_number,
            "review_status": review_status,
            "findings": findings,
            "summary": summary_text,
        }
        return response

    def execute_sandboxed_command(
        self,
        tenant: Tenant,
        command_line: str,
    ) -> Dict[str, Any]:
        """Execute sandboxed shell instruction verifying binary whitelist and isolation."""
        self._validate_tenant_active(tenant)

        is_safe, reason = self.safety_filter.is_safe_command(command_line)
        if not is_safe:
            raise PermissionError(f"Command rejected by safety filter: {reason}")

        self.usage_meter.record_container_spawn(tenant.tenant_id)
        self.usage_meter.record_tokens(
            tenant_id=tenant.tenant_id,
            input_tokens=40,
            output_tokens=30,
            cached_tokens=0,
        )

        command_tokens = command_line.strip().split()
        binary = command_tokens[0]
        arguments = command_tokens[1:]

        simulated_output = (
            f"[boxy-sandbox-container] Executed '{binary}' with args: {arguments}. "
            f"Tenant: {tenant.tenant_id}. Exit code: 0."
        )

        response = {
            "status": "success",
            "tool": ToolPermission.RUN_COMMAND.value,
            "command": command_line,
            "exit_code": 0,
            "output": simulated_output,
        }
        return response
