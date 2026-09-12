import { CommandPermissionLevel, CustomCommandSource, CustomCommandStatus, InspectionReport } from './types.js';
export interface Vector3 {
    x: number;
    y: number;
    z: number;
}
export interface ScriptEntity {
    id: string;
    typeId: string;
    name?: string;
    location?: Vector3;
}
export interface ScriptBlock {
    typeId: string;
    location: Vector3;
}
export interface CustomCommandOrigin {
    sourceType: CustomCommandSource | string;
    sourceEntity?: ScriptEntity;
    sourceBlock?: ScriptBlock;
    permissionLevel?: CommandPermissionLevel | number;
}
export interface CustomCommandResult {
    status: CustomCommandStatus;
    message: string;
}
export interface CustomCommand {
    name: string;
    description: string;
    permissionLevel: CommandPermissionLevel;
    cheatsRequired?: boolean;
}
export interface CustomCommandRegistry {
    registerCommand(commandDefinition: CustomCommand | string, callbackOrOptions?: unknown, maybeCallback?: unknown): void;
}
export interface StartupEvent {
    customCommandRegistry: CustomCommandRegistry;
}
/**
 * Builds an inspection report summarizing the command execution context.
 *
 * @param origin Contextual origin metadata for the command invocation.
 * @returns Structured inspection report object.
 */
export declare function buildInspectionReport(origin: CustomCommandOrigin): InspectionReport;
/**
 * Executes administrative inspection command logic across player and server contexts.
 *
 * @param origin Invocation metadata identifying caller type and position.
 * @returns Result object containing execution status and response message.
 */
export declare function executeInspectCommand(origin: CustomCommandOrigin): CustomCommandResult;
/**
 * Extracts and validates the active CustomCommandRegistry instance.
 *
 * @param target StartupEvent or CustomCommandRegistry instance.
 * @returns Validated CustomCommandRegistry instance.
 */
export declare function resolveRegistry(target: unknown): CustomCommandRegistry;
/**
 * Registers the /inspect and /engine:inspect slash commands onto the startup registry.
 *
 * @param target The startup event or CustomCommandRegistry instance.
 */
export declare function registerInspectCommand(target: StartupEvent | CustomCommandRegistry | unknown): void;
