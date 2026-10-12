/**
 * Represents a 3D vector.
 */
class Vector3 {
    constructor(x = 0, y = 0, z = 0) {
        this.x = x;
        this.y = y;
        this.z = z;
    }

    /**
     * Adds another vector to this vector.
     * @param {Vector3} other - The vector to add.
     * @returns {Vector3} A new vector representing the sum.
     */
    add(other) {
        return new Vector3(this.x + other.x, this.y + other.y, this.z + other.z);
    }

    /**
     * Subtracts another vector from this vector.
     * @param {Vector3} other - The vector to subtract.
     * @returns {Vector3} A new vector representing the difference.
     */
    subtract(other) {
        return new Vector3(this.x - other.x, this.y - other.y, this.z - other.z);
    }

    /**
     * Multiplies this vector by a scalar.
     * @param {number} scalar - The scalar to multiply by.
     * @returns {Vector3} A new vector representing the scaled vector.
     */
    multiplyScalar(scalar) {
        return new Vector3(this.x * scalar, this.y * scalar, this.z * scalar);
    }

    /**
     * Divides this vector by a scalar.
     * @param {number} scalar - The scalar to divide by.
     * @returns {Vector3} A new vector representing the divided vector.
     */
    divideScalar(scalar) {
        if (scalar === 0) {
            throw new Error("Cannot divide by zero.");
        }
        return new Vector3(this.x / scalar, this.y / scalar, this.z / scalar);
    }

    /**
     * Calculates the dot product with another vector.
     * @param {Vector3} other - The other vector.
     * @returns {number} The dot product.
     */
    dot(other) {
        return this.x * other.x + this.y * other.y + this.z * other.z;
    }

    /**
     * Calculates the squared length (magnitude) of the vector.
     * @returns {number} The squared length.
     */
    lengthSq() {
        return this.x * this.x + this.y * this.y + this.z * this.z;
    }

    /**
     * Calculates the length (magnitude) of the vector.
     * @returns {number} The length.
     */
    length() {
        return Math.sqrt(this.lengthSq());
    }

    /**
     * Normalizes this vector (makes its length 1).
     * @returns {Vector3} A new vector representing the normalized vector.
     */
    normalize() {
        const len = this.length();
        if (len === 0) {
            return new Vector3(0, 0, 0);
        }
        return this.divideScalar(len);
    }

    /**
     * Returns a string representation of the vector.
     * @returns {string}
     */
    toString() {
        return `Vector3(${this.x.toFixed(2)}, ${this.y.toFixed(2)}, ${this.z.toFixed(2)})`;
    }

    /**
     * Creates a copy of this vector.
     * @returns {Vector3} A new vector with the same components.
     */
    clone() {
        return new Vector3(this.x, this.y, this.z);
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = Vector3;
}
