"""Automated migration pipeline for converting legacy chat hacks to modern Custom Command API."""

from pathlib import Path
import re
from typing import Optional

from .models import (
    CommandPermissionLevel,
    CustomCommandDefinition,
    CustomCommandParameter,
    CustomCommandParamType,
)


class CommandMigrationPipeline:
    """Transforms legacy Bedrock chat interception scripts to modern custom command API."""

    def extract_legacy_commands(self, legacy_code: str) -> list[str]:
        """Extract command names intercepted via legacy chatSend patterns."""
        pattern = re.compile(
            r"event\.message\.startsWith\(\s*['\"]/([a-zA-Z0-9_-]+)['\"]\s*\)"
        )
        commands = pattern.findall(legacy_code)
        if not commands:
            generic_pattern = re.compile(r"['\"]/([a-zA-Z0-9_-]+)['\"]")
            commands = generic_pattern.findall(legacy_code)
        return sorted(list(set(commands)))

    def build_command_definitions(
        self,
        command_names: list[str],
        default_namespace: str = "admin",
    ) -> list[CustomCommandDefinition]:
        """Convert extracted command names into typed CustomCommandDefinition instances."""
        definitions: list[CustomCommandDefinition] = []
        for cmd in command_names:
            namespaced_name = f"{default_namespace}:{cmd}"
            target_param = CustomCommandParameter(
                name="target",
                param_type=CustomCommandParamType.STRING,
                optional=False,
            )
            mode_param = CustomCommandParameter(
                name="mode",
                param_type=CustomCommandParamType.STRING,
                optional=True,
            )
            definition = CustomCommandDefinition(
                name=namespaced_name,
                description=f"Administration command for {cmd} operations.",
                permission_level=CommandPermissionLevel.GAME_DIRECTORS,
                cheats_required=False,
                mandatory_parameters=[target_param],
                optional_parameters=[mode_param],
            )
            definitions.append(definition)
        return definitions

    def generate_modern_typescript(
        self,
        definitions: Optional[list[CustomCommandDefinition]] = None,
        include_inspect_handler: bool = True,
    ) -> str:
        """Generate compliant modern TypeScript source using system.beforeEvents.startup."""
        defs = definitions or self.build_command_definitions(["inspect"])
        template_lines = [
            'import {',
            '  system,',
            '  CommandPermissionLevel,',
            '  CustomCommandParamType,',
            '  CustomCommandStatus,',
            "} from '@minecraft/server';",
            'import type {',
            '  StartupBeforeEvent,',
            '  CustomCommandOrigin,',
            '  CustomCommandResult,',
            '  CustomCommandRegistry,',
            "} from '@minecraft/server';",
            '',
        ]

        if include_inspect_handler:
            template_lines.extend([
                '/**',
                ' * Executes administration inspect routine on target entity.',
                ' */',
                'export function executeInspectCommand(',
                '  origin: CustomCommandOrigin,',
                '  target: string,',
                '  mode: string = "all"',
                '): CustomCommandResult {',
                '  const caller = origin.sourceEntity ? origin.sourceEntity.nameTag : "Console";',
                '  const info = `Caller: ${caller}, Target: ${target}, Mode: ${mode}`;',
                '  return {',
                '    status: CustomCommandStatus.Success,',
                '    message: `[Inspect] ${info}`,',
                '  };',
                '}',
                '',
            ])

        template_lines.extend([
            '/**',
            ' * Registers all custom slash commands on the provided registry.',
            ' */',
            'export function registerCommandsOnRegistry(registry: CustomCommandRegistry): void {',
        ])

        for cmd_def in defs:
            template_lines.extend([
                '  registry.registerCommand(',
                '    {',
                f'      name: "{cmd_def.name}",',
                f'      description: "{cmd_def.description}",',
                '      permissionLevel: CommandPermissionLevel.GameDirectors,',
                '      cheatsRequired: false,',
                '      mandatoryParameters: [',
                '        { name: "target", type: CustomCommandParamType.String },',
                '      ],',
                '      optionalParameters: [',
                '        { name: "mode", type: CustomCommandParamType.String },',
                '      ],',
                '    },',
                '    (origin: CustomCommandOrigin, target: string, mode?: string) => {',
                '      return executeInspectCommand(origin, target, mode);',
                '    }',
                '  );',
            ])

        template_lines.extend([
            '}',
            '',
            '/**',
            ' * Subscribes to the startup lifecycle event to register custom commands safely.',
            ' */',
            'export function registerCustomCommands(): void {',
            '  system.beforeEvents.startup.subscribe((event: StartupBeforeEvent) => {',
            '    registerCommandsOnRegistry(event.customCommandRegistry);',
            '  });',
            '}',
            '',
            '/**',
            ' * Lifecycle entrypoint maintaining backward compatibility with script loaders.',
            ' */',
            'export function initCommands(): void {',
            '  registerCustomCommands();',
            '}',
            '',
        ])

        return "\n".join(template_lines)

    def migrate_script_content(self, legacy_code: str) -> str:
        """Migrate legacy chat interception script string into modern TypeScript source."""
        commands = self.extract_legacy_commands(legacy_code)
        if not commands:
            commands = ["inspect"]
        definitions = self.build_command_definitions(commands)
        return self.generate_modern_typescript(definitions)

    def migrate_script_file(self, source_path: str, target_path: str) -> str:
        """Read legacy script file and write migrated modern implementation to target."""
        legacy_content = Path(source_path).read_text(encoding="utf-8")
        modern_content = self.migrate_script_content(legacy_content)
        target = Path(target_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(modern_content, encoding="utf-8")
        return modern_content
