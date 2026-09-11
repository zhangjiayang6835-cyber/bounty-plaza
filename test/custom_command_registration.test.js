import test from 'node:test';
import assert from 'node:assert/strict';
import {
  CommandPermissionLevel,
  CustomCommandSource,
  CustomCommandStatus,
} from '../scripts/commands/types.js';
import {
  buildInspectionReport,
  validateCommandPermission,
  executeInspectCommand,
  registerInspectCommand,
} from '../scripts/commands/inspect.js';
import { initializeStartupHooks } from '../scripts/startup.js';

test('registerInspectCommand registers engine:inspect with Admin permission level on StartupEvent', () => {
  let registeredCommand = null;
  let registeredCallback = null;

  const mockRegistry = {
    registerCommand(commandDefinition, callback) {
      registeredCommand = commandDefinition;
      registeredCallback = callback;
    },
  };

  const mockStartupEvent = {
    customCommandRegistry: mockRegistry,
  };

  const command = registerInspectCommand(mockStartupEvent);

  assert.ok(registeredCommand);
  assert.equal(registeredCommand.name, 'engine:inspect');
  assert.equal(registeredCommand.permissionLevel, CommandPermissionLevel.Admin);
  assert.equal(registeredCommand.cheatsRequired, true);
  assert.equal(typeof registeredCallback, 'function');
  assert.equal(command.name, 'engine:inspect');
});

test('registerInspectCommand registers directly when passed customCommandRegistry instance', () => {
  let registeredCommand = null;

  const mockRegistry = {
    registerCommand(commandDefinition) {
      registeredCommand = commandDefinition;
    },
  };

  registerInspectCommand(mockRegistry);
  assert.ok(registeredCommand);
  assert.equal(registeredCommand.name, 'engine:inspect');
  assert.equal(registeredCommand.permissionLevel, CommandPermissionLevel.Admin);
});

test('registerInspectCommand throws TypeError when passed invalid registry', () => {
  assert.throws(
    () => {
      registerInspectCommand({});
    },
    {
      name: 'TypeError',
      message: 'CustomCommandRegistry instance with registerCommand function is required.',
    }
  );
});

test('validateCommandPermission enforces CommandPermissionLevel tiers', () => {
  const lowLevelOrigin = {
    sourceType: CustomCommandSource.Entity,
    permissionLevel: CommandPermissionLevel.Any,
  };
  assert.equal(validateCommandPermission(lowLevelOrigin, CommandPermissionLevel.Admin), false);

  const directorOrigin = {
    sourceType: CustomCommandSource.Entity,
    permissionLevel: CommandPermissionLevel.GameDirectors,
  };
  assert.equal(validateCommandPermission(directorOrigin, CommandPermissionLevel.Admin), false);

  const adminOrigin = {
    sourceType: CustomCommandSource.Entity,
    permissionLevel: CommandPermissionLevel.Admin,
  };
  assert.equal(validateCommandPermission(adminOrigin, CommandPermissionLevel.Admin), true);

  const hostOrigin = {
    sourceType: CustomCommandSource.Entity,
    permissionLevel: CommandPermissionLevel.Host,
  };
  assert.equal(validateCommandPermission(hostOrigin, CommandPermissionLevel.Admin), true);

  const serverConsoleOrigin = {
    sourceType: CustomCommandSource.Server,
  };
  assert.equal(validateCommandPermission(serverConsoleOrigin, CommandPermissionLevel.Admin), true);
});

test('executeInspectCommand enforces permission gating on low-privilege callers', () => {
  const unauthorizedOrigin = {
    sourceType: CustomCommandSource.Entity,
    permissionLevel: CommandPermissionLevel.Any,
    sourceEntity: {
      typeId: 'minecraft:player',
      name: 'RandoPlayer',
      id: 'player-001',
    },
  };

  const result = executeInspectCommand(unauthorizedOrigin, CommandPermissionLevel.Admin);
  assert.equal(result.status, CustomCommandStatus.Failure);
  assert.ok(result.message.includes('Access denied: Insufficient permissions'));
});

test('executeInspectCommand correctly formats player entity context when authorized', () => {
  const mockPlayer = {
    typeId: 'minecraft:player',
    name: 'Steve',
    id: 'player-entity-01',
    permissionLevel: CommandPermissionLevel.Admin,
    location: { x: 120.45, y: 64.0, z: -35.8 },
  };

  const mockOrigin = {
    sourceType: CustomCommandSource.Entity,
    sourceEntity: mockPlayer,
    permissionLevel: CommandPermissionLevel.Admin,
  };

  const report = buildInspectionReport(mockOrigin);
  assert.equal(report.targetType, 'minecraft:player');
  assert.equal(report.targetId, 'player-entity-01');
  assert.deepEqual(report.coordinates, { x: 120.45, y: 64.0, z: -35.8 });

  const result = executeInspectCommand(mockOrigin, CommandPermissionLevel.Admin);
  assert.equal(result.status, CustomCommandStatus.Success);
  assert.ok(result.message.includes("Inspected entity 'Steve'"));
  assert.ok(result.message.includes('[120.45, 64, -35.8]'));
});

test('executeInspectCommand correctly formats server console context', () => {
  const mockOrigin = {
    sourceType: CustomCommandSource.Server,
  };

  const report = buildInspectionReport(mockOrigin);
  assert.equal(report.targetType, 'server_console');
  assert.equal(report.sourceType, CustomCommandSource.Server);

  const result = executeInspectCommand(mockOrigin);
  assert.equal(result.status, CustomCommandStatus.Success);
  assert.ok(result.message.includes('BDS Server Console inspected'));
  assert.ok(result.message.includes('Subsystems operational'));
});

test('executeInspectCommand correctly formats command block context', () => {
  const mockOrigin = {
    sourceType: CustomCommandSource.Block,
    sourceBlock: {
      typeId: 'minecraft:command_block',
      location: { x: 10, y: 5, z: 20 },
    },
  };

  const report = buildInspectionReport(mockOrigin);
  assert.equal(report.targetType, 'minecraft:command_block');
  assert.deepEqual(report.coordinates, { x: 10, y: 5, z: 20 });

  const result = executeInspectCommand(mockOrigin);
  assert.equal(result.status, CustomCommandStatus.Success);
  assert.ok(result.message.includes("Inspected command block 'minecraft:command_block'"));
});

test('initializeStartupHooks subscribes to system.beforeEvents.startup and registers command', () => {
  let subscribedCallback = null;
  let registeredCommand = null;

  const mockSystem = {
    beforeEvents: {
      startup: {
        subscribe(callback) {
          subscribedCallback = callback;
        },
      },
    },
  };

  initializeStartupHooks(mockSystem);
  assert.equal(typeof subscribedCallback, 'function');

  const mockEvent = {
    customCommandRegistry: {
      registerCommand(commandDefinition) {
        registeredCommand = commandDefinition;
      },
    },
  };

  subscribedCallback(mockEvent);
  assert.ok(registeredCommand);
  assert.equal(registeredCommand.name, 'engine:inspect');
  assert.equal(registeredCommand.permissionLevel, CommandPermissionLevel.Admin);
});
