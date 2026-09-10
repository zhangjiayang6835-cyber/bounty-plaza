/**
 * Bedrock script runtime module integrating swept AABB continuous collision detection.
 */
export declare class BedrockKinematicRuntime {
    private static isInitialized;
    /**
     * Initializes periodic continuous collision verification loop.
     */
    static initialize(): void;
    /**
     * Executes continuous collision detection across tracked kinematic entities.
     */
    static tickKinematicEntities(): void;
}
