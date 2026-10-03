```typescript
import { Bedrock, commands } from '@minecraft/server';

export function registerCustomCommands() {
  return system.registerCommand({
    name: 'inspect',
    type: commands.ChatCommand,
    description: {
      default: 'inspects something',
      withSubcommand: false,
    },
    callback: (command) => {
      if (command.message.startsWith('/inspect')) {
        // handle logic
      }
    },
  });
}
```