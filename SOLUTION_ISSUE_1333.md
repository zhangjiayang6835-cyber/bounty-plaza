# Solution for Issue #1333

## 🛠️ Proposed Solution (by Aditya Waghamare)

### Analysis
The `CustomCommandRegistry` API was deprecated and removed in Minecraft Bedrock 1.21.70, resulting in `CommandRegistrationError` when addons attempt to register custom commands at global scope or inside legacy event hooks. Proper command registration must now use the stable `@minecraft/server` v2.8.0+ `system.beforeEvents.startup` lifecycle event combined with correct `CommandPermissionLevel` gating.

### Fix
Refactor `scripts/commands/inspect.ts` to hook into `system.beforeEvents.startup` and register the inspect command safely using the updated API.

### Implementation
```typescript
import { system, world, CommandPermissionLevel, MessageCommandParamType } from "@minecraft/server";

export function registerInspectCommand(): void {
    system.beforeEvents.startup.subscribe((event) => {
        try {
            // Register command with proper v2.8.0+ syntax and permission gating
            system.commandRegistry.registerCommand({
                name: "inspect",
                description: "Inspect target entity or block metadata.",
                permissionLevel: CommandPermissionLevel.Operator,
            });
            console.warn("[Aquarium] Successfully registered /inspect command.");
        } catch (error) {
            console.error(`[Aquarium] Failed to register /inspect command: ${error}`);
        }
    });
}

// Ensure execution at script load
registerInspectCommand();
```

### Testing
- Run Bedrock Dedicated Server (BDS) 1.21.70 with the updated module.
- Confirm `system.beforeEvents.startup` successfully registers the command without throwing `CommandRegistrationError`.
- Verify operator-only execution rights are correctly enforced via `CommandPermissionLevel.Operator`.

Signed-off-by: Aditya Waghamare <adityawaghamare7620@gmail.com>

---
*Submitted by Aditya Waghamare*
💰 **Payout Address (Base L2 / EVM):** `0xb61dBcdBc3407F71EaCb64D4CBFAcf9FFfe2415C`