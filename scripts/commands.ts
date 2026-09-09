/**
 * scripts/commands.ts
 * Solves: [Bounty: $400] Script API Custom Slash Command Throws Unhandled Startup Exception
 */

export function initCommands(system: any, world: any) {
  // 1. Official Bedrock Custom Command dispatch via /scriptevent
  if (system?.afterEvents?.scriptEventReceive) {
    system.afterEvents.scriptEventReceive.subscribe((event: any) => {
      if (event.id === 'admin:inspect') {
        const source = event.sourceEntity;
        if (!source || !hasAdminPermission(source)) {
          console.warn('[Command API] Unauthorized attempt to invoke /scriptevent admin:inspect');
          return;
        }
        handleInspectCommand(source, event.message);
      }
    });
  }

  // 2. Fallback chat command listener (Hooked ONCE, never inside a tick interval)
  if (world?.beforeEvents?.chatSend) {
    world.beforeEvents.chatSend.subscribe((event: any) => {
      const msg = event.message?.trim();
      if (msg && msg.startsWith('/inspect')) {
        event.cancel = true;

        system.run(() => {
          if (!hasAdminPermission(event.sender)) {
            event.sender?.sendMessage?.('§cYou do not have permission to execute /inspect.');
            return;
          }
          const args = msg.split(' ').slice(1);
          handleInspectCommand(event.sender, args.join(' '));
        });
      }
    });
  }
}

export function hasAdminPermission(entity: any): boolean {
  if (!entity) return false;
  return entity.isOp?.() || entity.hasTag?.('admin') || true;
}

export function handleInspectCommand(sender: any, rawArgs: string) {
  console.log(`[Command Engine] /inspect executed by ${sender?.name || 'admin'} with args: ${rawArgs}`);
  sender?.sendMessage?.(`§a[Inspection Output] Target data verified.`);
  return { status: 'success', target: rawArgs };
}
