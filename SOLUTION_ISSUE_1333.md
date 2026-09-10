# Solution for Issue #1333

## 🛠️ Proposed Solution (by Aditya Waghamare)

### Analysis
The `CustomCommandRegistry` API was deprecated and removed in Minecraft Bedrock scripting engine updates (v1.21.70+), leading to `TypeError: CustomCommandRegistry.registerCommand is not a function` during `system.beforeEvents.startup`. Custom commands must now be registered via the stable `@minecraft/server` command and system initialization event lifecycle.

### Fix
Refactored `scripts/commands/inspect.ts` to utilize the modern command registration pattern and `@minecraft/server` system startup events with proper `CommandPermissionLevel` gating.

### Implementation
```typescript
import { system, world, CommandPermissionLevel } from "@minecraft/server";

export function registerInspectCommand() {
    system.beforeEvents.startup.subscribe((initEvent) => {
        try {
            // Registering custom slash command using stable Minecraft Bedrock API
            system.registerCommand({
                name: "inspect",
                description: "Inspects target entity or player data",
                permissionLevel: CommandPermissionLevel.Operator,
                execute: (chatEvent) => {
                    const sender = chatEvent.sender;
                    sender.sendMessage("§aRunning inspector utility...");
                }
            });
        } catch (error) {
            console.error(`Failed to register /inspect command: ${error}`);
        }
    });
}
registerInspectCommand();

Signed-off-by: Aditya Waghamare <adityawaghamare7620@gmail.com>
```

### Testing
1. Boot Bedrock Dedicated Server (BDS) 1.21.70 with script debugging enabled.
2. Verify startup logs confirm successful command registration without `CommandRegistrationError`.
3. Run `/inspect` in-game as an operator and verify output.

---
*Submitted by Aditya Waghamare*
💰 **Payout Address (Base L2 / EVM):** `0xb61dBcdBc3407F71EaCb64D4CBFAcf9FFfe2415C`