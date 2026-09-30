```typescript
// scripts/commands/inspect.ts
import { inspect } from "@bedrock/commands";
import type { CustomCommandRegistry } from "@bedrock/core";

CustomCommandRegistry.registerCommand({
    name: "custom_command",
    callback: (context) => {
        // 命令逻辑
    },
    permissionLevel: "ops"
});
```