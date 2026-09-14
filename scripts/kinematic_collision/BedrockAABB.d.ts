import { AABB, BedrockFace, Vector3 } from "./types.js";
/**
 * Axis-Aligned Bounding Box implementing Minecraft Bedrock coordinate conventions.
 * Coordinates: +X = East, -X = West, +Y = Up, -Y = Down, +Z = South, -Z = North.
 */
export declare class BedrockAABB {
    readonly center: Vector3;
    readonly extent: Vector3;
    readonly min: Vector3;
    readonly max: Vector3;
    /**
     * Initializes a bounding box from center coordinates and half-extents.
     * @param center Center point in Bedrock 3D space.
     * @param extent Absolute distance from center to bounds along each axis.
     */
    constructor(center: Vector3, extent: Vector3);
    /**
     * Constructs a BedrockAABB from explicit minimum and maximum boundary coordinates.
     * @param min Minimum boundary vector.
     * @param max Maximum boundary vector.
     * @returns Newly initialized BedrockAABB instance.
     */
    static fromMinMax(min: Vector3, max: Vector3): BedrockAABB;
    /**
     * Constructs a BedrockAABB from Minecraft Bedrock Script API AABB structure.
     * @param aabb Native Bedrock AABB.
     * @returns BedrockAABB instance.
     */
    static fromEntityAABB(aabb: AABB): BedrockAABB;
    /**
     * Derives the 8 bounding box vertices following Bedrock coordinate conventions.
     * Order:
     * V0: West-Down-North (minX, minY, minZ)
     * V1: East-Down-North (maxX, minY, minZ)
     * V2: West-Up-North   (minX, maxY, minZ)
     * V3: East-Up-North   (maxX, maxY, minZ)
     * V4: West-Down-South (minX, minY, maxZ)
     * V5: East-Down-South (maxX, minY, maxZ)
     * V6: West-Up-South   (minX, maxY, maxZ)
     * V7: East-Up-South   (maxX, maxY, maxZ)
     * @returns Array of 8 vertex vectors.
     */
    deriveVertices(): Vector3[];
    /**
     * Computes the 6 cardinal faces with Bedrock normal vectors and boundary vertices.
     * @returns Array of BedrockFace objects.
     */
    getFaces(): BedrockFace[];
    /**
     * Translates bounding box by specified displacement vector.
     * @param offset Translation delta.
     * @returns New translated BedrockAABB instance.
     */
    translate(offset: Vector3): BedrockAABB;
    /**
     * Expands bounding box to enclose its current bounds plus translation delta.
     * @param displacement Vector representing motion delta.
     * @returns Swept broadphase enclosing BedrockAABB.
     */
    expand(displacement: Vector3): BedrockAABB;
    /**
     * Determines whether this bounding box statically overlaps another.
     * @param other Target bounding box.
     * @returns True if boxes intersect in 3D space.
     */
    intersects(other: BedrockAABB): boolean;
    /**
     * Converts BedrockAABB to native Minecraft Bedrock Script API AABB interface.
     * @returns Native AABB structure.
     */
    toMinecraftAABB(): AABB;
}
