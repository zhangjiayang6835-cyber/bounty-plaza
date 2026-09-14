import { StartupEvent } from './commands/inspect.js';
export interface SystemBeforeEvents {
    startup: {
        subscribe(callback: (event: StartupEvent) => void): void;
    };
}
export interface BedrockSystem {
    beforeEvents: SystemBeforeEvents;
}
/**
 * Subscribes all early-execution system lifecycle listeners and custom commands.
 *
 * @param system Optional Bedrock system object instance.
 */
export declare function initializeStartupHooks(system?: BedrockSystem): void;
