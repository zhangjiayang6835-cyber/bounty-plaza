import { system, CommandPermissionLevel, Player, Entity } from '@minecraft/server';

system.beforeEvents.startup.subscribe(() => {
  system.registerCommand({
    name: "inspect",
    description: "Inspect an entity and output its type and id",
    permission: CommandPermissionLevel.Operator,
    overloads: [
      {
        parameters: [
          {
            name: "target",
            type: "entity",
            optional: false
          }
        ],
        handler: ({ source, target }) => {
          if (!(source instanceof Player)) {
            source.sendMessage("§cOnly players can use this command.");
            return;
          }
          const entity = target as Entity;
          source.sendMessage(`§aInspect: §r${entity.id} (${entity.typeId})`);
        }
      }
    ]
  });
});