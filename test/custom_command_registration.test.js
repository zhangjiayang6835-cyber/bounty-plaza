import test from 'node:test';
import assert from 'node:assert/strict';
import {
  CommandPermissionLevel,
  CustomCommandSource,
  CustomCommandStatus,
} from '../scripts/commands/types.js';
import {
  buildInspectionReport,
  executeInspectCommand,
  registerInspectCommand,
  resolveRegistry,
} from '../scripts/commands/inspect.js';

test('registerInspectCommand registers inspect command with Admin permission level', () => {
  const registered = [];

  const mockRegistry = {
    registerCommand(definition, callback) {
      registered.push({ definition, callback });
    },
  };

  const mockEvent = {
    customCommandRegistry: mockRegistry,
  };

  registerInspectCommand(mockEvent);

  assert.equal(registered.length, 2);
  const inspectCmd = registered.find((cmd) => cmd.definition.name === 'inspect');
  assert.ok(inspectCmd);
  assert.equal(inspectCmd.definition.permissionLevel, CommandPermissionLevel.Admin);
  assert.equal(inspectCmd.definition.cheatsRequired, true);
  assert.equal(typeof inspectCmd.callback, 'function');

  const engineCmd = registered.find((cmd) => cmd.definition.name === 'engine:inspect');
  assert.ok(engineCmd);
  assert.equal(engineCmd.definition.permissionLevel, CommandPermissionLevel.Admin);
});

test('registerInspectCommand accepts registry instance directly', () => {
  const registered = [];
  const mockRegistry = {
    registerCommand(definition, callback) {
      registered.push({ definition, callback });
    },
  };

  registerInspectCommand(mockRegistry);
  assert.equal(registered.length, 2);
});

test('resolveRegistry throws TypeError when registry is invalid or missing registerCommand', () => {
  assert.throws(() => resolveRegistry(null), {
    name: 'TypeError',
  });
  assert.throws(() => resolveRegistry({}), {
    name: 'TypeError',
  });
  assert.throws(
    () =>
      resolveRegistry({
        customCommandRegistry: { notRegisterCommand: () => {} },
      }),
    {
      name: 'TypeError',
    }
  );
});

test('executeInspectCommand gates execution on permission level', () => {
  const lowPermissionOrigin = {
    sourceType: CustomCommandSource.Entity,
    permissionLevel: CommandPermissionLevel.Normal,
  };

  const result = executeInspectCommand(lowPermissionOrigin);
  assert.equal(result.status, CustomCommandStatus.Failure);
  assert.ok(result.message.includes('Permission denied'));
});

test('executeInspectCommand inspects player entity successfully', () => {
  const playerOrigin = {
    sourceType: CustomCommandSource.Entity,
    sourceEntity: {
      id: 'entity-uuid-1',
      typeId: 'minecraft:player',
      name: 'ServerAdmin',
      location: { x: 100.5, y: 64.0, z: -200.25 },
    },
    permissionLevel: CommandPermissionLevel.Admin,
  };

  const report = buildInspectionReport(playerOrigin);
  assert.equal(report.targetType, 'minecraft:player');
  assert.deepEqual(report.coordinates, { x: 100.5, y: 64.0, z: -200.25 });

  const result = executeInspectCommand(playerOrigin);
  assert.equal(result.status, CustomCommandStatus.Success);
  assert.ok(result.message.includes("Inspected entity 'ServerAdmin'"));
});

test('executeInspectCommand inspects command block successfully', () => {
  const blockOrigin = {
    sourceType: CustomCommandSource.Block,
    sourceBlock: {
      typeId: 'minecraft:command_block',
      location: { x: 0, y: 10, z: 0 },
    },
    permissionLevel: CommandPermissionLevel.Admin,
  };

  const result = executeInspectCommand(blockOrigin);
  assert.equal(result.status, CustomCommandStatus.Success);
  assert.ok(result.message.includes('command block'));
});

test('executeInspectCommand inspects server console successfully', () => {
  const consoleOrigin = {
    sourceType: CustomCommandSource.Server,
    permissionLevel: CommandPermissionLevel.Admin,
  };

  const result = executeInspectCommand(consoleOrigin);
  assert.equal(result.status, CustomCommandStatus.Success);
  assert.ok(result.message.includes('BDS Server Console'));
});
