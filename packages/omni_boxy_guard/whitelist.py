"""
Whitelist management engine for authorized Boxy contributors.
"""

import json
import os
from typing import Optional, Set


class WhitelistManager:
    """Manages explicitly whitelisted contributors who may submit pull requests."""

    def __init__(self, initial_users: Optional[list[str]] = None, storage_path: Optional[str] = None) -> None:
        """Initialize WhitelistManager with optional initial users and storage path.

        Args:
            initial_users: Optional list of usernames to seed into the whitelist.
            storage_path: Optional file path for JSON persistence.
        """
        self._whitelisted: Set[str] = set()
        self._storage_path = storage_path

        if initial_users:
            for user in initial_users:
                self.add_user(user)

        if self._storage_path and os.path.exists(self._storage_path):
            self.load_from_file(self._storage_path)

    def add_user(self, username: str) -> bool:
        """Add a username to the explicit whitelist.

        Args:
            username: The GitHub handle to add.

        Returns:
            True if user was added, False if invalid or already present.
        """
        if not username or not isinstance(username, str):
            return False
        cleaned = username.strip().lstrip("@").lower()
        if not cleaned:
            return False
        if cleaned in self._whitelisted:
            return False
        self._whitelisted.add(cleaned)
        if self._storage_path:
            self.save_to_file(self._storage_path)
        return True

    def remove_user(self, username: str) -> bool:
        """Remove a username from the explicit whitelist.

        Args:
            username: The GitHub handle to remove.

        Returns:
            True if user was removed, False if not found.
        """
        if not username or not isinstance(username, str):
            return False
        cleaned = username.strip().lstrip("@").lower()
        if cleaned not in self._whitelisted:
            return False
        self._whitelisted.remove(cleaned)
        if self._storage_path:
            self.save_to_file(self._storage_path)
        return True

    def is_whitelisted(self, username: str) -> bool:
        """Check if a contributor username is on the whitelist.

        Args:
            username: The GitHub handle to check.

        Returns:
            True if whitelisted, False otherwise.
        """
        if not username or not isinstance(username, str):
            return False
        cleaned = username.strip().lstrip("@").lower()
        return cleaned in self._whitelisted

    def get_whitelist(self) -> list[str]:
        """Retrieve sorted list of all whitelisted usernames.

        Returns:
            Sorted list of whitelisted usernames.
        """
        return sorted(list(self._whitelisted))

    def clear(self) -> None:
        """Clear all entries from the whitelist."""
        self._whitelisted.clear()
        if self._storage_path:
            self.save_to_file(self._storage_path)

    def count(self) -> int:
        """Return total number of whitelisted contributors.

        Returns:
            Total count of whitelisted usernames.
        """
        return len(self._whitelisted)

    def save_to_file(self, file_path: str) -> None:
        """Save whitelist to a JSON file on disk.

        Args:
            file_path: Target destination path.
        """
        directory = os.path.dirname(file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
        data = {"whitelisted_users": self.get_whitelist()}
        with open(file_path, "w", encoding="utf-8") as target_file:
            json.dump(data, target_file, indent=2)

    def load_from_file(self, file_path: str) -> None:
        """Load whitelist from a JSON file on disk.

        Args:
            file_path: Source file path.
        """
        if not os.path.exists(file_path):
            return
        with open(file_path, "r", encoding="utf-8") as source_file:
            data = json.load(source_file)
        if isinstance(data, dict) and "whitelisted_users" in data:
            users = data.get("whitelisted_users", [])
            for user in users:
                self.add_user(user)
        elif isinstance(data, list):
            for user in data:
                self.add_user(user)
