const Vector3 = require('../math/Vector3');
const AABB = require('./AABB');

/**
 * Performs a swept AABB continuous collision detection (CCD) test.
 * Determines if a moving AABB collides with a static AABB along a given velocity vector.
 *
 * @param {AABB} movingAABB - The AABB that is moving.
 * @param {AABB} staticAABB - The AABB that is static.
 * @param {Vector3} velocity - The velocity vector of the moving AABB for one tick.
 * @returns {{collision: boolean, t_entry: number, normal: Vector3|null}} An object containing collision details.
 *   - collision: true if a collision occurs within the movement range (0 < t_entry < 1).
 *   - t_entry: The normalized time (0 to 1) at which the collision first occurs.
 *              0 means collision at start, 1 means collision at end.
 *              If no collision, t_entry will be 1 or greater.
 *   - normal: The normal vector of the surface hit, or null if no collision.
 */
function sweptAABB(movingAABB, staticAABB, velocity) {
    // Relative velocity
    const v = velocity;

    // Expand the static AABB by the dimensions of the moving AABB
    // This effectively treats the moving AABB as a point for collision detection
    // against the expanded static AABB.
    const expandedStaticMin = staticAABB.min.subtract(movingAABB.max.subtract(movingAABB.min));
    const expandedStaticMax = staticAABB.max;

    // Calculate time of entry and time of exit for each axis
    let t_entry = -Infinity;
    let t_exit = Infinity;

    let normal = null; // Collision normal

    // Check X-axis
    if (v.x === 0) {
        // If velocity is 0, check if already overlapping or if path is within bounds
        if (movingAABB.max.x <= staticAABB.min.x || movingAABB.min.x >= staticAABB.max.x) {
            return { collision: false, t_entry: 1, normal: null }; // No collision on X axis
        }
    } else {
        const tx_entry = (expandedStaticMin.x - movingAABB.min.x) / v.x;
        const tx_exit = (expandedStaticMax.x - movingAABB.min.x) / v.x;

        if (tx_entry > tx_exit) {
            [t_entry, t_exit] = [tx_exit, tx_entry]; // Swap to ensure entry < exit
        } else {
            [t_entry, t_exit] = [tx_entry, tx_exit];
        }

        // Update overall t_entry and t_exit
        if (t_entry > t_entry) { // Max of entry times
            t_entry = t_entry;
            normal = v.x > 0 ? new Vector3(-1, 0, 0) : new Vector3(1, 0, 0);
        }
        if (t_exit < t_exit) { // Min of exit times
            t_exit = t_exit;
        }
    }

    // Check Y-axis
    if (v.y === 0) {
        if (movingAABB.max.y <= staticAABB.min.y || movingAABB.min.y >= staticAABB.max.y) {
            return { collision: false, t_entry: 1, normal: null }; // No collision on Y axis
        }
    } else {
        const ty_entry = (expandedStaticMin.y - movingAABB.min.y) / v.y;
        const ty_exit = (expandedStaticMax.y - movingAABB.min.y) / v.y;

        if (ty_entry > ty_exit) {
            [ty_entry, ty_exit] = [ty_exit, ty_entry];
        }

        if (ty_entry > t_entry) {
            t_entry = ty_entry;
            normal = v.y > 0 ? new Vector3(0, -1, 0) : new Vector3(0, 1, 0);
        }
        if (ty_exit < t_exit) {
            t_exit = ty_exit;
        }
    }

    // Check Z-axis
    if (v.z === 0) {
        if (movingAABB.max.z <= staticAABB.min.z || movingAABB.min.z >= staticAABB.max.z) {
            return { collision: false, t_entry: 1, normal: null }; // No collision on Z axis
        }
    } else {
        const tz_entry = (expandedStaticMin.z - movingAABB.min.z) / v.z;
        const tz_exit = (expandedStaticMax.z - movingAABB.min.z) / v.z;

        if (tz_entry > tz_exit) {
            [tz_entry, tz_exit] = [tz_exit, tz_entry];
        }

        if (tz_entry > t_entry) {
            t_entry = tz_entry;
            normal = v.z > 0 ? new Vector3(0, 0, -1) : new Vector3(0, 0, 1);
        }
        if (tz_exit < t_exit) {
            t_exit = tz_exit;
        }
    }

    // If t_entry < t_exit, and t_entry < 1, and t_exit > 0, then there is a collision.
    // t_entry < 1 ensures collision happens within the current movement step.
    // t_exit > 0 ensures collision is not "behind" the moving object.
    const collision = t_entry < t_exit && t_entry < 1 && t_exit > 0;

    // If collision is detected, but t_entry is negative, it means the objects are already
    // overlapping. In this case, we might want to return t_entry = 0.
    // However, for swept AABB, we are interested in the *first* time of contact *during* the sweep.
    // If t_entry < 0, it means they were already overlapping at the start of the sweep.
    // For this problem, we assume we want to detect new collisions.
    if (collision && t_entry < 0) {
        // This case means they are already overlapping.
        // Depending on the physics engine, this might be handled as an immediate collision
        // or ignored if the goal is to prevent tunneling.
        // For preventing tunneling, we can consider it a collision at t=0.
        // For simplicity and to focus on the "swept" aspect, we'll return t_entry = 0 if already overlapping.
        // However, the standard swept AABB usually implies t_entry >= 0.
        // Let's refine the normal calculation for the actual collision axis.
        // The normal should be based on the axis that caused the earliest *positive* t_entry,
        // or the axis that caused the overlap if t_entry is 0.
        // For now, the normal is set when t_entry is updated.
    }

    // Re-evaluate normal based on the actual t_entry
    if (collision) {
        const epsilon = 1e-6; // Small epsilon for floating point comparisons
        let finalNormal = null;

        // Check which axis caused the t_entry
        // Recalculate tx_entry, ty_entry, tz_entry to find the dominant axis
        let tx_entry_val = -Infinity, ty_entry_val = -Infinity, tz_entry_val = -Infinity;

        if (v.x !== 0) {
            tx_entry_val = (expandedStaticMin.x - movingAABB.min.x) / v.x;
            const tx_exit_val = (expandedStaticMax.x - movingAABB.min.x) / v.x;
            if (tx_entry_val > tx_exit_val) tx_entry_val = tx_exit_val; // Ensure entry is min
        }
        if (v.y !== 0) {
            ty_entry_val = (expandedStaticMin.y - movingAABB.min.y) / v.y;
            const ty_exit_val = (expandedStaticMax.y - movingAABB.min.y) / v.y;
            if (ty_entry_val > ty_exit_val) ty_entry_val = ty_exit_val;
        }
        if (v.z !== 0) {
            tz_entry_val = (expandedStaticMin.z - movingAABB.min.z) / v.z;
            const tz_exit_val = (expandedStaticMax.z - movingAABB.min.z) / v.z;
            if (tz_entry_val > tz_exit_val) tz_entry_val = tz_exit_val;
        }

        if (Math.abs(t_entry - tx_entry_val) < epsilon) {
            finalNormal = v.x > 0 ? new Vector3(-1, 0, 0) : new Vector3(1, 0, 0);
        } else if (Math.abs(t_entry - ty_entry_val) < epsilon) {
            finalNormal = v.y > 0 ? new Vector3(0, -1, 0) : new Vector3(0, 1, 0);
        } else if (Math.abs(t_entry - tz_entry_val) < epsilon) {
            finalNormal = v.z > 0 ? new Vector3(0, 0, -1) : new Vector3(0, 0, 1);
        }
        normal = finalNormal;
    }


    return { collision, t_entry: collision ? Math.max(0, t_entry) : 1, normal };
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = sweptAABB;
}
