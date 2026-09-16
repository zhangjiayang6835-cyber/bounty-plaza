"""Tenant-isolated persistent memory and sticky note registry for Boxy assistant."""

import time
import uuid
from typing import Dict, List, Optional
from packages.omni_boxy_saas.models import StickyNote


class StickyNoteStore:
    """Provides isolated memory persistence partitioned strictly by tenant boundary."""

    def __init__(self) -> None:
        """Initialize in-memory registry indexed by tenant and note identifier."""
        self._notes_by_tenant: Dict[str, Dict[str, StickyNote]] = {}

    def save_note(
        self,
        tenant_id: str,
        repo_full_name: str,
        title: str,
        content: str,
        author: str,
        tags: Optional[List[str]] = None,
        max_notes_limit: Optional[int] = None,
    ) -> StickyNote:
        """Store context memory item associated with tenant repository."""
        if tenant_id not in self._notes_by_tenant:
            self._notes_by_tenant[tenant_id] = {}

        tenant_bucket = self._notes_by_tenant[tenant_id]
        if max_notes_limit is not None and len(tenant_bucket) >= max_notes_limit:
            raise ValueError(f"Tenant sticky note capacity of {max_notes_limit} reached")

        note_id = str(uuid.uuid4())[:8]
        tag_list = list(tags) if tags else []
        note = StickyNote(
            note_id=note_id,
            tenant_id=tenant_id,
            repo_full_name=repo_full_name.lower().strip(),
            title=title.strip(),
            content=content.strip(),
            author=author.strip(),
            created_at=time.time(),
            tags=tag_list,
        )
        tenant_bucket[note_id] = note
        return note

    def get_note(self, tenant_id: str, note_id: str) -> Optional[StickyNote]:
        """Retrieve specific sticky note by identifier, enforcing tenant ownership."""
        tenant_bucket = self._notes_by_tenant.get(tenant_id)
        if not tenant_bucket:
            return None
        return tenant_bucket.get(note_id)

    def list_notes(self, tenant_id: str, repo_full_name: Optional[str] = None) -> List[StickyNote]:
        """Enumerate notes belonging to tenant, optionally filtered by repository."""
        tenant_bucket = self._notes_by_tenant.get(tenant_id)
        if not tenant_bucket:
            empty_list: List[StickyNote] = []
            return empty_list

        notes = list(tenant_bucket.values())
        if repo_full_name:
            target_repo = repo_full_name.lower().strip()
            notes = [n for n in notes if n.repo_full_name == target_repo]

        notes.sort(key=lambda n: n.created_at, reverse=True)
        return notes

    def search_notes(self, tenant_id: str, query: str) -> List[StickyNote]:
        """Search tenant notes matching query string in title or content."""
        all_notes = self.list_notes(tenant_id)
        lowered = query.lower()
        matched = [n for n in all_notes if lowered in n.title.lower() or lowered in n.content.lower()]
        return matched

    def delete_note(self, tenant_id: str, note_id: str) -> bool:
        """Delete note if it exists and is owned by calling tenant."""
        tenant_bucket = self._notes_by_tenant.get(tenant_id)
        if not tenant_bucket:
            return False
        if note_id in tenant_bucket:
            del tenant_bucket[note_id]
            return True
        return False

    def count_notes(self, tenant_id: str) -> int:
        """Return total count of sticky notes currently saved for tenant."""
        tenant_bucket = self._notes_by_tenant.get(tenant_id)
        if not tenant_bucket:
            return 0
        return len(tenant_bucket)
