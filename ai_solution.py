```typescript
import { world, system } from '@minecraft/server';

export function registerCustomCommands() {
  system.beforeEvents.registerCommand({
    name: '/inspect',
    callback: (command) => {
      if (command.startsWith('/inspect')) {
        // handle logic
      }
    },
  });
}
```