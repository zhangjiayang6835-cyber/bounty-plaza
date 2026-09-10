import { AABB, BedrockFace, Vector3 } from "./types.js";

/**
 * Axis-Aligned Bounding Box implementing Minecraft Bedrock coordinate conventions.
 * Coordinates: +X = East, -X = West, +Y = Up, -Y = Down, +Z = South, -Z = North.
 */
export class BedrockAABB {
  public readonly center: Vector3;
  public readonly extent: Vector3;
  public readonly min: Vector3;
  public readonly max: Vector3;

  /**
   * Initializes a bounding box from center coordinates and half-extents.
   * @param center Center point in Bedrock 3D space.
   * @param extent Absolute distance from center to bounds along each axis.
   */
  constructor(center: Vector3, extent: Vector3) {
    const extX = Math.abs(extent.x);
    const extY = Math.abs(extent.y);
    const extZ = Math.abs(extent.z);

    this.center = { x: center.x, y: center.y, z: center.z };
    this.extent = { x: extX, y: extY, z: extZ };
    this.min = {
      x: center.x - extX,
      y: center.y - extY,
      z: center.z - extZ
    };
    this.max = {
      x: center.x + extX,
      y: center.y + extY,
      z: center.z + extZ
    };
  }

  /**
   * Constructs a BedrockAABB from explicit minimum and maximum boundary coordinates.
   * @param min Minimum boundary vector.
   * @param max Maximum boundary vector.
   * @returns Newly initialized BedrockAABB instance.
   */
  public static fromMinMax(min: Vector3, max: Vector3): BedrockAABB {
    const minX = Math.min(min.x, max.x);
    const minY = Math.min(min.y, max.y);
    const minZ = Math.min(min.z, max.z);
    const maxX = Math.max(min.x, max.x);
    const maxY = Math.max(min.y, max.y);
    const maxZ = Math.max(min.z, max.z);

    const center: Vector3 = {
      x: (minX + maxX) / 2,
      y: (minY + maxY) / 2,
      z: (minZ + maxZ) / 2
    };
    const extent: Vector3 = {
      x: (maxX - minX) / 2,
      y: (maxY - minY) / 2,
      z: (maxZ - minZ) / 2
    };

    return new BedrockAABB(center, extent);
  }

  /**
   * Constructs a BedrockAABB from Minecraft Bedrock Script API AABB structure.
   * @param aabb Native Bedrock AABB.
   * @returns BedrockAABB instance.
   */
  public static fromEntityAABB(aabb: AABB): BedrockAABB {
    return new BedrockAABB(aabb.center, aabb.extent);
  }

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
  public deriveVertices(): Vector3[] {
    return [
      { x: this.min.x, y: this.min.y, z: this.min.z },
      { x: this.max.x, y: this.min.y, z: this.min.z },
      { x: this.min.x, y: this.max.y, z: this.min.z },
      { x: this.max.x, y: this.max.y, z: this.min.z },
      { x: this.min.x, y: this.min.y, z: this.max.z },
      { x: this.max.x, y: this.min.y, z: this.max.z },
      { x: this.min.x, y: this.max.y, z: this.max.z },
      { x: this.max.x, y: this.max.y, z: this.max.z }
    ];
  }

  /**
   * Computes the 6 cardinal faces with Bedrock normal vectors and boundary vertices.
   * @returns Array of BedrockFace objects.
   */
  public getFaces(): BedrockFace[] {
    const verts = this.deriveVertices();
    return [
      {
        name: "East",
        normal: { x: 1, y: 0, z: 0 },
        vertices: [verts[1], verts[5], verts[7], verts[3]]
      },
      {
        name: "West",
        normal: { x: -1, y: 0, z: 0 },
        vertices: [verts[0], verts[2], verts[6], verts[4]]
      },
      {
        name: "Up",
        normal: { x: 0, y: 1, z: 0 },
        vertices: [verts[2], verts[3], verts[7], verts[6]]
      },
      {
        name: "Down",
        normal: { x: 0, y: -1, z: 0 },
        vertices: [verts[0], verts[4], verts[5], verts[1]]
      },
      {
        name: "South",
        normal: { x: 0, y: 0, z: 1 },
        vertices: [verts[4], verts[5], verts[7], verts[6]]
      },
      {
        name: "North",
        normal: { x: 0, y: 0, z: -1 },
        vertices: [verts[0], verts[1], verts[3], verts[2]]
      }
    ];
  }

  /**
   * Translates bounding box by specified displacement vector.
   * @param offset Translation delta.
   * @returns New translated BedrockAABB instance.
   */
  public translate(offset: Vector3): BedrockAABB {
    const newCenter: Vector3 = {
      x: this.center.x + offset.x,
      y: this.center.y + offset.y,
      z: this.center.z + offset.z
    };
    return new BedrockAABB(newCenter, this.extent);
  }

  /**
   * Expands bounding box to enclose its current bounds plus translation delta.
   * @param displacement Vector representing motion delta.
   * @returns Swept broadphase enclosing BedrockAABB.
   */
  public expand(displacement: Vector3): BedrockAABB {
    const sweptMin: Vector3 = {
      x: Math.min(this.min.x, this.min.x + displacement.x),
      y: Math.min(this.min.y, this.min.y + displacement.y),
      z: Math.min(this.min.z, this.min.z + displacement.z)
    };
    const sweptMax: Vector3 = {
      x: Math.max(this.max.x, this.max.x + displacement.x),
      y: Math.max(this.max.y, this.max.y + displacement.y),
      z: Math.max(this.max.z, this.max.z + displacement.z)
    };
    return BedrockAABB.fromMinMax(sweptMin, sweptMax);
  }

  /**
   * Determines whether this bounding box statically overlaps another.
   * @param other Target bounding box.
   * @returns True if boxes intersect in 3D space.
   */
  public intersects(other: BedrockAABB): boolean {
    return (
      this.min.x < other.max.x &&
      this.max.x > other.min.x &&
      this.min.y < other.max.y &&
      this.max.y > other.min.y &&
      this.min.z < other.max.z &&
      this.max.z > other.min.z
    );
  }

  /**
   * Converts BedrockAABB to native Minecraft Bedrock Script API AABB interface.
   * @returns Native AABB structure.
   */
  public toMinecraftAABB(): AABB {
    return {
      center: { ...this.center },
      extent: { ...this.extent }
    };
  }
}
