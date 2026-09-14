"""Automated refactoring pipeline for Bedrock script command modernization."""

import re


class CommandMigrationPipeline:
    """Transforms legacy and buggy command scripts into modern Bedrock Script API."""

    @staticmethod
    def migrate_static_registry_calls(content: str) -> str:
        """Replace static CustomCommandRegistry calls with event registry references."""
        pattern = re.compile(
            r"CustomCommandRegistry\.registerCommand\s*\((.*?)\);?",
            re.DOTALL,
        )
        replacement = r"event.customCommandRegistry.registerCommand(\1);"
        return pattern.sub(replacement, content)

    @staticmethod
    def migrate_chat_send_interception(content: str) -> str:
        """Convert deprecated chatSend interception handlers to startup event subscription."""
        chat_pattern = re.compile(
            r"world\.beforeEvents\.chatSend\.subscribe\s*\((.*?)\);?",
            re.DOTALL,
        )
        if not chat_pattern.search(content):
            return content

        modern_header = (
            "import { system, CommandPermissionLevel } from '@minecraft/server';\n\n"
            "system.beforeEvents.startup.subscribe((event) => {\n"
            "  const registry = event.customCommandRegistry;\n"
            "  registry.registerCommand({\n"
            "    name: 'inspect',\n"
            "    description: 'Inspect engine state',\n"
            "    permissionLevel: CommandPermissionLevel.GameDirectors,\n"
            "  }, (origin) => {\n"
            "    // Command logic here\n"
            "  });\n"
            "});\n"
        )
        return chat_pattern.sub(modern_header.strip(), content)

    def migrate_script_content(self, content: str) -> str:
        """Run complete migration pipeline over script content."""
        migrated = self.migrate_static_registry_calls(content)
        migrated = self.migrate_chat_send_interception(migrated)
        return migrated
