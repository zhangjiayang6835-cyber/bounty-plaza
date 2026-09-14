/**
 * 3D vector and Axis-Aligned Bounding Box primitives adhering to Bedrock coordinates.
 * +X = East,  -X = West
 * +Y = Up,    -Y = Down
 * +Z = South, -Z = North
 */
import { BedrockFaceDef, Vector3D } from "./types.js";
export declare class Vector3 implements Vector3D {
    readonly x: number;
    readonly y: number;
    readonly z: number;
    constructor(x: number, y: number, z: number);
    /**
     * Adds target vector to current vector.
     */
    add(other: Vector3D): Vector3;
    /**
     * Subtracts target vector from current vector.
     */
    subtract(other: Vector3D): Vector3;
    /**
     * Multiplies vector by scalar factor.
     */
    scale(scalar: number): Vector3;
    /**
     * Calculates scalar dot product.
     */
    dot(other: Vector3D): number;
    /**
     * Calculates vector cross product.
     */
    cross(other: Vector3D): Vector3;
    /**
     * Calculates Euclidean vector magnitude.
     */
    magnitude(): number;
    /**
     * Normalizes vector to unit length.
     */
    normalize(): Vector3;
    /**
     * Calculates Euclidean distance to target vector.
     */
    distanceTo(other: Vector3D): number;
}
export declare class BoundingBox {
    readonly center: Vector3;
    readonly extent: Vector3;
    constructor(center: Vector3, extent: Vector3);
    /**
     * Calculates minimum coordinate boundary point (West, Down, North).
     */
    get minPoint(): Vector3;
    /**
     * Calculates maximum coordinate boundary point (East, Up, South).
     */
    get maxPoint(): Vector3;
    /**
     * Derives eight corner vertices following Bedrock coordinate boundaries.
     */
    deriveVertices(): Vector3[];
    /**
     * Returns cardinal faces with Bedrock normal vectors.
     */
    getFaces(): BedrockFaceDef[];
    /**
     * Computes expanded bounding box enclosing swept trajectory.
     */
    expand(displacement: Vector3D): BoundingBox;
    /**
     * Determines volumetric overlap with target bounding box.
     */
    intersects(other: BoundingBox): boolean;
}
