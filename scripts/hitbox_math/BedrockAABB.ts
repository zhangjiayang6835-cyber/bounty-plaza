/**
 * 3D vector and Axis-Aligned Bounding Box primitives adhering to Bedrock coordinates.
 * +X = East,  -X = West
 * +Y = Up,    -Y = Down
 * +Z = South, -Z = North
 */

import { BedrockFaceDef, BedrockFaceName, Vector3D } from "./types.js";

export class Vector3 implements Vector3D {
  readonly x: number;
  readonly y: number;
  readonly z: number;

  constructor(x: number, y: number, z: number) {
    this.x = x;
    this.y = y;
    this.z = z;
  }

  /**
   * Adds target vector to current vector.
   */
  add(other: Vector3D): Vector3 {
    return new Vector3(this.x + other.x, this.y + other.y, this.z + other.z);
  }

  /**
   * Subtracts target vector from current vector.
   */
  subtract(other: Vector3D): Vector3 {
    return new Vector3(this.x - other.x, this.y - other.y, this.z - other.z);
  }

  /**
   * Multiplies vector by scalar factor.
   */
  scale(scalar: number): Vector3 {
    return new Vector3(this.x * scalar, this.y * scalar, this.z * scalar);
  }

  /**
   * Calculates scalar dot product.
   */
  dot(other: Vector3D): number {
    return this.x * other.x + this.y * other.y + this.z * other.z;
  }

  /**
   * Calculates vector cross product.
   */
  cross(other: Vector3D): Vector3 {
    const cx = this.y * other.z - this.z * other.y;
    const cy = this.z * other.x - this.x * other.z;
    const cz = this.x * other.y - this.y * other.x;
    return new Vector3(cx, cy, cz);
  }

  /**
   * Calculates Euclidean vector magnitude.
   */
  magnitude(): number {
    return Math.sqrt(this.x * this.x + this.y * this.y + this.z * this.z);
  }

  /**
   * Normalizes vector to unit length.
   */
  normalize(): Vector3 {
    const mag = this.magnitude();
    if (mag < 1e-9) {
      return new Vector3(0, 0, 0);
    }
    return new Vector3(this.x / mag, this.y / mag, this.z / mag);
  }

  /**
   * Calculates Euclidean distance to target vector.
   */
  distanceTo(other: Vector3D): number {
    return this.subtract(other).magnitude();
  }
}

export class BoundingBox {
  readonly center: Vector3;
  readonly extent: Vector3;

  constructor(center: Vector3, extent: Vector3) {
    this.center = center;
    this.extent = extent;
  }

  /**
   * Calculates minimum coordinate boundary point (West, Down, North).
   */
  get minPoint(): Vector3 {
    return new Vector3(
      this.center.x - this.extent.x,
      this.center.y - this.extent.y,
      this.center.z - this.extent.z,
    );
  }

  /**
   * Calculates maximum coordinate boundary point (East, Up, South).
   */
  get maxPoint(): Vector3 {
    return new Vector3(
      this.center.x + this.extent.x,
      this.center.y + this.extent.y,
      this.center.z + this.extent.z,
    );
  }

  /**
   * Derives eight corner vertices following Bedrock coordinate boundaries.
   */
  deriveVertices(): Vector3[] {
    const minP = this.minPoint;
    const maxP = this.maxPoint;
    return [
      new Vector3(minP.x, minP.y, minP.z),
      new Vector3(maxP.x, minP.y, minP.z),
      new Vector3(minP.x, maxP.y, minP.z),
      new Vector3(maxP.x, maxP.y, minP.z),
      new Vector3(minP.x, minP.y, maxP.z),
      new Vector3(maxP.x, minP.y, maxP.z),
      new Vector3(minP.x, maxP.y, maxP.z),
      new Vector3(maxP.x, maxP.y, maxP.z),
    ];
  }

  /**
   * Returns cardinal faces with Bedrock normal vectors.
   */
  getFaces(): BedrockFaceDef[] {
    return [
      { name: "East" as BedrockFaceName, normal: new Vector3(1, 0, 0) },
      { name: "West" as BedrockFaceName, normal: new Vector3(-1, 0, 0) },
      { name: "Up" as BedrockFaceName, normal: new Vector3(0, 1, 0) },
      { name: "Down" as BedrockFaceName, normal: new Vector3(0, -1, 0) },
      { name: "South" as BedrockFaceName, normal: new Vector3(0, 0, 1) },
      { name: "North" as BedrockFaceName, normal: new Vector3(0, 0, -1) },
    ];
  }

  /**
   * Computes expanded bounding box enclosing swept trajectory.
   */
  expand(displacement: Vector3D): BoundingBox {
    const minP = this.minPoint;
    const maxP = this.maxPoint;

    const minX = Math.min(minP.x, minP.x + displacement.x);
    const minY = Math.min(minP.y, minP.y + displacement.y);
    const minZ = Math.min(minP.z, minP.z + displacement.z);

    const maxX = Math.max(maxP.x, maxP.x + displacement.x);
    const maxY = Math.max(maxP.y, maxP.y + displacement.y);
    const maxZ = Math.max(maxP.z, maxP.z + displacement.z);

    const newCenter = new Vector3(
      (minX + maxX) * 0.5,
      (minY + maxY) * 0.5,
      (minZ + maxZ) * 0.5,
    );
    const newExtent = new Vector3(
      (maxX - minX) * 0.5,
      (maxY - minY) * 0.5,
      (maxZ - minZ) * 0.5,
    );

    return new BoundingBox(newCenter, newExtent);
  }

  /**
   * Determines volumetric overlap with target bounding box.
   */
  intersects(other: BoundingBox): boolean {
    const minA = this.minPoint;
    const maxA = this.maxPoint;
    const minB = other.minPoint;
    const maxB = other.maxPoint;

    const overlapX = minA.x <= maxB.x && maxA.x >= minB.x;
    const overlapY = minA.y <= maxB.y && maxA.y >= minB.y;
    const overlapZ = minA.z <= maxB.z && maxA.z >= minB.z;

    return overlapX && overlapY && overlapZ;
  }
}
