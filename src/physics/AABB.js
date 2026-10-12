const Vector3 = require('../math/Vector3');

/**
 * Represents an Axis-Aligned Bounding Box (AABB).
 * Follows Bedrock coordinate space (+X East, +Y Up, +Z South).
 */
class AABB {
    /**
     * Creates an AABB.
     * @param {Vector3} min - The minimum corner of the AABB.
     * @param {Vector3} max - The maximum corner of the AABB.
     */
    constructor(min, max) {
        if (!(min instanceof Vector3) || !(max instanceof Vector3)) {
            throw new Error("AABB constructor requires two Vector3 instances for min and max.");
        }
        this.min = min;
        this.max = max;
    }

    /**
     * Creates an AABB from a center position and dimensions.
     * Assumes position is the bottom-center for Y, and center for XZ.
     * @param {Vector3} position - The bottom-center position of the AABB.
     * @param {number} width - The width of the AABB (X dimension).
     * @param {number} height - The height of the AABB (Y dimension).
     * @param {number} depth - The depth of the AABB (Z dimension).
     * @returns {AABB} A new AABB instance.
     */
    static fromPositionAndDimensions(position, width, height, depth) {
        const halfWidth = width / 2;
        const halfDepth = depth / 2;

        const minX = position.x - halfWidth;
        const minY = position.y;
        const minZ = position.z - halfDepth;

        const maxX = position.x + halfWidth;
        const maxY = position.y + height;
        const maxZ = position.z + halfDepth;

        return new AABB(new Vector3(minX, minY, minZ), new Vector3(maxX, maxY, maxZ));
    }

    /**
     * Translates the AABB by a given vector.
     * @param {Vector3} offset - The translation vector.
     * @returns {AABB} A new AABB instance, translated.
     */
    translate(offset) {
        return new AABB(this.min.add(offset), this.max.add(offset));
    }

    /**
     * Returns all 8 spatial bounding vertices of the AABB.
     * Vertices are ordered for consistency, e.g., starting from min corner.
     *
     * Bedrock coordinate space: +X East, +Y Up, +Z South.
     *
     * @returns {Vector3[]} An array of 8 Vector3 instances representing the vertices.
     */
    getVertices() {
        const { min, max } = this;
        return [
            new Vector3(min.x, min.y, min.z), // 0: min corner
            new Vector3(max.x, min.y, min.z), // 1: +X
            new Vector3(min.x, max.y, min.z), // 2: +Y
            new Vector3(min.x, min.y, max.z), // 3: +Z
            new Vector3(max.x, max.y, min.z), // 4: +X, +Y
            new Vector3(max.x, min.y, max.z), // 5: +X, +Z
            new Vector3(min.x, max.y, max.z), // 6: +Y, +Z
            new Vector3(max.x, max.y, max.z)  // 7: max corner
        ];
    }

    /**
     * Checks if this AABB intersects with another AABB.
     * @param {AABB} other - The other AABB.
     * @returns {boolean} True if they intersect, false otherwise.
     */
    intersects(other) {
        return (this.min.x < other.max.x && this.max.x > other.min.x) &&
               (this.min.y < other.max.y && this.max.y > other.min.y) &&
               (this.min.z < other.max.z && this.max.z > other.min.z);
    }

    /**
     * Returns a string representation of the AABB.
     * @returns {string}
     */
    toString() {
        return `AABB(min: ${this.min.toString()}, max: ${this.max.toString()})`;
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AABB;
}
